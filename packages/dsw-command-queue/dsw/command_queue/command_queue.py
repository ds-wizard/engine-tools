import abc
import datetime
import logging
import os
import platform
import signal

import psycopg
import tenacity

from dsw.database import Database
from dsw.database.model import PersistentCommand

from .query import CommandQueries

LOG = logging.getLogger(__name__)

RETRY_QUERY_MULTIPLIER = 0.5
RETRY_QUERY_TRIES = 3
RETRY_QUEUE_MULTIPLIER = 0.5
RETRY_QUEUE_TRIES = 5


class CommandWorker:

    @abc.abstractmethod
    def work(self, cmd: PersistentCommand):
        pass

    def process_exception(self, exc: Exception):
        pass


class CommandQueue:

    _INSTANCES = []  # type: list[CommandQueue]

    @classmethod
    def interrupt_all(cls):
        for instance in cls._INSTANCES:
            instance.interrupt()

    def __init__(self, worker: CommandWorker, db: Database,
                 channel: str, component: str):
        CommandQueue._INSTANCES.append(self)
        self.worker = worker
        self.db = db
        self._queries = CommandQueries(
            channel=channel,
            component=component
        )
        self._interrupted = False

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUEUE_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUEUE_TRIES),
        before=tenacity.before_log(LOG, logging.INFO),
        after=tenacity.after_log(LOG, logging.INFO),
    )
    def run(self):
        LOG.info('Trying queued jobs before listening')
        while self.fetch_and_process():
            pass
        LOG.info('Preparing to listen for jobs in command queue')
        queue_conn = self.db.conn_queue
        queue_conn.connection.execute(
            query=self._queries.query_listen(),
        )
        queue_conn.listening = True
        LOG.info('Listening for jobs in command queue')
        running = True
        while running:
            queue_notifications = queue_conn.connection.notifies()
            LOG.info('Entering working cycle, waiting for notifications')
            for notification in queue_notifications:
                LOG.info('Notification received')
                while self.accept_notification(payload=notification):
                    pass

                if self._interrupted:
                    LOG.debug('Interrupt signal received, ending...')
                    queue_notifications.close()
                    running = False
        LOG.debug('Exiting command queue')

    def accept_notification(self, payload: psycopg.Notify) -> bool:
        LOG.debug('Accepting notification from channel "%s" (PID = %s) %s',
                  payload.channel, payload.pid, payload.payload)
        LOG.debug('Trying to fetch a new job')
        return self.fetch_and_process()

    def fetch_and_process(self) -> bool:
        cursor = self.db.conn_query.new_cursor(use_dict=True)
        cursor.execute(
            query=self._queries.query_get_command(),
            params={'now': datetime.datetime.utcnow()},
        )
        result = cursor.fetchall()
        if len(result) != 1:
            LOG.debug('Fetched %d persistent commands', len(result))
            return False

        command = PersistentCommand.from_dict_row(result[0])
        LOG.info('Retrieved persistent command %s for processing', command.uuid)
        LOG.debug('Previous state: %s', command.state)
        LOG.debug('Attempts: %d / %d', command.attempts, command.max_attempts)
        LOG.debug('Last error: %s', command.last_error_message)

        try:
            self.worker.work(command)

            self.db.execute_query(
                query=self._queries.query_command_done(),
                attempts=command.attempts + 1,
                updated_at=datetime.datetime.utcnow(),
                uuid=command.uuid,
            )
        except Exception as exc:
            msg = f'Failed with exception: {str(exc)} ({type(exc).__name__})'
            LOG.warning(msg)
            self.worker.process_exception(exc)
            self.db.execute_query(
                query=self._queries.query_command_error(),
                attempts=command.attempts + 1,
                error_message=msg,
                updated_at=datetime.datetime.utcnow(),
                uuid=command.uuid,
            )

        LOG.debug('Committing transaction')
        self.db.conn_query.connection.commit()
        cursor.close()
        LOG.info('Notification processing finished')
        return True

    def interrupt(self):
        self.db.conn_queue.connection.cancel()


# Interruption handling
IS_LINUX = platform == 'Linux'

if IS_LINUX:
    _QUEUE_PIPE_R, _QUEUE_PIPE_W = os.pipe()
    signal.set_wakeup_fd(_QUEUE_PIPE_W)


def signal_handler(recv_signal, frame):
    LOG.warning('Received interrupt signal: %s (frame: %s)',
                recv_signal, frame)
    CommandQueue.interrupt_all()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGABRT, signal_handler)
