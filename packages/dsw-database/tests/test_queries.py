import re

import pytest

from dsw.config.model import DatabaseConfig
from dsw.database.database import Database


# Tables referenced by a query must be prefixed; these targets must not be.
TABLE_REFERENCE = re.compile(r'\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z_][a-zA-Z0-9_.]*)')
NOT_A_TABLE = frozenset({'set', 'information_schema.tables'})

TEST_PREFIX = 'test_'


def query_templates() -> dict[str, str]:
    return {
        name: value for name, value in vars(Database).items()
        if name.isupper() and isinstance(value, str)
    }


def make_config(table_prefix: str) -> DatabaseConfig:
    return DatabaseConfig(
        connection_string='postgresql://user:pass@db:5432/dsw',
        connection_timeout=30000,
        queue_timeout=180,
        table_prefix=table_prefix,
    )


def referenced_tables(query: str) -> list[str]:
    return [
        table for table in TABLE_REFERENCE.findall(query)
        if table.lower() not in NOT_A_TABLE
    ]


def test_there_are_queries_to_check():
    assert len(query_templates()) > 10


@pytest.mark.parametrize('name', sorted(query_templates()))
def test_query_has_no_unresolved_placeholder(name):
    query = make_config(TEST_PREFIX).prepare_query(query_templates()[name])
    assert '{' not in query
    assert '}' not in query


@pytest.mark.parametrize('name', sorted(query_templates()))
def test_query_tables_are_prefixed(name):
    query = make_config(TEST_PREFIX).prepare_query(query_templates()[name])
    tables = referenced_tables(query)
    assert all(table.startswith(TEST_PREFIX) for table in tables), tables


@pytest.mark.parametrize('name', sorted(query_templates()))
def test_query_without_prefix_keeps_plain_table_names(name):
    query = make_config('').prepare_query(query_templates()[name])
    assert '{' not in query
    for table in referenced_tables(query):
        assert not table.startswith('_')


def test_query_uses_the_configured_prefix():
    query = make_config('w_').prepare_query(Database.SELECT_DOCUMENT)
    assert query == ('SELECT * FROM w_document '
                     'WHERE uuid = %s AND tenant_uuid = %s LIMIT 1;')
