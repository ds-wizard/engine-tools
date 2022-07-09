import dataclasses
import datetime
import json
import logging
import psycopg2  # type: ignore
import psycopg2.extensions  # type: ignore
import psycopg2.extras  # type: ignore
import tenacity

from ..config import DatabaseConfig
from ..consts import NULL_UUID
from ..context import Context

from typing import Optional, Iterable

ISOLATION_DEFAULT = psycopg2.extensions.ISOLATION_LEVEL_DEFAULT
ISOLATION_AUTOCOMMIT = psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT

RETRY_QUERY_MULTIPLIER = 0.5
RETRY_QUERY_TRIES = 3

RETRY_CONNECT_MULTIPLIER = 0.2
RETRY_CONNECT_TRIES = 10


@dataclasses.dataclass
class PersistentCommand:
    uuid: str
    state: str
    component: str
    function: str
    body: dict
    last_error_message: Optional[str]
    attempts: int
    max_attempts: int
    app_uuid: str
    created_by: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @staticmethod
    def deserialize(data: dict):
        return PersistentCommand(
            uuid=data['uuid'],
            state=data['state'],
            component=data['component'],
            function=data['function'],
            body=json.loads(data['body']),
            last_error_message=data['last_error_message'],
            attempts=data['attempts'],
            max_attempts=data['max_attempts'],
            created_by=data['created_by'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            app_uuid=data.get('app_uuid', NULL_UUID),
        )


class Database:

    def __init__(self, cfg: DatabaseConfig):
        self.cfg = cfg
        Context.logger.info('Preparing PostgreSQL connection for QUERY')
        self.conn_query = PostgresConnection(
            name='query',
            dsn=self.cfg.connection_string,
            timeout=self.cfg.connection_timeout,
            autocommit=False,
        )
        self.conn_query.connect()
        Context.logger.info('Preparing PostgreSQL connection for QUEUE')
        self.conn_queue = PostgresConnection(
            name='queue',
            dsn=self.cfg.connection_string,
            timeout=self.cfg.connection_timeout,
            autocommit=True,
        )
        self.conn_queue.connect()

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(Context.logger, logging.DEBUG),
        after=tenacity.after_log(Context.logger, logging.DEBUG),
    )
    def execute_queries(self, queries: Iterable[str]):
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            for query in queries:
                cursor.execute(query=query)

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(Context.logger, logging.DEBUG),
        after=tenacity.after_log(Context.logger, logging.DEBUG),
    )
    def execute_query(self, query: str, **kwargs):
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(query=query, vars=kwargs)


class PostgresConnection:

    def __init__(self, name: str, dsn: str, timeout=30000, autocommit=False):
        self.name = name
        self.listening = False
        self.dsn = psycopg2.extensions.make_dsn(dsn, connect_timeout=timeout)
        self.isolation = ISOLATION_AUTOCOMMIT if autocommit else ISOLATION_DEFAULT
        self._connection = None

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_CONNECT_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_CONNECT_TRIES),
        before=tenacity.before_log(Context.logger, logging.DEBUG),
        after=tenacity.after_log(Context.logger, logging.DEBUG),
    )
    def _connect_db(self):
        Context.logger.info(f'Creating connection to PostgreSQL database "{self.name}"')
        connection = psycopg2.connect(dsn=self.dsn)
        connection.set_isolation_level(self.isolation)
        # test connection
        cursor = connection.cursor()
        cursor.execute(query='SELECT uuid FROM persistent_command;')
        result = cursor.fetchall()
        Context.logger.debug(f'Connection verified [{len(result)}]')
        cursor.close()
        self._connection = connection
        self.listening = False

    def connect(self):
        if not self._connection or self._connection.closed != 0:
            self._connect_db()

    @property
    def connection(self):
        self.connect()
        return self._connection

    def new_cursor(self, use_dict: bool = False):
        return self.connection.cursor(
            cursor_factory=psycopg2.extras.DictCursor if use_dict else None,
        )

    def reset(self):
        self.close()
        self.connect()

    def close(self):
        if self._connection:
            Context.logger.info(f'Closing connection to PostgreSQL database "{self.name}"')
            self._connection.close()
        self._connection = None
