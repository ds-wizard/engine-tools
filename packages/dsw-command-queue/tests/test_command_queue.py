"""A failed command is handed back to the backend only when it will be tried again."""
import pytest

from dsw.command_queue.command_queue import (
    CommandJobError,
    CommandJobTimeoutError,
    CommandQueue,
    CommandWorker,
    FatalCommandQueueError,
    ProcessResult,
)
from dsw.command_queue.query import CommandQueries
from dsw.database.model import PersistentCommand


class FailingWorker(CommandWorker):

    def __init__(self, error: Exception | None):
        self.error = error

    def work(self, command: PersistentCommand):
        if self.error is not None:
            raise self.error


class FakeDatabase:

    def __init__(self):
        self.queries: list[str] = []

    def execute_query(self, query: str, **kwargs):
        self.queries.append(query)


def make_command(attempts: int, max_attempts: int = 3) -> PersistentCommand:
    return PersistentCommand(
        uuid='cmd-1', state='NewPersistentCommandState', component='mailer',
        function='sendMail', body={}, last_error_message=None, attempts=attempts,
        max_attempts=max_attempts, tenant_uuid='tenant', created_by=None,
        created_at=None, updated_at=None,
    )


def process(monkeypatch, error: Exception | None, attempts: int) -> tuple[list[str], object]:
    queue = CommandQueue.__new__(CommandQueue)
    queue.worker = FailingWorker(error)
    queue.db = FakeDatabase()
    queue.queries = CommandQueries(channel='mailer')
    queue.work_timeout = 10
    monkeypatch.setattr(queue, '_start_command', lambda **_: True)
    monkeypatch.setattr(queue, '_commit', lambda: None)
    monkeypatch.setattr(queue, '_rollback_work', lambda: None)
    monkeypatch.setattr(queue, '_abandon_connection', lambda: None)
    if isinstance(error, CommandJobTimeoutError):
        def time_out(_):
            raise error
        monkeypatch.setattr(queue, '_do_work', time_out)
        with pytest.raises(FatalCommandQueueError):
            queue._process(make_command(attempts=attempts))
        return queue.db.queries, None
    result = queue._process(make_command(attempts=attempts))
    return queue.db.queries, result


ERRORS = [
    ValueError('boom'),
    CommandJobError(job_id='cmd-1', message='boom', try_again=True),
    CommandJobTimeoutError(timeout=10),
]


@pytest.mark.parametrize('error', ERRORS, ids=lambda e: type(e).__name__)
def test_failure_with_attempts_left_clears_lambda_invoked(monkeypatch, error):
    queries, _ = process(monkeypatch, error, attempts=0)
    assert queries == [CommandQueries.query_command_error()]
    assert 'lambda_invoked = FALSE' in queries[0]


@pytest.mark.parametrize('error', ERRORS, ids=lambda e: type(e).__name__)
def test_failure_of_last_attempt_keeps_lambda_invoked(monkeypatch, error):
    queries, _ = process(monkeypatch, error, attempts=2)
    assert queries == [CommandQueries.query_command_error_stop()]
    assert 'lambda_invoked' not in queries[0]


def test_failure_without_retry_keeps_lambda_invoked(monkeypatch):
    error = CommandJobError(job_id='cmd-1', message='boom', try_again=False)
    queries, _ = process(monkeypatch, error, attempts=0)
    assert queries == [CommandQueries.query_command_error_stop()]


def test_success_keeps_lambda_invoked(monkeypatch):
    queries, result = process(monkeypatch, None, attempts=0)
    assert result is ProcessResult.DONE
    assert queries == [CommandQueries.query_command_done()]
    assert 'lambda_invoked' not in queries[0]
