import logging

import pytest

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
        prog_name='test',
        release='0.0.0',
    )
    assert SentryReporter.report is False


@pytest.mark.parametrize('dsn', [None, ''])
def test_not_reporting_without_dsn(caplog, dsn):
    with caplog.at_level(logging.WARNING):
        SentryReporter.initialize(
            config=make_config(enabled=True, dsn=dsn),
            prog_name='test',
            release='0.0.0',
        )
    assert SentryReporter.report is False
    assert 'no DSN' in caplog.text
