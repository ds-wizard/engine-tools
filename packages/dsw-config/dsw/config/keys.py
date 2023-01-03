import collections

from typing import Any, Optional, Generic, TypeVar, Callable


T = TypeVar('T')


def cast_bool(value: Any) -> bool:
    return bool(value)


def cast_int(value: Any) -> int:
    return int(value)


def cast_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    return int(value)


def cast_float(value: Any) -> float:
    return float(value)


def cast_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def cast_str(value: Any) -> str:
    return str(value)


def cast_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


class ConfigKey(Generic[T]):

    def __init__(self, yaml_path: list[str], cast: Callable[[Any], T],
                 var_names=None, default=None, required=False):
        self.yaml_path = yaml_path
        self.var_names = var_names or []  # type: list[str]
        self.default = default
        self.required = required
        self.cast = cast

    def __str__(self):
        return 'ConfigKey: ' + '.'.join(self.yaml_path)


class ConfigKeysMeta(type):

    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        return collections.OrderedDict()

    def __init__(cls, name, bases, namespace):
        cls._config_keys = []
        for attr in namespace:
            if attr.startswith('_'):
                continue
            value = getattr(cls, attr)
            if isinstance(value, ConfigKey):
                cls._config_keys.append(value)
            if hasattr(value, '_config_keys'):
                keys = getattr(value, '_config_keys')
                if isinstance(keys, list):
                    cls._config_keys.extend(keys)
        super().__init__(name, bases, namespace)

    def __iter__(cls):
        return iter(cls._config_keys)


class ConfigKeysContainer(metaclass=ConfigKeysMeta):
    pass


class _GeneralKeys(ConfigKeysContainer):
    environment = ConfigKey(
        yaml_path=['general', 'environment'],
        var_names=['GENERAL_ENVIRONMENT'],
        default='Production',
        cast=cast_str,
    )
    client_url = ConfigKey(
        yaml_path=['general', 'clientUrl'],
        var_names=['GENERAL_CLIENT_URL'],
        default='http://localhost:8080',
        cast=cast_str,
    )
    secret = ConfigKey(
        yaml_path=['general', 'secret'],
        var_names=['GENERAL_SECRET'],
        default='',
        cast=cast_str,
    )


class _LoggingKeys(ConfigKeysContainer):
    level = ConfigKey(
        yaml_path=['logging', 'level'],
        var_names=['LOGGING_ENVIRONMENT'],
        default='INFO',
        cast=cast_str,
    )
    global_level = ConfigKey(
        yaml_path=['logging', 'globalLevel'],
        var_names=['LOGGING_CLIENT_URL'],
        default='WARNING',
        cast=cast_str,
    )
    format = ConfigKey(
        yaml_path=['logging', 'format'],
        var_names=['LOGGING_FORMAT'],
        default='%(asctime)s | %(levelname)8s | %(name)s: [T:%(traceId)s] %(message)s',
        cast=cast_str,
    )


class _CloudKeys(ConfigKeysContainer):
    enabled = ConfigKey(
        yaml_path=['cloud', 'enabled'],
        var_names=['CLOUD_ENABLED'],
        default=False,
        cast=cast_bool,
    )


class _SentryKeys(ConfigKeysContainer):
    enabled = ConfigKey(
        yaml_path=['sentry', 'enabled'],
        var_names=['SENTRY_ENABLED'],
        default=False,
        cast=cast_bool,
    )
    worker_dsn = ConfigKey(
        yaml_path=['sentry', 'workersDsn'],
        var_names=['SENTRY_WORKER_DSN'],
        default='',
        cast=cast_str,
    )


