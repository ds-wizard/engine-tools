from __future__ import annotations

import logging
import typing
import uuid

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


if typing.TYPE_CHECKING:
    from sentry_sdk.types import Event, Hint

    from .model import SentryConfig

    EventProcessor = typing.Callable[[Event, Hint], Event | None]


LOG = logging.getLogger(__name__)


class Command(typing.Protocol):
    uuid: str
    function: str
    tenant_uuid: str
    created_by: str | None
    attempts: int
    max_attempts: int


class SentryReporter:
    report = False
    filters: list[EventProcessor] = []

    @classmethod
    def initialize(cls, *, config: SentryConfig, component: str, release: str,
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
            sentry_sdk.set_tag('component', component)

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

    @classmethod
    def set_command(cls, command: Command, *, tenant_uuid: str | None = None):
        """Tag events with the persistent command being processed, the way the backend does.

        The command UUID is the trace UUID of the job (it is the `traceId` in the logs).
        """
        if not cls.report:
            return
        sentry_sdk.set_tags({
            'function': command.function,
            'tenantUuid': tenant_uuid or command.tenant_uuid,
            'traceUuid': command.uuid,
        })
        sentry_sdk.set_extra('uuid', command.uuid)
        sentry_sdk.set_extra('attempts', str(command.attempts))
        sentry_sdk.set_extra('maxAttempts', str(command.max_attempts))
        sentry_sdk.set_user({'id': command.created_by} if command.created_by else None)
        trace_id = _to_trace_id(command.uuid)
        if trace_id is not None:
            sentry_sdk.continue_trace({'sentry-trace': f'{trace_id}-{trace_id[:16]}'})

    @classmethod
    def reset_command(cls):
        if not cls.report:
            return
        scope = sentry_sdk.get_isolation_scope()
        for tag in ('function', 'tenantUuid', 'traceUuid'):
            scope.remove_tag(tag)
        for extra in ('uuid', 'attempts', 'maxAttempts'):
            scope.remove_extra(extra)
        scope.set_user(None)
        scope.set_new_propagation_context()


def _to_trace_id(value: str) -> str | None:
    try:
        return uuid.UUID(value).hex
    except ValueError:
        return None
