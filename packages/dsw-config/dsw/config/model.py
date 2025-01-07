import dataclasses

from .logging import prepare_logging, LOG_FILTER


def _config_to_string(config: object):
    lines = [f'{type(config).__name__}']
    fields = (f for f in config.__dict__.keys() if not f.startswith('_'))
    for field in fields:
        v = str(getattr(config, field))
        t = type(getattr(config, field)).__name__
        lines.append(f'- {field} = {v} [{t}]')
    return '\n'.join(lines)


class ConfigModel:

    def __str__(self):
        return _config_to_string(self)


@dataclasses.dataclass
class GeneralConfig(ConfigModel):
    environment: str
    client_url: str
    secret: str


@dataclasses.dataclass
class SentryConfig(ConfigModel):
    enabled: bool
    workers_dsn: str | None
    traces_sample_rate: float | None
    max_breadcrumbs: int | None
    environment: str


@dataclasses.dataclass
class DatabaseConfig(ConfigModel):
    connection_string: str
    connection_timeout: int
    queue_timeout: int


@dataclasses.dataclass
class S3Config(ConfigModel):
    url: str
    username: str
    password: str
    bucket: str
    region: str


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

    @property
    def has_credentials(self) -> bool:
        return self.access_key_id is not None and self.secret_access_key is not None


@dataclasses.dataclass
class CloudConfig(ConfigModel):
    multi_tenant: bool
