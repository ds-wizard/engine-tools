from __future__ import annotations

import abc
import datetime
import enum
import logging
import os
import select
import signal
import threading
import time
import typing

import psycopg
import psycopg.errors
import tenacity

from dsw.database.model import PersistentCommand

from .query import CommandQueries


if typing.TYPE_CHECKING:
    from dsw.database import Database


LOG = logging.getLogger(__name__)

RETRY_QUERY_MULTIPLIER = 0.5
RETRY_QUERY_TRIES = 3
RETRY_QUEUE_MULTIPLIER = 0.5
RETRY_QUEUE_TRIES = 5

# Pause after a failed command, so a queue full of failing commands
# cannot be processed in a tight loop
FAILED_COMMAND_DELAY = 0.5


def _setup_wakeup_pipe() -> tuple[int, int] | tuple[None, None]:
    # Self-pipe makes select() return immediately when a signal is received
    # (works with any POSIX platform, on Windows select() accepts sockets only)
    if os.name != 'posix':
        return None, None
    read_fd, write_fd = os.pipe()
    try:
        os.set_blocking(read_fd, False)
        os.set_blocking(write_fd, False)
        signal.set_wakeup_fd(write_fd)
    except (OSError, ValueError):
        # not in the main thread of the main interpreter
        LOG.warning('Could not set up the signal wakeup pipe', exc_info=True)
        os.close(read_fd)
        os.close(write_fd)
        return None, None
    return read_fd, write_fd


_WAKEUP_PIPE_R, _WAKEUP_PIPE_W = _setup_wakeup_pipe()


def _drain_wakeup_pipe():
    if _WAKEUP_PIPE_R is None:
        return
    try:
        while os.read(_WAKEUP_PIPE_R, 4096):
            pass
    except BlockingIOError:
        pass


class ProcessResult(enum.Enum):
    DONE = 'done'
    FAILED = 'failed'
    SKIPPED = 'skipped'  # taken by someone else, nothing was processed


class CommandJobError(Exception):

    def __init__(self, job_id: str, message: str, try_again: bool,
                 exc: BaseException | None = None):
        self.job_id = job_id
        self.message = message
        self.try_again = try_again
        self.exc = exc
        super().__init__(message)

    def __str__(self):
        return self.message

    def log_message(self):
        if self.exc is None:
            return self.message
        return f'{self.message} (caused by: [{type(self.exc).__name__}] {str(self.exc)})'

    def db_message(self):
        if self.exc is None:
            return self.message
        return f'{self.message}\n\n' \
               f'Caused by: {type(self.exc).__name__}\n' \
               f'{str(self.exc)}'

    @staticmethod
    def create(job_id: str, message: str, try_again: bool = True,
               exc: BaseException | None = None):
        if isinstance(exc, CommandJobError):
            return exc
        return CommandJobError(
            job_id=job_id,
            message=message,
            try_again=try_again,
            exc=exc,
        )


class CommandJobTimeoutError(Exception):

    def __init__(self, timeout: float):
        self.timeout = timeout
        super().__init__(f'Job exceeded the time limit ({timeout} seconds)')


class FatalCommandQueueError(Exception):
    """Error that makes it unsafe to continue processing in this process."""


class CommandWorker:

    @abc.abstractmethod
    def work(self, command: PersistentCommand):
        pass

    def process_timeout(self, e: BaseException):
        pass

    def process_exception(self, e: BaseException):
        pass


class _CommandJobThread(threading.Thread):
    """Runs a single job and captures whatever it raises."""

    def __init__(self, work: typing.Callable[[], None]):
        super().__init__(daemon=True, name='dsw-command-job')
        self.work = work
        self.exception: BaseException | None = None

    def run(self):
        try:
            self.work()
        except BaseException as e:  # noqa: BLE001 (re-raised in the caller thread)
            self.exception = e


