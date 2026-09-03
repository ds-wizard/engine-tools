import pytest

from dsw.command_queue.query import CommandQueries


TABLE = 'persistent_command'

TABLE_QUERIES = [
    'query_get_command',
    'query_lock_command',
    'query_command_error',
    'query_command_error_stop',
    'query_command_done',
    'query_command_start',
]


def make_queries(table_prefix: str = 'w_') -> CommandQueries:
    return CommandQueries(channel='doc_worker', table_prefix=table_prefix)


@pytest.mark.parametrize('query_name', TABLE_QUERIES)
def test_command_queries_are_prefixed(query_name):
    query = getattr(make_queries(), query_name)()
    assert f'w_{TABLE}' in query
    assert '{' not in query


@pytest.mark.parametrize('query_name', TABLE_QUERIES)
def test_command_queries_without_prefix(query_name):
    query = getattr(make_queries(table_prefix=''), query_name)()
    assert TABLE in query
    assert '{' not in query


def test_listen_channel_is_not_prefixed():
    # the notification channel is a constant in the engine, not a table name
    assert make_queries().query_listen() == (
        'LISTEN persistent_command_channel__doc_worker;'
    )


def test_queries_without_tables_are_unaffected():
    queries = make_queries()
    assert queries.query_terminate_backend() == 'SELECT pg_terminate_backend(%(pid)s);'
    assert queries.query_savepoint() == 'SAVEPOINT dsw_command_job;'
    assert queries.query_rollback_to_savepoint() == 'ROLLBACK TO SAVEPOINT dsw_command_job;'
