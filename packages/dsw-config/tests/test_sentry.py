import dataclasses
import logging

import pytest
import sentry_sdk

from dsw.config.model import SentryConfig
from dsw.config.sentry import SentryReporter


def make_config(*, enabled: bool, dsn: str | None) -> SentryConfig:
    return SentryConfig(
        enabled=enabled,
        workers_dsn=dsn,
        traces_sample_rate=None,
        max_breadcrumbs=None,
        environment='test',
    )


@pytest.fixture(autouse=True)
def _reset_reporter():
    yield
    SentryReporter.report = False


def test_not_reporting_when_disabled():
    SentryReporter.initialize(
        config=make_config(enabled=False, dsn='https://token@sentry.io/1'),
        component='test',
        release='0.0.0',
    )
    assert SentryReporter.report is False


@pytest.mark.parametrize('dsn', [None, ''])
def test_not_reporting_without_dsn(caplog, dsn):
    with caplog.at_level(logging.WARNING):
        SentryReporter.initialize(
            config=make_config(enabled=True, dsn=dsn),
            component='test',
            release='0.0.0',
        )
    assert SentryReporter.report is False
    assert 'no DSN' in caplog.text


@dataclasses.dataclass
class FakeCommand:
    uuid: str = '8a7d1f0e-3b2c-4d5e-9f60-7182a3b4c5d6'
    function: str = 'generateDocument'
    tenant_uuid: str = '00000000-0000-0000-0000-000000000000'
    created_by: str | None = 'c1d2e3f4-a5b6-4c7d-8e9f-0a1b2c3d4e5f'
    attempts: int = 1
    max_attempts: int = 10


@pytest.fixture
def captured():
    events = []

    def capture(event, _hint):
        events.append(event)
        return None

    SentryReporter.initialize(
        config=make_config(enabled=True, dsn='https://token@sentry.example.org/1'),
        component='document_worker',
        release='v4.0.0~abc1234',
    )
    SentryReporter.filters.append(capture)
    yield events
    SentryReporter.filters.remove(capture)
    sentry_sdk.get_isolation_scope().clear()
    sentry_sdk.get_client().close()


def test_command_tags_match_backend(captured):
    command = FakeCommand()
    SentryReporter.set_command(command)
    SentryReporter.capture_message('failed')

    event = captured[-1]
    assert event['environment'] == 'test'
    assert event['release'] == 'v4.0.0~abc1234'
    assert event['tags'] == {
        'component': 'document_worker',
        'function': 'generateDocument',
        'tenantUuid': command.tenant_uuid,
        'traceUuid': command.uuid,
    }
    assert event['user'] == {'id': command.created_by}
    assert event['extra']['maxAttempts'] == '10'
    assert event['contexts']['trace']['trace_id'] == command.uuid.replace('-', '')


def test_command_tenant_override(captured):
    SentryReporter.set_command(FakeCommand(), tenant_uuid='t')
    SentryReporter.capture_message('failed')
    assert captured[-1]['tags']['tenantUuid'] == 't'


def test_reset_command(captured):
    command = FakeCommand()
    SentryReporter.set_command(command)
    SentryReporter.reset_command()
    SentryReporter.capture_message('failed')

    event = captured[-1]
    assert event['tags'] == {'component': 'document_worker'}
    assert 'user' not in event
    assert event['contexts']['trace']['trace_id'] != command.uuid.replace('-', '')
