import abc
import logging
import os
import platform
import select
import signal
import tenacity

from dsw.database import Database

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
    def work(self) -> bool:
        pass


class CommandQueue:

    def __init__(self, worker: CommandWorker, db: Database, listen_query: str):
        self.worker = worker
        self.db = db
        self.listen_query = listen_query

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUEUE_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUEUE_TRIES),
        before=tenacity.before_log(LOG, logging.INFO),
        after=tenacity.after_log(LOG, logging.INFO),
    )
    def run(self):
        LOG.info('Preparing to listen for jobs in command queue')
        queue_conn = self.db.conn_queue
        # Prepare file descriptors
        fds = [queue_conn.connection]
        if IS_LINUX:
            fds.append(_QUEUE_PIPE_R)
        # Query queue
        with queue_conn.new_cursor() as cursor:
            cursor.execute(self.listen_query)
            queue_conn.listening = True
            LOG.info('Listening for jobs in command queue')

            notifications = list()  # type: list[str]
            timeout = self.db.cfg.queue_timout

            LOG.info('Entering working cycle, waiting for notifications')
            while True:
                while self.worker.work():
                    pass

                LOG.debug('Waiting for new notifications')
                notifications.clear()
                if not queue_conn.listening:
                    cursor.execute(self.listen_query)
                    queue_conn.listening = True

                w = select.select(fds, [], [], timeout)

                if INTERRUPTED:
                    LOG.debug('Interrupt signal received, ending...')
                    break

                if w == ([], [], []):
                    LOG.debug(f'Nothing received in this cycle '
                              f'(timeouted after {timeout} seconds).')
                else:
                    queue_conn.connection.poll()
                    while queue_conn.connection.notifies:
                        notifications.append(queue_conn.connection.notifies.pop())
                    LOG.info(f'Notifications received ({len(notifications)})')
                    LOG.debug(f'Notifications: {notifications}')
    LOG.debug('The End')
