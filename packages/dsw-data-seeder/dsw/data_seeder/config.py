import dataclasses

from dsw.config import DSWConfigParser
from dsw.config.keys import (
    ConfigKey,
    ConfigKeys,
    ConfigKeysContainer,
    cast_dict,
    cast_int,
    cast_optional_int,
    cast_str,
)
from dsw.config.model import (
    CloudConfig,
    ConfigModel,
    DatabaseConfig,
    GeneralConfig,
    LoggingConfig,
    S3Config,
    SentryConfig,
)


class _SeedKeys(ConfigKeysContainer):
    job_timeout = ConfigKey(
        yaml_path=['seed', 'jobTimeout'],
        var_names=['SEED_JOB_TIMEOUT'],
        default=None,
        cast=cast_optional_int,
    )
    variables = ConfigKey(
        yaml_path=['seed', 'variables'],
        var_names=[],
        default=None,
        cast=cast_dict,
    )


class DataSeederConfigKeys(ConfigKeys):
    seed = _SeedKeys


@dataclasses.dataclass
class SeedConfig(ConfigModel):
    job_timeout: int | None
    variables: dict


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
    seed: SeedConfig

    def __str__(self):
        return f'SeederConfig\n' \
               f'====================\n' \
               f'{self.general}' \
               f'{self.db}' \
               f'{self.s3}' \
               f'{self.log}' \
               f'{self.sentry}' \
               f'{self.cloud}' \
               f'{self.seed}' \
               f'====================\n'


class SeederConfigParser(DSWConfigParser):

    def __init__(self):
        super().__init__(keys=DataSeederConfigKeys)
        self.keys: type[DataSeederConfigKeys] = DataSeederConfigKeys

    @property
    def extra_dbs(self) -> dict[str, DatabaseConfig]:
        result = {}
        for db_id in self.cfg.get('extraDatabases', {}):
            result[db_id] = DatabaseConfig(
                connection_string=self.get(
                    key=ConfigKey(
                        yaml_path=['extraDatabases', db_id, 'connectionString'],
                        var_names=[],
                        default=f'postgresql://postgres:postgres@postgres:5432/{db_id}',
                        cast=cast_str,
                    ),
                ),
                connection_timeout=self.get(
                    key=ConfigKey(
                        yaml_path=['extraDatabases', db_id, 'connectionTimeout'],
                        var_names=[],
                        default=30000,
                        cast=cast_int,
                    ),
                ),
                queue_timeout=0,
            )

        return result

    @property
    def extra_s3s(self) -> dict[str, S3Config]:
        result = {}
        for s3_id in self.cfg.get('extraS3s', {}):
            result[s3_id] = S3Config(
                url=self.get(
                    key=ConfigKey(
                        yaml_path=['extraS3s', s3_id, 'url'],
                        var_names=[],
                        cast=cast_str,
                    ),
                ),
                username=self.get(
                    key=ConfigKey(
                        yaml_path=['extraS3s', s3_id, 'username'],
                        var_names=[],
                        cast=cast_str,
                    ),
                ),
                password=self.get(
                    key=ConfigKey(
                        yaml_path=['extraS3s', s3_id, 'password'],
                        var_names=[],
                        cast=cast_str,
                    ),
                ),
                bucket=self.get(
                    key=ConfigKey(
                        yaml_path=['extraS3s', s3_id, 'bucket'],
                        var_names=[],
                        cast=cast_str,
                    ),
                ),
                region=self.get(
                    key=ConfigKey(
                        yaml_path=['extraS3s', s3_id, 'region'],
                        var_names=[],
                        cast=cast_str,
                    ),
                ),
            )

        return result

    @property
    def seed(self) -> SeedConfig:
        return SeedConfig(
            job_timeout=self.get(self.keys.seed.job_timeout),
            variables=self.get(self.keys.seed.variables),
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
            seed=self.seed,
        )
