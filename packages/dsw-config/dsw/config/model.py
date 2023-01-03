from typing import Optional


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

    def __init__(self, enabled: bool, workers_dsn: Optional[str]):
        self.enabled = enabled
        self.workers_dsn = workers_dsn


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

    def __init__(self, level: str, global_level: str, message_format: str):
        self.level = level
        self.global_level = global_level
        self.message_format = message_format


class CloudConfig(ConfigModel):

    def __init__(self, multi_tenant: bool):
        self.multi_tenant = multi_tenant


class MailConfig(ConfigModel):

    def __init__(self, enabled: bool, ssl: Optional[bool], name: str, email: str,
                 host: str, port: Optional[int], security: Optional[str],
                 auth: Optional[bool], username: Optional[str],
                 password: Optional[str], rate_limit_window: int,
                 rate_limit_count: int, timeout: int):
        self.enabled = enabled
        self.name = name
        self.email = email
        self.host = host
        self.security = 'plain'
        if security is not None:
            self.security = security.lower()
        elif ssl is not None:
            self.security = 'ssl' if ssl else 'plain'
        self.port = port or self._default_port()
        self.auth = auth or (username is not None and password is not None)
        self.username = username if self.auth is not None else None
        self.password = password if self.auth is not None else None
        self.rate_limit_window = rate_limit_window
        self.rate_limit_count = rate_limit_count
        self.timeout = timeout

    @property
    def login_user(self) -> str:
        return self.username or ''

    @property
    def login_password(self) -> str:
        return self.password or ''

    @property
    def is_plain(self):
        return self.security == 'plain'

    @property
    def is_ssl(self):
        return self.security == 'ssl'

    @property
    def is_tls(self):
        return self.security == 'starttls' or self.security == 'tls'

    def _default_port(self) -> int:
        if self.is_plain:
            return 25
        if self.is_ssl:
            return 465
        return 587

    def has_credentials(self) -> bool:
        return self.username is not None and self.password is not None

    def __str__(self):
        return f'MailConfig\n' \
               f'- enabled = {self.enabled}\n' \
               f'- name = {self.name}\n' \
               f'- email = {self.email}\n' \
               f'- host = {self.host}\n' \
               f'- port = {self.port}\n' \
               f'- security = {self.security}\n' \
               f'- auth = {self.auth}\n' \
               f'- rate_limit_window = {self.rate_limit_window}\n' \
               f'- rate_limit_count = {self.rate_limit_count}\n' \
               f'- timeout = {self.timeout}\n'
