import os
import typing

import yaml

from .keys import ConfigKey, ConfigKeys
from .model import GeneralConfig, SentryConfig, S3Config, \
    DatabaseConfig, LoggingConfig, CloudConfig, AWSConfig


class MissingConfigurationError(Exception):

    def __init__(self, missing: list[str]):
        self.missing = missing


class DSWConfigParser:

    def __init__(self, keys=ConfigKeys):
        self.cfg = {}
        self.keys = keys

    @staticmethod
    def can_read(content: str):
        try:
            yaml.load(content, Loader=yaml.FullLoader)
            return True
        except Exception:
            return False

    def read_file(self, fp: typing.IO):
        self.cfg = yaml.load(fp, Loader=yaml.FullLoader) or self.cfg

    def read_string(self, content: str):
        self.cfg = yaml.load(content, Loader=yaml.FullLoader) or self.cfg

    def has_value_for_path(self, yaml_path: list[str]):
        x = self.cfg
        for p in yaml_path:
            if not hasattr(x, 'keys') or p not in x.keys():
                return False
            x = x[p]
        return True

    @staticmethod
    def _prefix_var(var_name: str) -> str:
        return f'DSW_{var_name}'

    def has_value_for_key(self, key: ConfigKey):
        if self.has_value_for_path(key.yaml_path):
            return True
        for var_name in key.var_names:
            if var_name in os.environ or self._prefix_var(var_name) in os.environ:
                return True
        return False

    def get_or_default(self, key: ConfigKey):
        x: typing.Any = self.cfg
        for p in key.yaml_path:
            if not hasattr(x, 'keys') or p not in x.keys():
                return key.default
            x = x[p]
        return x

    def get(self, key: ConfigKey):
        for var_name in key.var_names:
            if var_name in os.environ:
                return key.cast(os.environ[var_name])
            if self._prefix_var(var_name) in os.environ:
                return key.cast(os.environ[self._prefix_var(var_name)])
        return key.cast(self.get_or_default(key))

    def validate(self):
        missing = []
        for key in self.keys:
            if key.required and not self.has_value_for_key(key):
                missing.append('.'.join(key.yaml_path))
        if len(missing) > 0:
            raise MissingConfigurationError(missing)

    @property
    def db(self) -> DatabaseConfig:
        return DatabaseConfig(
            connection_string=self.get(self.keys.database.connection_string),
            connection_timeout=self.get(self.keys.database.connection_timeout),
            queue_timeout=self.get(self.keys.database.queue_timeout),
        )

    @property
    def s3(self) -> S3Config:
        return S3Config(
            url=self.get(self.keys.s3.url),
            username=self.get(self.keys.s3.username),
            password=self.get(self.keys.s3.password),
            bucket=self.get(self.keys.s3.bucket),
            region=self.get(self.keys.s3.region),
        )

    @property
    def logging(self) -> LoggingConfig:
        return LoggingConfig(
            level=self.get(self.keys.logging.level),
            global_level=self.get(self.keys.logging.global_level),
            message_format=self.get(self.keys.logging.format),
            dict_config=self.get(self.keys.logging.dict_config),
        )

    @property
    def cloud(self) -> CloudConfig:
        return CloudConfig(
            multi_tenant=self.get(self.keys.cloud.enabled),
        )

    @property
    def sentry(self) -> SentryConfig:
        return SentryConfig(
            enabled=self.get(self.keys.sentry.enabled),
            workers_dsn=self.get(self.keys.sentry.worker_dsn),
            traces_sample_rate=self.get(self.keys.sentry.traces_sample_rate),
            max_breadcrumbs=self.get(self.keys.sentry.max_breadcrumbs),
            environment=self.get(self.keys.sentry.environment),
        )

    @property
    def general(self) -> GeneralConfig:
        return GeneralConfig(
            environment=self.get(self.keys.general.environment),
            client_url=self.get(self.keys.general.client_url),
            secret=self.get(self.keys.general.secret),
        )

    @property
    def aws(self) -> AWSConfig:
        return AWSConfig(
            access_key_id=self.get(self.keys.aws.access_key_id),
            secret_access_key=self.get(self.keys.aws.secret_access_key),
            region=self.get(self.keys.aws.region),
        )
