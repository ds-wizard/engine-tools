from dsw.config import DSWConfigParser
from dsw.config.model import DatabaseConfig, S3Config, \
    LoggingConfig, SentryConfig, CloudConfig, GeneralConfig


class SeederConfig:

    def __init__(self, db: DatabaseConfig, s3: S3Config, log: LoggingConfig,
                 sentry: SentryConfig, cloud: CloudConfig, general: GeneralConfig):
        self.general = general
        self.db = db
        self.s3 = s3
        self.log = log
        self.sentry = sentry
        self.cloud = cloud

    def __str__(self):
        return f'SeederConfig\n' \
               f'====================\n' \
               f'{self.general}' \
               f'{self.db}' \
               f'{self.s3}' \
               f'{self.log}' \
               f'{self.sentry}' \
               f'{self.cloud}' \
               f'====================\n'


class SeederConfigParser(DSWConfigParser):

    @property
    def config(self) -> SeederConfig:
        return SeederConfig(
            db=self.db,
            s3=self.s3,
            log=self.logging,
            sentry=self.sentry,
            cloud=self.cloud,
            general=self.general,
        )