class _DatabaseKeys(ConfigKeysContainer):
    connection_string = ConfigKey(
        yaml_path=['database', 'connectionString'],
        var_names=['DATABASE_CONNECTION_STRING'],
        default='postgresql://postgres:postgres@postgres:5432/engine-wizard',
        cast=cast_str,
    )
    connection_timeout = ConfigKey(
        yaml_path=['database', 'connectionTimeout'],
        var_names=['DATABASE_CONNECTION_TIMEOUT'],
        default=30000,
        cast=cast_int,
    )
    queue_timeout = ConfigKey(
        yaml_path=['database', 'queueTimeout'],
        var_names=['DATABASE_QUEUE_TIMEOUT'],
        default=180,
        cast=cast_int,
    )


class _S3Keys(ConfigKeysContainer):
    url = ConfigKey(
        yaml_path=['s3', 'url'],
        var_names=['S3_URL'],
        default='http://minio:9000',
        cast=cast_str,
    )
    bucket = ConfigKey(
        yaml_path=['s3', 'bucket'],
        var_names=['S3_BUCKET'],
        default='engine-wizard',
        cast=cast_str,
    )
    region = ConfigKey(
        yaml_path=['s3', 'region'],
        var_names=['S3_REGION'],
        default='eu-central-1',
        cast=cast_str,
    )
    username = ConfigKey(
        yaml_path=['s3', 'username'],
        var_names=['S3_USERNAME'],
        default='minio',
        cast=cast_str,
    )
    password = ConfigKey(
        yaml_path=['s3', 'password'],
        var_names=['S3_PASSWORD'],
        default='minioPassword',
        cast=cast_str,
    )


class _MailKeys(ConfigKeysContainer):
    enabled = ConfigKey(
        yaml_path=['mail', 'enabled'],
        var_names=['MAIL_ENABLED'],
        default=True,
        cast=cast_bool,
    )
    name = ConfigKey(
        yaml_path=['mail', 'name'],
        var_names=['MAIL_NAME'],
        default='',
        cast=cast_str,
    )
    email = ConfigKey(
        yaml_path=['mail', 'email'],
        var_names=['MAIL_EMAIL'],
        default='',
        cast=cast_str,
    )
    host = ConfigKey(
        yaml_path=['mail', 'host'],
        var_names=['MAIL_HOST'],
        default='',
        cast=cast_str,
    )
    port = ConfigKey(
        yaml_path=['mail', 'port'],
        var_names=['MAIL_PORT'],
        cast=cast_str,
    )
    ssl = ConfigKey(
        yaml_path=['mail', 'ssl'],
        var_names=[],
        cast=cast_optional_str,
    )
    security = ConfigKey(
        yaml_path=['mail', 'security'],
        var_names=['MAIL_SECURITY'],
        cast=cast_optional_str,
    )
    auth_enabled = ConfigKey(
        yaml_path=['mail', 'authEnabled'],
        var_names=[],
        default=False,
        cast=cast_bool,
    )
    username = ConfigKey(
        yaml_path=['mail', 'username'],
        var_names=['MAIL_USERNAME'],
        cast=cast_str,
    )
    password = ConfigKey(
        yaml_path=['mail', 'password'],
        var_names=['MAIL_PASSWORD'],
        cast=cast_str,
    )
    rate_limit_window = ConfigKey(
        yaml_path=['mail', 'rateLimit', 'window'],
        var_names=['MAIL_RATE_LIMIT_WINDOW'],
        default=0,
        cast=cast_int,
    )
    rate_limit_count = ConfigKey(
        yaml_path=['mail', 'rateLimit', 'count'],
        var_names=['MAIL_RATE_LIMIT_COUNT'],
        default=0,
        cast=cast_int,
    )
    timeout = ConfigKey(
        yaml_path=['mail', 'timeout'],
        var_names=['MAIL_TIMEOUT'],
        default=10,
        cast=cast_int,
    )


class ConfigKeys(ConfigKeysContainer):
    cloud = _CloudKeys
    database = _DatabaseKeys
    general = _GeneralKeys
    logging = _LoggingKeys
    mail = _MailKeys
    s3 = _S3Keys
    sentry = _SentryKeys


if __name__ == '__main__':
    for key in ConfigKeys:
        print(str(key))
