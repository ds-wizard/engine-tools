import yaml

from typing import List, Optional


class MissingConfigurationError(Exception):

    def __init__(self, missing: List[str]):
        self.missing = missing


class GeneralConfig:

    def __init__(self, environment: str, client_url: str):
        self.environment = environment
        self.client_url = client_url

    def __str__(self):
        return f'GeneralConfig\n' \
               f'- environment = {self.environment} ({type(self.environment)})\n' \
               f'- client_url = {self.client_url} ({type(self.client_url)})\n'


class SentryConfig:

    def __init__(self, enabled: bool, workers_dsn: Optional[str]):
        self.enabled = enabled
        self.workers_dsn = workers_dsn

    def __str__(self):
        return f'SentryConfig\n' \
               f'- enabled = {self.enabled} ({type(self.enabled)})\n' \
               f'- workers_dsn = {self.workers_dsn} ({type(self.workers_dsn)})\n'


class DatabaseConfig:

    def __init__(self, connection_string: str, connection_timeout: int,
                 queue_timout: int):
        self.connection_string = connection_string
        self.connection_timeout = connection_timeout
        self.queue_timout = queue_timout

    def __str__(self):
        return f'DatabaseConfig\n' \
               f'- connection_string = {self.connection_string} ' \
               f'({type(self.connection_string)})\n' \
               f'- connection_timeout = {self.connection_timeout} ' \
               f'({type(self.connection_timeout)})\n' \
               f'- queue_timout = {self.queue_timout} ({type(self.queue_timout)})\n'


class LoggingConfig:

    def __init__(self, level: str, global_level: str, message_format: str):
        self.level = level
        self.global_level = global_level
        self.message_format = message_format

    def __str__(self):
        return f'LoggingConfig\n' \
               f'- level = {self.level} ({type(self.level)})\n' \
               f'- message_format = {self.message_format} ' \
               f'({type(self.message_format)})\n'


class MailConfig:

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
               f'- rate_limit_count = {self.rate_limit_count}\n'


class MailerConfig:

    def __init__(self, db: DatabaseConfig, log: LoggingConfig,
                 mail: MailConfig, sentry: SentryConfig,
                 general: GeneralConfig):
        self.db = db
        self.log = log
        self.mail = mail
        self.sentry = sentry
        self.general = general

    def __str__(self):
        return f'MailerConfig\n' \
               f'====================\n' \
               f'{self.db}' \
               f'{self.log}' \
               f'{self.mail}' \
               f'{self.sentry}' \
               f'{self.general}' \
               f'====================\n'


class MailerConfigParser:

    DB_SECTION = 'database'
    LOGGING_SECTION = 'logging'
    MAIL_SECTION = 'mail'
    SENTRY_SECTION = 'sentry'
    GENERAL_SECTION = 'general'

    DEFAULTS = {
        DB_SECTION: {
            'connectionString': 'postgresql://postgres:postgres@'
                                'postgres:5432/engine-wizard',
            'connectionTimeout': 30000,
            'queueTimeout': 120,
        },
        LOGGING_SECTION: {
            'level': 'INFO',
            'globalLevel': 'WARNING',
            'format': '%(asctime)s | %(levelname)8s | %(name)s: '
                      '[T:%(traceId)s] %(message)s',
        },
        MAIL_SECTION: {
            'enabled': True,
            'name': 'DS Wizard',
            'email': '',
            'host': '',
            'port': None,
            'ssl': None,
            'security': None,
            'authEnabled': False,
            'username': None,
            'password': None,
            'rateLimit': {
                'window': 0,
                'count': 0,
            },
            'timeout': 5,
        },
        SENTRY_SECTION: {
            'enabled': False,
            'workersDsn': None
        },
        GENERAL_SECTION: {
            'environment': 'Production',
            'clientUrl': 'http://localhost:8080',
        },
    }

    REQUIRED = [
        [MAIL_SECTION, 'email'],
        [MAIL_SECTION, 'host'],
        [MAIL_SECTION, 'port'],
    ]

    def __init__(self):
        self.cfg = dict()

    @staticmethod
    def can_read(content):
        try:
            yaml.load(content, Loader=yaml.FullLoader)
            return True
        except Exception:
            return False

    def read_file(self, fp):
        self.cfg = yaml.load(fp, Loader=yaml.FullLoader)

    def read_string(self, content):
        self.cfg = yaml.load(content, Loader=yaml.FullLoader)

    def has(self, *path):
        x = self.cfg
        for p in path:
            if not hasattr(x, 'keys') or p not in x.keys():
                return False
            x = x[p]
        return True

    def _get_default(self, *path):
        x = self.DEFAULTS
        for p in path:
            x = x[p]
        return x

    def get_or_default(self, *path):
        x = self.cfg
        for p in path:
            if not hasattr(x, 'keys') or p not in x.keys():
                return self._get_default(*path)
            x = x[p]
        return x

    def validate(self):
        missing = []
        for path in self.REQUIRED:
            if not self.has(*path):
                missing.append('.'.join(path))
        if len(missing) > 0:
            raise MissingConfigurationError(missing)

    @property
    def db(self) -> DatabaseConfig:
        return DatabaseConfig(
            connection_string=self.get_or_default(
                self.DB_SECTION, 'connectionString'
            ),
            connection_timeout=self.get_or_default(
                self.DB_SECTION, 'connectionTimeout'
            ),
            queue_timout=self.get_or_default(
                self.DB_SECTION, 'queueTimeout'
            ),
        )

    @property
    def logging(self) -> LoggingConfig:
        return LoggingConfig(
            level=self.get_or_default(self.LOGGING_SECTION, 'level'),
            global_level=self.get_or_default(self.LOGGING_SECTION, 'globalLevel'),
            message_format=self.get_or_default(self.LOGGING_SECTION, 'format'),
        )

    @property
    def mail(self):
        return MailConfig(
            enabled=self.get_or_default(self.MAIL_SECTION, 'enabled'),
            name=self.get_or_default(self.MAIL_SECTION, 'name'),
            email=self.get_or_default(self.MAIL_SECTION, 'email'),
            host=self.get_or_default(self.MAIL_SECTION, 'host'),
            ssl=self.get_or_default(self.MAIL_SECTION, 'ssl'),
            port=self.get_or_default(self.MAIL_SECTION, 'port'),
            security=self.get_or_default(self.MAIL_SECTION, 'security'),
            auth=self.get_or_default(self.MAIL_SECTION, 'authEnabled'),
            username=self.get_or_default(self.MAIL_SECTION, 'username'),
            password=self.get_or_default(self.MAIL_SECTION, 'password'),
            rate_limit_window=self.get_or_default(
                self.MAIL_SECTION, 'rateLimit', 'window'
            ),
            rate_limit_count=self.get_or_default(
                self.MAIL_SECTION, 'rateLimit', 'count'
            ),
            timeout=int(self.get_or_default(self.MAIL_SECTION, 'timeout')),
        )

    @property
    def sentry(self) -> SentryConfig:
        return SentryConfig(
            enabled=self.get_or_default(self.SENTRY_SECTION, 'enabled'),
            workers_dsn=self.get_or_default(self.SENTRY_SECTION, 'workersDsn'),
        )

    @property
    def general(self) -> GeneralConfig:
        return GeneralConfig(
            environment=self.get_or_default(self.GENERAL_SECTION, 'environment'),
            client_url=self.get_or_default(self.GENERAL_SECTION, 'clientUrl'),
        )

    @property
    def config(self) -> MailerConfig:
        return MailerConfig(
            db=self.db,
            log=self.logging,
            mail=self.mail,
            sentry=self.sentry,
            general=self.general,
        )
