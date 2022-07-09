import yaml

from typing import List


class MissingConfigurationError(Exception):

    def __init__(self, missing: List[str]):
        self.missing = missing


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


class S3Config:

    def __init__(self, url: str, username: str, password: str,
                 bucket: str, region: str):
        self.url = url
        self.username = username
        self.password = password
        self.bucket = bucket
        self.region = region

    def __str__(self):
        return f'S3Config\n' \
               f'- url = {self.url} ({type(self.url)})\n' \
               f'- username = {self.username} ({type(self.username)})\n' \
               f'- password = {self.password} ({type(self.password)})\n' \
               f'- bucket = {self.bucket} ({type(self.bucket)})\n' \
               f'- region = {self.region} ({type(self.region)})\n'


class LoggingConfig:

    def __init__(self, level: str, global_level: str, message_format: str):
        self.level = level.upper()
        self.global_level = global_level
        self.message_format = message_format

    def __str__(self):
        return f'LoggingConfig\n' \
               f'- level = {self.level} ({type(self.level)})\n' \
               f'- global_level = {self.global_level} ({type(self.global_level)})\n' \
               f'- message_format = {self.message_format} ({type(self.message_format)})\n'


class CloudConfig:

    def __init__(self, multi_tenant: bool):
        self.multi_tenant = multi_tenant

    def __str__(self):
        return f'CloudConfig\n' \
               f'- multi_tenant = {self.multi_tenant} ({type(self.multi_tenant)})\n'


class SeederConfig:

    def __init__(self, db: DatabaseConfig, s3: S3Config, log: LoggingConfig,
                 cloud: CloudConfig):
        self.db = db
        self.s3 = s3
        self.log = log
        self.cloud = cloud

    def __str__(self):
        return f'SeederConfig\n' \
               f'====================\n' \
               f'{self.db}' \
               f'{self.s3}' \
               f'{self.log}' \
               f'{self.cloud}' \
               f'====================\n'


class SeederConfigParser:

    DB_SECTION = 'database'
    S3_SECTION = 's3'
    LOGGING_SECTION = 'logging'
    SEED_SECTION = 'seed'
    CLOUD_SECTION = 'cloud'

    DEFAULTS = {
        DB_SECTION: {
            'connectionString': 'postgresql://postgres:postgres@'
                                'postgres:5432/engine-wizard',
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
            'format': '%(asctime)s | %(levelname)8s | %(name)s: '
                      '[T:%(traceId)s] %(message)s',
        },
        CLOUD_SECTION: {
            'enabled': False,
        },
    }

    REQUIRED = []  # type: list[str]

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
    def config(self) -> SeederConfig:
        return SeederConfig(
            db=self.db,
            s3=self.s3,
            log=self.logging,
            cloud=self.cloud,
        )
