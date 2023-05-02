import abc
import datetime
import logging
import os
import platform
import psycopg
import signal
import tenacity

from dsw.database import Database
from dsw.database.model import PersistentCommand

from .query import CommandQueries

LOG = logging.getLogger(__name__)

RETRY_QUERY_MULTIPLIER = 0.5
RETRY_QUERY_TRIES = 3
RETRY_QUEUE_MULTIPLIER = 0.5
RETRY_QUEUE_TRIES = 5

INTERRUPTED = False
IS_LINUX = platform == 'Linux'

if IS_LINUX:
    _QUEUE_PIPE_R, _QUEUE_PIPE_W = os.pipe()
    signal.set_wakeup_fd(_QUEUE_PIPE_W)


def signal_handler(recv_signal, frame):
    global INTERRUPTED
    LOG.warning(f'Received interrupt signal: {recv_signal}')
    INTERRUPTED = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGABRT, signal_handler)


class CommandWorker:

    @abc.abstractmethod
    def work(self, payload: PersistentCommand):
        pass

    def process_exception(self, e: Exception):
        pass


class CommandQueue:

    def __init__(self, worker: CommandWorker, db: Database,
                 channel: str, component: str):
        self.worker = worker
        self.db = db
        self.queries = CommandQueries(
            channel=channel,
            component=component
        )

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
            query=self.queries.query_listen(),
        )
        queue_conn.listening = True
        LOG.info('Listening for jobs in command queue')
        running = True
        while running:
            queue_notifications = queue_conn.connection.notifies()
            LOG.info('Entering working cycle, waiting for notifications')
            for notification in queue_notifications:
                LOG.info(f'Notification received: {notification}')
                while self.accept_notification(payload=notification):
                    pass

                if INTERRUPTED:
                    LOG.debug('Interrupt signal received, ending...')
                    queue_notifications.close()
                    running = False
        LOG.debug('Exiting command queue')

    def accept_notification(self, payload: psycopg.Notify) -> bool:
        LOG.debug(f'Accepting notification from channel "{payload.channel}" '
                  f'(PID = {payload.pid}) {payload.payload}')
        LOG.debug('Trying to fetch a new job')
        return self.fetch_and_process()

    def fetch_and_process(self) -> bool:
        cursor = self.db.conn_query.new_cursor(use_dict=True)
        cursor.execute(
            query=self.queries.query_get_command(),
            params={'now': datetime.datetime.utcnow()},
        )
        result = cursor.fetchall()
        if len(result) != 1:
            LOG.debug(f'Fetched {len(result)} persistent commands')
            return False

        command = PersistentCommand.from_dict_row(result[0])
        LOG.info(f'Retrieved persistent command {command.uuid} for processing')
        LOG.debug(f'Previous state: {command.state}')
        LOG.debug(f'Attempts: {command.attempts} / {command.max_attempts}')
        LOG.debug(f'Last error: {command.last_error_message}')

        try:
            self.worker.work(command)

            self.db.execute_query(
                query=self.queries.query_command_done(),
                attempts=command.attempts + 1,
                updated_at=datetime.datetime.utcnow(),
                uuid=command.uuid,
            )
        except Exception as e:
            msg = f'Failed with exception: {str(e)} ({type(e).__name__})'
            LOG.warning(msg)
            self.worker.process_exception(e)
            self.db.execute_query(
                query=self.queries.query_command_error(),
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
