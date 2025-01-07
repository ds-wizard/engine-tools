import logging
import typing

import sentry_sdk
from sentry_sdk.types import Event, Hint
from sentry_sdk.integrations.logging import LoggingIntegration

from .model import SentryConfig


EventProcessor = typing.Callable[[Event, Hint], typing.Optional[Event]]


class SentryReporter:
    report = False
    filters = []  # type: list[EventProcessor]

    @classmethod
    def initialize(cls, *, config: SentryConfig, prog_name: str, release: str,
                   breadcrumb_level: int | None = logging.INFO,
                   event_level: int | None = logging.ERROR):
        cls.report = config.enabled and config.workers_dsn is not None
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
