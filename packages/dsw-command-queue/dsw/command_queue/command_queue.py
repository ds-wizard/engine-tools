import abc
import datetime
import logging
import os
import platform
import select
import signal

import func_timeout
import psycopg
import psycopg.generators
import tenacity

from dsw.database import Database
from dsw.database.model import PersistentCommand

from .query import CommandQueries

LOG = logging.getLogger(__name__)

RETRY_QUERY_MULTIPLIER = 0.5
RETRY_QUERY_TRIES = 3
RETRY_QUEUE_MULTIPLIER = 0.5
RETRY_QUEUE_TRIES = 5

IS_LINUX = platform == 'Linux'

if IS_LINUX:
    _QUEUE_PIPE_R, _QUEUE_PIPE_W = os.pipe()
    signal.set_wakeup_fd(_QUEUE_PIPE_W)


class CommandJobError(BaseException):

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


class CommandWorker:

    @abc.abstractmethod
    def work(self, command: PersistentCommand):
        pass

    def process_timeout(self, e: BaseException):
        pass

    def process_exception(self, e: BaseException):
        pass


class CommandQueue:

    def __init__(self, *, worker: CommandWorker, db: Database,
                 channel: str, component: str, wait_timeout: float,
                 work_timeout: int | None = None):
        self.worker = worker
        self.db = db
        self.queries = CommandQueries(
            channel=channel,
            component=component
        )
        self.wait_timeout = wait_timeout
        self.work_timeout = work_timeout
        self._interrupted = False

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGABRT, self._signal_handler)

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUEUE_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUEUE_TRIES),
        before=tenacity.before_log(LOG, logging.INFO),
        after=tenacity.after_log(LOG, logging.INFO),
    )
    def run(self):
        LOG.info('Preparing to listen to command queue')
        queue_conn = self.db.conn_queue
        queue_conn.connection.execute(
            query=self.queries.query_listen(),
        )
        queue_conn.listening = True
        LOG.info('Listening to notifications in command queue')
        fds = [queue_conn.connection.pgconn.socket]
        if IS_LINUX:
            fds.append(_QUEUE_PIPE_R)

        while True:
            self._fetch_and_process_queued()

            LOG.debug('Waiting for notifications')
            w = select.select(fds, [], [], self.wait_timeout)

            if self._interrupted:
                LOG.debug('Interrupt signal received, ending...')
                break

            if w == ([], [], []):
                LOG.debug('Nothing received in this cycle (timeout %s seconds)',
                          self.wait_timeout)
            else:
                notifications = 0
                for n in psycopg.generators.notifies(queue_conn.connection.pgconn):
                    notifications += 1
                    LOG.debug(str(n))
                LOG.info('Notifications received (%s in total)', notifications)
        LOG.debug('Exiting command queue')

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUEUE_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUEUE_TRIES),
        before=tenacity.before_log(LOG, logging.INFO),
        after=tenacity.after_log(LOG, logging.INFO),
    )
    def run_once(self):
        LOG.info('Processing the command queue once')
        self._fetch_and_process_queued()

    def _fetch_and_process_queued(self):
        LOG.info('Fetching the commands')
        count = 0
        while self.fetch_and_process():
            count += 1
        LOG.info('There are no more commands to process (%s processed)',
                 count)

    def accept_notification(self, payload: psycopg.Notify) -> bool:
        LOG.debug('Accepting notification from channel "%s" (PID = %s) %s',
                  payload.channel, payload.pid, payload.payload)
        LOG.debug('Trying to fetch a new job')
        return self.fetch_and_process()

    def fetch_and_process(self) -> bool:
        cursor = self.db.conn_query.new_cursor(use_dict=True)
        cursor.execute(
            query=self.queries.query_get_command(),
            params={'now': datetime.datetime.now(tz=datetime.UTC)},
        )
        result = cursor.fetchall()
        if len(result) != 1:
            LOG.debug('Fetched %s persistent commands', len(result))
            return False

        command = PersistentCommand.from_dict_row(result[0])
        LOG.info('Retrieved persistent command %s for processing', command.uuid)
        LOG.debug('Previous state: %s', command.state)
        LOG.debug('Attempts: %s / %s', command.attempts, command.max_attempts)
        LOG.debug('Last error: %s', command.last_error_message)

        self._process(command)

        LOG.debug('Committing transaction')
        self.db.conn_query.connection.commit()
        cursor.close()
        LOG.info('Notification processing finished')
        return True

    def _process(self, command: PersistentCommand):
        attempt_number = command.attempts + 1
        try:
            self.db.execute_query(
                query=self.queries.query_command_start(),
                attempts=attempt_number,
                updated_at=datetime.datetime.now(tz=datetime.UTC),
                uuid=command.uuid,
            )
            self.db.conn_query.connection.commit()

            def work():
                self.worker.work(command)

            if self.work_timeout is None:
                LOG.info('Processing (without any timeout set)')
                work()
            else:
                LOG.info('Processing (with timeout set to %s seconds)',
                         self.work_timeout)
                func_timeout.func_timeout(
                    timeout=self.work_timeout,
                    func=work,
                    args=(),
                    kwargs=None,
                )

            self.db.execute_query(
                query=self.queries.query_command_done(),
                attempts=attempt_number,
                updated_at=datetime.datetime.now(tz=datetime.UTC),
                uuid=command.uuid,
            )
        except func_timeout.exceptions.FunctionTimedOut as e:
            msg = f'Processing exceeded time limit ({self.work_timeout} seconds)'
            LOG.warning(msg)
            self.worker.process_timeout(e)
            self.db.execute_query(
                query=self.queries.query_command_error(),
                attempts=attempt_number,
                error_message=msg,
                updated_at=datetime.datetime.now(tz=datetime.UTC),
                uuid=command.uuid,
            )
        except CommandJobError as e:
            if e.try_again and attempt_number < command.max_attempts:
                query = self.queries.query_command_error()
                msg = f'Failed with job error: {e.message} (will try again)'
            else:
                query = self.queries.query_command_error_stop()
                msg = f'Failed with job error: {e.message}'
            LOG.warning(msg)
            self.worker.process_exception(e)
            self.db.execute_query(
                query=query,
                attempts=attempt_number,
                error_message=msg,
                updated_at=datetime.datetime.now(tz=datetime.UTC),
                uuid=command.uuid,
            )
        except Exception as e:
            if attempt_number < command.max_attempts:
                msg = f'Failed with exception [{type(e).__name__}]: {str(e)} (will try again)'
            else:
                msg = f'Failed with exception [{type(e).__name__}]: {str(e)}'
            LOG.warning(msg)
            self.worker.process_exception(e)
            self.db.execute_query(
                query=self.queries.query_command_error(),
                attempts=attempt_number,
                error_message=msg,
                updated_at=datetime.datetime.now(tz=datetime.UTC),
                uuid=command.uuid,
            )

    def _signal_handler(self, recv_signal, frame):
        LOG.warning('Received interrupt signal: %s (frame: %s)',
                    recv_signal, frame)
        self._interrupted = True
