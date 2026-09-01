from __future__ import annotations

import dataclasses
import typing

from .logging import LOG_FILTER, prepare_logging


MASKED_VALUE = '***'


def _config_to_string(config: object):
    lines = [f'{type(config).__name__}']
    secret_fields = getattr(config, '_secret_fields', ())
    fields = (f for f in config.__dict__ if not f.startswith('_'))
    for field in fields:
        value = getattr(config, field)
        v = MASKED_VALUE if field in secret_fields and value is not None else str(value)
        t = type(value).__name__
        lines.append(f'- {field} = {v} [{t}]')
    return '\n'.join(lines)


class ConfigModel:
    # names of fields that must never be printed (credentials, secrets, DSNs)
    _secret_fields: typing.ClassVar[tuple[str, ...]] = ()

    def __str__(self):
        return _config_to_string(self)


@dataclasses.dataclass
class GeneralConfig(ConfigModel):
    environment: str
    client_url: str
    secret: str

    _secret_fields = ('secret',)


@dataclasses.dataclass
class SentryConfig(ConfigModel):
    enabled: bool
    workers_dsn: str | None
    traces_sample_rate: float | None
    max_breadcrumbs: int | None
    environment: str

    _secret_fields = ('workers_dsn',)


@dataclasses.dataclass
class DatabaseConfig(ConfigModel):
    connection_string: str
    connection_timeout: int
    queue_timeout: int

    _secret_fields = ('connection_string',)


@dataclasses.dataclass
class S3Config(ConfigModel):
    url: str
    username: str
    password: str
    bucket: str
    region: str

    _secret_fields = ('password',)


@dataclasses.dataclass
class LoggingConfig(ConfigModel):
    level: str
    global_level: str
    message_format: str
    dict_config: dict | None = None

    def apply(self):
        prepare_logging(self)

    @staticmethod
    def set_logging_extra(key: str, value: str):
        LOG_FILTER.set_extra(key, value)


@dataclasses.dataclass
class AWSConfig(ConfigModel):
    access_key_id: str | None
    secret_access_key: str | None
    region: str | None

    _secret_fields = ('access_key_id', 'secret_access_key')

    @property
    def has_credentials(self) -> bool:
        return self.access_key_id is not None and self.secret_access_key is not None


@dataclasses.dataclass
class CloudConfig(ConfigModel):
    multi_tenant: bool
