from typing import Optional

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


class GeneralConfig(ConfigModel):

    def __init__(self, environment: str, client_url: str, secret: str):
        self.environment = environment
        self.client_url = client_url
        self.secret = secret


class SentryConfig(ConfigModel):

    def __init__(self, enabled: bool, workers_dsn: Optional[str],
                 traces_sample_rate: Optional[float], max_breadcrumbs: Optional[int]):
        self.enabled = enabled
        self.workers_dsn = workers_dsn
        self.traces_sample_rate = traces_sample_rate
        self.max_breadcrumbs = max_breadcrumbs


class DatabaseConfig(ConfigModel):

    def __init__(self, connection_string: str, connection_timeout: int, queue_timout: int):
        self.connection_string = connection_string
        self.connection_timeout = connection_timeout
        self.queue_timout = queue_timout


class S3Config(ConfigModel):

    def __init__(self, url: str, username: str, password: str,
                 bucket: str, region: str):
        self.url = url
        self.username = username
        self.password = password
        self.bucket = bucket
        self.region = region


class LoggingConfig(ConfigModel):

    def __init__(self, level: str, global_level: str, message_format: str,
                 dict_config: Optional[dict] = None):
        self.level = level
        self.global_level = global_level
        self.message_format = message_format
        self.dict_config = dict_config

    def apply(self):
        prepare_logging(self)

    @staticmethod
    def set_logging_extra(key: str, value: str):
        LOG_FILTER.set_extra(key, value)


class AWSConfig(ConfigModel):

    def __init__(self, access_key_id: Optional[str], secret_access_key: Optional[str],
                 region: Optional[str]):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region

    @property
    def has_credentials(self) -> bool:
        return self.access_key_id is not None and self.secret_access_key is not None


class CloudConfig(ConfigModel):

    def __init__(self, multi_tenant: bool):
        self.multi_tenant = multi_tenant
