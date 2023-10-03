from dsw.config import DSWConfigParser
from dsw.config.keys import ConfigKey, cast_str, cast_int
from dsw.config.model import DatabaseConfig, S3Config, \
    LoggingConfig, SentryConfig, CloudConfig, GeneralConfig


class SeederConfig:

    def __init__(self, db: DatabaseConfig, s3: S3Config, log: LoggingConfig,
                 sentry: SentryConfig, cloud: CloudConfig, general: GeneralConfig,
                 extra_dbs: dict[str, DatabaseConfig]):
        self.general = general
        self.db = db
        self.s3 = s3
        self.log = log
        self.sentry = sentry
        self.cloud = cloud
        self.extra_dbs = extra_dbs

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
    def extra_dbs(self) -> dict[str, DatabaseConfig]:
        result = {}
        for db_id, val in self.cfg.get('extraDatabases', {}).items():
            result[db_id] = DatabaseConfig(
                connection_string=self.get(
                    key=ConfigKey(
                        yaml_path=['extraDatabases', db_id, 'connectionString'],
                        var_names=[],
                        default=f'postgresql://postgres:postgres@postgres:5432/{db_id}',
                        cast=cast_str,
                    )
                ),
                connection_timeout=self.get(
                    key=ConfigKey(
                        yaml_path=['extraDatabases', db_id, 'connectionTimeout'],
                        var_names=[],
                        default=30000,
                        cast=cast_int,
                    )
                ),
                queue_timout=0,
            )

        return result

    @property
    def config(self) -> SeederConfig:
        return SeederConfig(
            db=self.db,
            s3=self.s3,
            log=self.logging,
            sentry=self.sentry,
            cloud=self.cloud,
            general=self.general,
            extra_dbs=self.extra_dbs,
        )
