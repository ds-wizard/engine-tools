import sentry_sdk

from .model import SentryConfig


class SentryReporter:
    report = False

    @classmethod
    def initialize(cls, dsn: str, server_name: str, environment: str,
                   prog_name: str, release: str, config: SentryConfig):
        cls.report = config.enabled and config.workers_dsn is not None
        if cls.report:
            sentry_sdk.init(
                dsn=dsn,
                traces_sample_rate=config.traces_sample_rate or 1.0,
                max_breadcrumbs=config.max_breadcrumbs or sentry_sdk.consts.DEFAULT_MAX_BREADCRUMBS,
                release=release,
                server_name=server_name,
                environment=environment,
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
    def set_context(cls, name: str, value):
        if cls.report:
            sentry_sdk.set_context(name, value)
