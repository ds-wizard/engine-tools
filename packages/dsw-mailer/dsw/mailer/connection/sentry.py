import sentry_sdk

from ..build_info import BUILD_INFO
from ..consts import PROG_NAME


class SentryReporter:

    @classmethod
    def initialize(cls, dsn: str, server_name: str, environment: str):
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=1.0,
            release=BUILD_INFO.version,
            server_name=server_name,
            environment=environment,
        )
        sentry_sdk.set_tag('worker', PROG_NAME)

    @staticmethod
    def capture_exception(*args, **kwargs):
        sentry_sdk.capture_exception(*args, **kwargs)

    @staticmethod
    def capture_message(*args, **kwargs):
        sentry_sdk.capture_message(*args, **kwargs)
