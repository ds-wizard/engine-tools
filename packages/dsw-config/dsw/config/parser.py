import yaml

from typing import List

from .model import GeneralConfig, SentryConfig, S3Config, \
    DatabaseConfig, LoggingConfig, CloudConfig, MailConfig


class MissingConfigurationError(Exception):

    def __init__(self, missing: List[str]):
        self.missing = missing


class DSWConfigParser:

    DB_SECTION = 'database'
    S3_SECTION = 's3'
    LOGGING_SECTION = 'logging'
    CLOUD_SECTION = 'cloud'
    SENTRY_SECTION = 'sentry'
    GENERAL_SECTION = 'general'
    MAIL_SECTION = 'mail'

    DEFAULTS = {
        DB_SECTION: {
            'connectionString': 'postgresql://postgres:postgres@postgres:5432/engine-wizard',
            'connectionTimeout': 30000,
            'queueTimeout': 120,
        },
        S3_SECTION: {
            'url': 'http://minio:9000',
            'vhost': 'minio',
            'queue': 'minio',
            'bucket': 'engine-wizard',
            'region': 'eu-central-1',
        },
        LOGGING_SECTION: {
            'level': 'INFO',
            'globalLevel': 'WARNING',
            'format': '%(asctime)s | %(levelname)8s | %(name)s: [T:%(traceId)s] %(message)s',
        },
        CLOUD_SECTION: {
            'enabled': False,
        },
        SENTRY_SECTION: {
            'enabled': False,
            'workersDsn': None
        },
        GENERAL_SECTION: {
            'environment': 'Production',
            'clientUrl': 'http://localhost:8080',
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
    }

    REQUIRED = []  # type: List[str]

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
            connection_string=self.get_or_default(self.DB_SECTION, 'connectionString'),
            connection_timeout=self.get_or_default(self.DB_SECTION, 'connectionTimeout'),
            queue_timout=self.get_or_default(self.DB_SECTION, 'queueTimeout'),
        )

    @property
    def s3(self) -> S3Config:
        return S3Config(
            url=self.get_or_default(self.S3_SECTION, 'url'),
            username=self.get_or_default(self.S3_SECTION, 'username'),
            password=self.get_or_default(self.S3_SECTION, 'password'),
            bucket=self.get_or_default(self.S3_SECTION, 'bucket'),
            region=self.get_or_default(self.S3_SECTION, 'region'),
        )

    @property
    def logging(self) -> LoggingConfig:
        return LoggingConfig(
            level=self.get_or_default(self.LOGGING_SECTION, 'level'),
            global_level=self.get_or_default(self.LOGGING_SECTION, 'globalLevel'),
            message_format=self.get_or_default(self.LOGGING_SECTION, 'format'),
        )

    @property
    def cloud(self) -> CloudConfig:
        return CloudConfig(
            multi_tenant=self.get_or_default(self.CLOUD_SECTION, 'enabled'),
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