class CommandQueue:

    def __init__(self, *, worker: CommandWorker, db: Database,
                 channel: str, component: str, wait_timeout: float,
                 work_timeout: int | None = None):
        self.worker = worker
        self.db = db
        self.queries = CommandQueries(
            channel=channel,
        )
        self.component = component
        self.wait_timeout = wait_timeout
        self.work_timeout = work_timeout
        self._interrupted = False

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGABRT, self._signal_handler)

    def run(self):
        LOG.info('Starting to process the command queue')
        while not self._interrupted:
            self._run_iteration()
        LOG.info('Exiting command queue')

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUEUE_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUEUE_TRIES),
        retry=tenacity.retry_if_not_exception_type(FatalCommandQueueError),
        before=tenacity.before_log(LOG, logging.INFO),
        after=tenacity.after_log(LOG, logging.INFO),
    )
    def _run_iteration(self):
        # Retrying is per iteration (not per process), so the budget is spent
        # on a single outage and reset by each successful cycle
        connection = self._ensure_listening()
        self._fetch_and_process_queued()
        if self._interrupted:
            return
        self._wait_for_notifications(connection)

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUEUE_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUEUE_TRIES),
        retry=tenacity.retry_if_not_exception_type(FatalCommandQueueError),
        before=tenacity.before_log(LOG, logging.INFO),
        after=tenacity.after_log(LOG, logging.INFO),
    )
    def run_once(self):
        LOG.info('Processing the command queue once')
        self._fetch_and_process_queued()

    def _ensure_listening(self) -> psycopg.Connection:
        # Both the connection and the LISTEN registration are re-checked in
        # each iteration: a re-established connection is not listening anymore
        # and its socket (used for select) is a different one
        queue_conn = self.db.conn_queue
        connection = queue_conn.connection
        if connection.broken:
            LOG.warning('Connection of the command queue is broken, reconnecting')
            queue_conn.reset()
            connection = queue_conn.connection
        if not queue_conn.listening:
            LOG.info('Preparing to listen to command queue (issuing LISTEN)')
            connection.execute(
                query=self.queries.query_listen().encode(),
            )
            queue_conn.listening = True
            LOG.info('Listening to notifications in command queue')
        return connection

    def _wait_for_notifications(self, connection: psycopg.Connection):
        socket_fd = connection.pgconn.socket
        fds = [socket_fd]
        if _WAKEUP_PIPE_R is not None:
            fds.append(_WAKEUP_PIPE_R)

        LOG.info('Waiting for notifications (up to %s seconds)', self.wait_timeout)
        readable, _, _ = select.select(fds, [], [], self.wait_timeout)

        if _WAKEUP_PIPE_R is not None and _WAKEUP_PIPE_R in readable:
            _drain_wakeup_pipe()

        if self._interrupted:
            LOG.debug('Interrupt signal received, ending...')
            return

        if len(readable) == 0:
            LOG.info('Nothing received in this cycle (timeout %s seconds)',
                     self.wait_timeout)
            return

        if socket_fd in readable:
            self._receive_notifications(connection)

    def _receive_notifications(self, connection: psycopg.Connection):
        # A readable socket may also mean that the server closed the connection;
        # reading from it is the only way to find that out (the connection still
        # reports itself as usable until then)
        try:
            connection.pgconn.consume_input()
            notifications = 0
            for notification in connection.notifies(timeout=0):
                notifications += 1
                LOG.info('Notification received: %s', notification)
            LOG.info('Notifications received (%s in total)', notifications)
        except psycopg.Error as e:
            LOG.warning('Connection of the command queue is not usable (%s), '
                        'it will be established again', str(e))
            self.db.conn_queue.listening = False

    def _fetch_and_process_queued(self):
        LOG.info('Fetching the commands')
        count = 0
        while self.fetch_and_process():
            count += 1
            if self._interrupted:
                LOG.debug('Interrupt signal received, stopping the processing')
                break
        LOG.info('There are no more commands to process (%s processed)',
                 count)

    def fetch_and_process(self) -> bool:
        command = self._fetch_command()
        if command is None:
            return False

        LOG.info('Retrieved persistent command %s for processing', command.uuid)
        LOG.info('Previous state: %s', command.state)
        LOG.info('Attempts: %s / %s', command.attempts, command.max_attempts)
        LOG.info('Last error: %s', command.last_error_message)

        if self._process(command) is ProcessResult.FAILED:
            time.sleep(FAILED_COMMAND_DELAY)
        LOG.info('Notification processing finished')
        return True

    def _fetch_command(self) -> PersistentCommand | None:
        # SELECT ... FOR UPDATE starts a transaction that must be ended on every
        # exit path, otherwise the connection stays idle in transaction forever
        try:
            with self.db.conn_query.new_cursor(use_dict=True) as cursor:
                cursor.execute(
                    query=self.queries.query_get_command(),
                    params={
                        'component': self.component,
                        'now': datetime.datetime.now(tz=datetime.UTC),
                    },
                )
                result = cursor.fetchone()
        except Exception:
            self._rollback()
            raise
        if result is None:
            LOG.info('There is no persistent command to process')
            self._rollback()
            return None
        return PersistentCommand.from_dict_row(result)

    def _process(self, command: PersistentCommand) -> ProcessResult:
        attempt_number = command.attempts + 1
        if not self._start_command(command=command, attempt_number=attempt_number):
            return ProcessResult.SKIPPED

        try:
            self._do_work(command)
            self.db.execute_query(
                query=self.queries.query_command_done(),
                attempts=attempt_number,
                updated_at=datetime.datetime.now(tz=datetime.UTC),
                uuid=command.uuid,
            )
            self._commit()
            return ProcessResult.DONE
        except CommandJobTimeoutError as e:
            msg = f'Processing exceeded time limit ({self.work_timeout} seconds)'
            LOG.error(msg)
            try:
                # The job goes on in its thread and it may be in the middle of
                # using the connection, so this one must not be touched anymore
                self._abandon_connection()
                self.worker.process_timeout(e)
                self._store_result(
                    query=self.queries.query_command_error(),
                    message=msg,
                    attempts=attempt_number,
                    uuid=command.uuid,
                )
            except Exception:
                LOG.warning('Failed to store the result of the timed-out command',
                            exc_info=True)
            # The job cannot be stopped and it shares the resources of this
            # process (DB connection, S3 client, ...), so it must not continue
            raise FatalCommandQueueError(msg) from e
        except CommandJobError as e:
            if e.try_again and attempt_number < command.max_attempts:
                query = self.queries.query_command_error()
                msg = f'Failed with job error: {e.message} (will try again)'
            else:
                query = self.queries.query_command_error_stop()
                msg = f'Failed with job error: {e.message}'
            LOG.warning(msg)
            self._rollback_work()
            self.worker.process_exception(e)
            self._store_result(
                query=query,
                message=msg,
                attempts=attempt_number,
                uuid=command.uuid,
            )
        except Exception as e:
            if attempt_number < command.max_attempts:
                msg = f'Failed with exception [{type(e).__name__}]: {str(e)} (will try again)'
            else:
                msg = f'Failed with exception [{type(e).__name__}]: {str(e)}'
            LOG.warning(msg)
            self._rollback_work()
            self.worker.process_exception(e)
            self._store_result(
                query=self.queries.query_command_error(),
                message=msg,
                attempts=attempt_number,
                uuid=command.uuid,
            )
        return ProcessResult.FAILED

    def _abandon_connection(self):
        # Replace the connection that the timed-out job may still be using: any
        # query issued here would wait for its lock (psycopg serializes access
        # to a connection), and that wait could never end
        backend_pid = self.db.conn_query.discard()
        if backend_pid is None:
            return
        # Terminating the backend releases the locks and rolls back whatever the
        # job managed to write, so the result can be stored on the new connection
        LOG.warning('Terminating the backend of the timed-out job (pid: %s)',
                    backend_pid)
        self._execute(
            query=self.queries.query_terminate_backend(),
            pid=backend_pid,
        )
        self._commit()

    def _start_command(self, command: PersistentCommand, attempt_number: int) -> bool:
        # The attempt is stored before the work starts: if the worker dies while
        # processing, the command must not be retried immediately nor forever
        self.db.execute_query(
            query=self.queries.query_command_start(),
            attempts=attempt_number,
            updated_at=datetime.datetime.now(tz=datetime.UTC),
            uuid=command.uuid,
        )
        self._commit()
        # Committing released the lock from SELECT ... FOR UPDATE, it needs to be
        # taken again and held for the whole processing (otherwise another worker
        # could process the very same command concurrently)
        try:
            self._execute(
                query=self.queries.query_lock_command(),
                uuid=command.uuid,
            )
        except psycopg.errors.LockNotAvailable:
            LOG.warning('Command %s is locked by someone else, skipping it',
                        command.uuid)
            self._rollback()
            return False
        self._execute(query=self.queries.query_savepoint())
        return True

    def _do_work(self, command: PersistentCommand):
        def work():
            self.worker.work(command)

        if self.work_timeout is None:
            LOG.info('Processing (without any timeout set)')
            work()
            return

        LOG.info('Processing (with timeout set to %s seconds)',
                 self.work_timeout)
        thread = _CommandJobThread(work=work)
        thread.start()
        thread.join(timeout=self.work_timeout)
        if thread.is_alive():
            raise CommandJobTimeoutError(timeout=self.work_timeout)
        if thread.exception is not None:
            raise thread.exception

    def _store_result(self, *, query: str, message: str, attempts: int, uuid: str):
        self.db.execute_query(
            query=query,
            attempts=attempts,
            error_message=message,
            updated_at=datetime.datetime.now(tz=datetime.UTC),
            uuid=uuid,
        )
        self._commit()

    def _execute(self, query: str, **params):
        with self.db.conn_query.new_cursor() as cursor:
            cursor.execute(query=query, params=params or None)

    def _commit(self):
        LOG.debug('Committing transaction')
        self.db.conn_query.connection.commit()

    def _rollback(self):
        LOG.debug('Rolling back transaction')
        try:
            self.db.conn_query.connection.rollback()
        except psycopg.Error:
            LOG.warning('Failed to roll back the transaction', exc_info=True)

    def _rollback_work(self):
        # Changes made by the failed job must not become durable together with
        # its error record (the job itself may have already ended the
        # transaction, then there is nothing to roll back to)
        try:
            self._execute(query=self.queries.query_rollback_to_savepoint())
            return
        except psycopg.Error as e:
            LOG.info('Could not roll back to savepoint (%s), rolling back fully',
                     str(e))
        self._rollback()

    def _signal_handler(self, recv_signal, frame):
        LOG.warning('Received interrupt signal: %s (frame: %s)',
                    recv_signal, frame)
        self._interrupted = True
