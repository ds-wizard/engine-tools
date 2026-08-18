from __future__ import annotations

import logging
import typing

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


if typing.TYPE_CHECKING:
    from sentry_sdk.types import Event, Hint

    from .model import SentryConfig

    EventProcessor = typing.Callable[[Event, Hint], Event | None]


LOG = logging.getLogger(__name__)


class SentryReporter:
    report = False
    filters: list[EventProcessor] = []

    @classmethod
    def initialize(cls, *, config: SentryConfig, prog_name: str, release: str,
                   breadcrumb_level: int | None = logging.INFO,
                   event_level: int | None = logging.ERROR):
        if config.enabled and not config.workers_dsn:
            LOG.warning('Sentry is enabled but no DSN is configured, '
                        'no events will be reported')
        cls.report = config.enabled and bool(config.workers_dsn)
        if cls.report:
            def before_send(event, hint):
                for f in cls.filters:
                    if not f(event, hint):
                        return None
                return event

            sentry_sdk.init(
                dsn=config.workers_dsn,
                traces_sample_rate=config.traces_sample_rate or 1.0,
                max_breadcrumbs=config.max_breadcrumbs or sentry_sdk.consts.DEFAULT_MAX_BREADCRUMBS,
                release=release,
                environment=config.environment,
                before_send=before_send,
                default_integrations=False,
                integrations=[
                    LoggingIntegration(
                        level=breadcrumb_level,
                        event_level=event_level,
                    ),
                ],
            )
            sentry_sdk.set_tag('component', prog_name)

    @classmethod
    def capture_exception(cls, *args, **kwargs):
        if cls.report:
            sentry_sdk.capture_exception(*args, **kwargs)

    @classmethod
    def capture_message(cls, *args, **kwargs):
        if cls.report:
            sentry_sdk.capture_message(*args, **kwargs)

    @classmethod
    def set_tags(cls, **tags):
        if cls.report:
            sentry_sdk.set_tags(tags)
