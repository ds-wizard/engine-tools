import dataclasses

from dsw.config import DSWConfigParser
from dsw.config.keys import ConfigKey, ConfigKeys, ConfigKeysContainer, \
    cast_str, cast_int, cast_optional_int
from dsw.config.model import ConfigModel, DatabaseConfig, S3Config, \
    LoggingConfig, SentryConfig, CloudConfig, GeneralConfig


# pylint: disable-next=too-few-public-methods
class _ExperimentalKeys(ConfigKeysContainer):
    job_timeout = ConfigKey(
        yaml_path=['experimental', 'jobTimeout'],
        var_names=['EXPERIMENTAL_JOB_TIMEOUT'],
        default=None,
        cast=cast_optional_int,
    )


# pylint: disable-next=too-few-public-methods
class MailerConfigKeys(ConfigKeys):
    experimental = _ExperimentalKeys


@dataclasses.dataclass
class ExperimentalConfig(ConfigModel):
    job_timeout: int | None


@dataclasses.dataclass
class SeederConfig:
    db: DatabaseConfig
    s3: S3Config
    log: LoggingConfig
    sentry: SentryConfig
    cloud: CloudConfig
    general: GeneralConfig
    extra_dbs: dict[str, DatabaseConfig]
    extra_s3s: dict[str, S3Config]
    experimental: ExperimentalConfig

    def __str__(self):
        return f'SeederConfig\n' \
               f'====================\n' \
               f'{self.general}' \
               f'{self.db}' \
               f'{self.s3}' \
               f'{self.log}' \
               f'{self.sentry}' \
               f'{self.cloud}' \
               f'{self.experimental}' \
               f'====================\n'


class SeederConfigParser(DSWConfigParser):

    def __init__(self):
        super().__init__(keys=MailerConfigKeys)
        self.keys = MailerConfigKeys  # type: type[MailerConfigKeys]

    @property
    def extra_dbs(self) -> dict[str, DatabaseConfig]:
        result = {}
        for db_id in self.cfg.get('extraDatabases', {}).keys():
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
                queue_timeout=0,
            )

        return result

    @property
    def extra_s3s(self) -> dict[str, S3Config]:
        result = {}
        for s3_id in self.cfg.get('extraS3s', {}).keys():
            result[s3_id] = S3Config(
                url=self.get(
                    key=ConfigKey(
                        yaml_path=['extraS3s', s3_id, 'url'],
                        var_names=[],
                        cast=cast_str,
                    )
                ),
                username=self.get(
                    key=ConfigKey(
                        yaml_path=['extraS3s', s3_id, 'username'],
                        var_names=[],
                        cast=cast_str,
                    )
                ),
                password=self.get(
                    key=ConfigKey(
                        yaml_path=['extraS3s', s3_id, 'password'],
                        var_names=[],
                        cast=cast_str,
                    )
                ),
                bucket=self.get(
                    key=ConfigKey(
                        yaml_path=['extraS3s', s3_id, 'bucket'],
                        var_names=[],
                        cast=cast_str,
                    )
                ),
                region=self.get(
                    key=ConfigKey(
                        yaml_path=['extraS3s', s3_id, 'region'],
                        var_names=[],
                        cast=cast_str,
                    )
                ),
            )

        return result

    @property
    def experimental(self) -> ExperimentalConfig:
        return ExperimentalConfig(
            job_timeout=self.get(self.keys.experimental.job_timeout),
        )

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
            extra_s3s=self.extra_s3s,
            experimental=self.experimental,
        )
