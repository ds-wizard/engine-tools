import types

import pytest

from dsw.document_worker.config import DocumentsConfig
from dsw.document_worker.context import Context
from dsw.document_worker.exceptions import JobError
from dsw.document_worker.limits import COMMAND_LIMITS_KEY, LimitsEnforcer


@pytest.fixture
def with_max_size(tmp_path):
    original = Context._instance

    def initialize(max_size: int | None):
        config = types.SimpleNamespace(
            doc=DocumentsConfig(naming_strategy='sanitize', max_size=max_size),
        )
        Context.initialize(db=None, s3=None, config=config, workdir=tmp_path)

    yield initialize
    Context._instance = original


def test_limit_from_command_body():
    doc_context = {'document': {}, COMMAND_LIMITS_KEY: {'storage': 3_000_000}}
    assert LimitsEnforcer.take_storage_limit(doc_context) == 3_000_000
    assert COMMAND_LIMITS_KEY not in doc_context


@pytest.mark.parametrize('doc_context', [
    {},
    {COMMAND_LIMITS_KEY: None},
    {COMMAND_LIMITS_KEY: {}},
    {COMMAND_LIMITS_KEY: {'storage': None}},
])
def test_no_limit_from_command_body(doc_context):
    assert LimitsEnforcer.take_storage_limit(doc_context) is None
    assert COMMAND_LIMITS_KEY not in doc_context


def test_size_usage_within_limit():
    LimitsEnforcer.check_size_usage('job', doc_size=100, used_size=800, limit_size=1_000)
    LimitsEnforcer.check_size_usage('job', doc_size=10**9, used_size=10**9, limit_size=None)


def test_size_usage_over_limit():
    with pytest.raises(JobError, match='No space left'):
        LimitsEnforcer.check_size_usage('job', doc_size=300, used_size=800, limit_size=1_000)


def test_doc_size_within_max_size(with_max_size):
    with_max_size(5_000_000)
    LimitsEnforcer.check_doc_size('job', doc_size=5_000_000)


def test_doc_size_over_max_size(with_max_size):
    with_max_size(5_000_000)
    with pytest.raises(JobError, match='exceeded size limit'):
        LimitsEnforcer.check_doc_size('job', doc_size=5_000_001)


def test_doc_size_without_max_size(with_max_size):
    with_max_size(None)
    LimitsEnforcer.check_doc_size('job', doc_size=10**12)
