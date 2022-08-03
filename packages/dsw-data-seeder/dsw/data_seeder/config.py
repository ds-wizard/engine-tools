from dsw.config import DSWConfigParser
from dsw.config.model import DatabaseConfig, S3Config, \
    LoggingConfig, CloudConfig


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


class SeederConfigParser(DSWConfigParser):

    @property
    def config(self) -> SeederConfig:
        return SeederConfig(
            db=self.db,
            s3=self.s3,
            log=self.logging,
            cloud=self.cloud,
        )
