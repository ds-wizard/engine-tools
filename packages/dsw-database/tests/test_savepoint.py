"""Query attempts run in their own savepoint, so a failed one can be retried.

The unit tests use a fake connection that records statements. The integration tests need a
PostgreSQL database and run only when ``DSW_TEST_DATABASE_URL`` is set, e.g.
``postgresql://postgres:postgres@localhost:5432/postgres``; they create only temporary tables.
"""
import os

import psycopg
import psycopg.pq
import pytest
import tenacity

from dsw.config.model import DatabaseConfig
from dsw.database.database import Database, PostgresConnection, _in_savepoint


INERROR = psycopg.pq.TransactionStatus.INERROR
INTRANS = psycopg.pq.TransactionStatus.INTRANS
IDLE = psycopg.pq.TransactionStatus.IDLE


class FakeCursor:

    def __init__(self, log: list[str], conn: 'FakeConnection'):
        self.log = log
        self.conn = conn

    def execute(self, query, params=None):
        text = query if isinstance(query, str) else query.as_string()
        self.log.append(text)
        if 'ROLLBACK TO' in text:
            self.conn.info.transaction_status = INTRANS

    def close(self):
        pass


class FakeInfo:
    transaction_status = INTRANS


class FakeConnection:

    def __init__(self):
        self.log: list[str] = []
        self.info = FakeInfo()
        self.closed = 0

    def cursor(self, **kwargs):
        return FakeCursor(self.log, self)


def fake_connection() -> tuple[PostgresConnection, FakeConnection]:
    connection = PostgresConnection(name='test', dsn='postgresql://', autocommit=False)
    fake = FakeConnection()
    connection._connection = fake
    return connection, fake


def test_successful_block_releases_savepoint():
    connection, fake = fake_connection()
    with connection.savepoint():
        pass
    assert fake.log == ['SAVEPOINT "dsw_query";', 'RELEASE SAVEPOINT "dsw_query";']


def test_failed_block_rolls_back_to_savepoint_and_raises_again():
    connection, fake = fake_connection()
    with pytest.raises(RuntimeError), connection.savepoint():
        fake.info.transaction_status = INERROR
        raise RuntimeError('query failed')
    assert fake.log == ['SAVEPOINT "dsw_query";', 'ROLLBACK TO SAVEPOINT "dsw_query";',
                        'RELEASE SAVEPOINT "dsw_query";']


def test_error_caught_inside_block_is_rolled_back_too():
    connection, fake = fake_connection()
    with connection.savepoint():
        fake.info.transaction_status = INERROR  # a statement failed, the block caught it
    assert 'ROLLBACK TO SAVEPOINT "dsw_query";' in fake.log
    assert fake.info.transaction_status == INTRANS


def test_block_that_commits_ends_the_savepoint():
    connection, fake = fake_connection()
    with connection.savepoint():
        fake.info.transaction_status = IDLE  # e.g. update_component_info commits
    assert fake.log == ['SAVEPOINT "dsw_query";']


def test_autocommit_connection_has_no_savepoint():
    connection = PostgresConnection(name='test', dsn='postgresql://', autocommit=True)
    with connection.savepoint():
        pass  # no connection needed at all


# integration

DATABASE_URL = os.environ.get('DSW_TEST_DATABASE_URL')
integration = pytest.mark.skipif(DATABASE_URL is None, reason='DSW_TEST_DATABASE_URL is not set')
RETRY = tenacity.retry(reraise=True, stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_none())


class FlakyDatabase(Database):
    """A query that fails on its first attempt, decorated like every query of Database."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attempts = 0

    def _flaky_query(self) -> int:
        self.attempts += 1
        table = 'no_such_table' if self.attempts == 1 else 'pg_class'
        with self.conn_query.new_cursor() as cursor:
            cursor.execute(f'SELECT 1 FROM {table} LIMIT 1;')
            return cursor.fetchone()[0]

    @RETRY
    @_in_savepoint
    def flaky(self) -> int:
        return self._flaky_query()

    @RETRY
    def flaky_without_savepoint(self) -> int:
        return self._flaky_query()


@pytest.fixture
def database():
    db = FlakyDatabase(DatabaseConfig(connection_string=DATABASE_URL, connection_timeout=5,
                                      queue_timeout=5), with_queue=False)
    yield db
    db.conn_query.connection.rollback()
    db.conn_query.close()


@integration
def test_failed_attempt_keeps_the_job_transaction(database):
    connection = database.conn_query
    with connection.new_cursor() as cursor:
        cursor.execute('CREATE TEMP TABLE job_work (x int);')
        cursor.execute('INSERT INTO job_work VALUES (1);')  # the job's work so far
    with pytest.raises(psycopg.errors.UndefinedTable), connection.savepoint(), \
            connection.new_cursor() as cursor:
        cursor.execute('SELECT * FROM no_such_table;')
    assert connection.connection.info.transaction_status == INTRANS
    with connection.new_cursor() as cursor:
        cursor.execute('SELECT count(*) FROM job_work;')
        assert cursor.fetchone()[0] == 1


@integration
def test_retried_query_succeeds_after_a_failed_attempt(database):
    assert database.flaky() == 1
    assert database.attempts == 2


@integration
def test_without_savepoint_the_retry_only_sees_the_aborted_transaction(database):
    # what the worker logged before: the real error was replaced by this one
    with pytest.raises(psycopg.errors.InFailedSqlTransaction):
        database.flaky_without_savepoint()


@integration
def test_missing_tenant_limit_table_means_no_limit(database):
    with database.conn_query.new_cursor() as cursor:
        cursor.execute("SELECT to_regclass('tenant_limit_bundle') IS NULL;")
        if not cursor.fetchone()[0]:
            pytest.skip('the test database has a tenant_limit_bundle table')
    assert database.fetch_tenant_limits('00000000-0000-0000-0000-000000000000') is None
    assert database.conn_query.connection.info.transaction_status != INERROR


@integration
def test_committing_query_leaves_a_usable_connection(database):
    with database.conn_query.savepoint(), database.conn_query.new_cursor() as cursor:
        cursor.execute('SELECT 1;')
        database.conn_query.connection.commit()
    assert database.conn_query.connection.info.transaction_status == IDLE
    with database.conn_query.new_cursor() as cursor:
        cursor.execute('SELECT 1;')
        assert cursor.fetchone()[0] == 1
