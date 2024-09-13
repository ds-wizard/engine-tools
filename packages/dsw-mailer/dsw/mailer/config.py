import enum
import pathlib

from dsw.config import DSWConfigParser
from dsw.config.keys import ConfigKey, ConfigKeys, ConfigKeysContainer, \
    cast_str, cast_bool, cast_optional_str, cast_optional_bool, cast_int, \
    cast_optional_int
from dsw.config.model import GeneralConfig, SentryConfig, \
    DatabaseConfig, LoggingConfig, ConfigModel, AWSConfig
from dsw.database.model import DBInstanceConfigMail


class _ExperimentalKeys(ConfigKeysContainer):
    job_timeout = ConfigKey(
        yaml_path=['experimental', 'jobTimeout'],
        var_names=['EXPERIMENTAL_JOB_TIMEOUT'],
        default=None,
        cast=cast_optional_int,
    )


class ExperimentalConfig(ConfigModel):

    def __init__(self, job_timeout: int | None):
        self.job_timeout = job_timeout


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
    provider = ConfigKey(
        yaml_path=['mail', 'provider'],
        var_names=['MAIL_PROVIDER'],
        default='smtp',
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
    dkim_selector = ConfigKey(
        yaml_path=['mail', 'dkim', 'selector'],
        var_names=['MAIL_DKIM_SELECTOR'],
        default=None,
        cast=cast_optional_str,
    )
    dkim_privkey_file = ConfigKey(
        yaml_path=['mail', 'dkim', 'privkey_file'],
        var_names=['MAIL_DKIM_PRIVKEY_FILE'],
        default=None,
        cast=cast_optional_str,
    )


class _MailLegacySMTPKeys(ConfigKeysContainer):
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
        cast=cast_optional_bool,
    )
    username = ConfigKey(
        yaml_path=['mail', 'username'],
        var_names=['MAIL_USERNAME'],
        cast=cast_optional_str,
    )
    password = ConfigKey(
        yaml_path=['mail', 'password'],
        var_names=['MAIL_PASSWORD'],
        cast=cast_optional_str,
    )
    timeout = ConfigKey(
        yaml_path=['mail', 'timeout'],
        var_names=['MAIL_TIMEOUT'],
        default=5,
        cast=cast_int,
    )


class _MailSMTPKeys(ConfigKeysContainer):
    host = ConfigKey(
        yaml_path=['mail', 'smtp', 'host'],
        var_names=['MAIL_SMTP_HOST'],
        default='',
        cast=cast_optional_str,
    )
    port = ConfigKey(
        yaml_path=['mail', 'smtp', 'port'],
        var_names=['MAIL_SMTP_PORT'],
        cast=cast_optional_int,
    )
    security = ConfigKey(
        yaml_path=['mail', 'smtp', 'security'],
        var_names=['MAIL_SMTP_SECURITY'],
        cast=cast_optional_str,
    )
    username = ConfigKey(
        yaml_path=['mail', 'smtp', 'username'],
        var_names=['MAIL_SMTP_USERNAME'],
        cast=cast_optional_str,
    )
    password = ConfigKey(
        yaml_path=['mail', 'smtp', 'password'],
        var_names=['MAIL_SMTP_PASSWORD'],
        cast=cast_optional_str,
    )
    timeout = ConfigKey(
        yaml_path=['mail', 'smtp', 'timeout'],
        var_names=['MAIL_TIMEOUT'],
        default=5,
        cast=cast_int,
    )


class _MailAmazonSESKeys(ConfigKeysContainer):
    access_key_id = ConfigKey(
        yaml_path=['mail', 'amazonSes', 'accessKeyId'],
        var_names=['MAIL_SES_ACCESS_KEY_ID'],
        cast=cast_optional_str,
    )
    secret_access_key = ConfigKey(
        yaml_path=['mail', 'amazonSes', 'secretAccessKey'],
        var_names=['MAIL_SES_SECRET_ACCESS_KEY'],
        cast=cast_optional_str,
    )
    region = ConfigKey(
        yaml_path=['mail', 'amazonSes', 'region'],
        var_names=['MAIL_SES_REGION'],
        cast=cast_optional_str,
    )


class MailerConfigKeys(ConfigKeys):
    mail = _MailKeys
    mail_legacy_smtp = _MailLegacySMTPKeys
    mail_smtp = _MailSMTPKeys
    mail_amazon_ses = _MailAmazonSESKeys
    experimental = _ExperimentalKeys


class SMTPSecurityMode(enum.Enum):
    PLAIN = enum.auto()
    SSL = enum.auto()
    TLS = enum.auto()

    @classmethod
    def has(cls, name):
        return name in cls.__members__


class MailProvider(enum.Enum):
    NONE = enum.auto()
    SMTP = enum.auto()
    AMAZON_SES = enum.auto()

    @classmethod
    def has(cls, name):
        return name in cls.__members__


class MailSMTPConfig:

    def __init__(self, host: str | None = None, port: int | None = None,
                 security: str | None = None, ssl: bool | None = None,
                 username: str | None = None, password: str | None = None,
                 auth_enabled: bool | None = None, timeout: int = 10):
        self.host = host
        self.security = SMTPSecurityMode.PLAIN  # type: SMTPSecurityMode
        if security is not None and SMTPSecurityMode.has(security.upper()):
            self.security = SMTPSecurityMode[security.upper()]
        elif ssl is not None:
            self.security = SMTPSecurityMode.SSL if ssl else SMTPSecurityMode.PLAIN
        self.port = port or self._default_port()
        self.auth = auth_enabled
        if self.auth is None:
            self.auth = username is not None and password is not None
        self.username = username
        self.password = password
        self.timeout = timeout

    @property
    def login_user(self) -> str:
        return self.username or ''

    @property
    def login_password(self) -> str:
        return self.password or ''

    @property
    def is_plain(self):
        return self.security == SMTPSecurityMode.PLAIN

    @property
    def is_ssl(self):
        return self.security == SMTPSecurityMode.SSL

    @property
    def is_tls(self):
        return self.security == SMTPSecurityMode.TLS

    def _default_port(self) -> int:
        if self.is_plain:
            return 25
        if self.is_ssl:
            return 465
        return 587

    def has_credentials(self) -> bool:
        return self.username is not None and self.password is not None


class MailAmazonSESConfig:

    def __init__(self, access_key_id: str | None = None,
                 secret_access_key: str | None = None,
                 region: str | None = None):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region

    def has_credentials(self) -> bool:
        return self.access_key_id is not None and self.secret_access_key is not None


class MailConfig(ConfigModel):

    def __init__(self, enabled: bool, name: str, email: str,
                 provider: str, smtp: MailSMTPConfig, amazon_ses: MailAmazonSESConfig,
                 rate_limit_window: int, rate_limit_count: int,
                 dkim_selector: str | None = None, dkim_privkey_file: str | None = None):
        self.enabled = enabled
        self.name = name
        self.email = email

        if provider.lower() == 'smtp':
            self.provider = MailProvider.SMTP
        elif provider.lower() in ['ses', 'amazon_ses', 'amazonses']:
            self.provider = MailProvider.AMAZON_SES
        else:
            raise ValueError(f'Unknown mail provider: {provider}')
        self.smtp = smtp
        self.amazon_ses = amazon_ses

        self.rate_limit_window = rate_limit_window
        self.rate_limit_count = rate_limit_count
        self.dkim_selector = dkim_selector
        self.dkim_privkey_file = dkim_privkey_file
        self.dkim_privkey = b''

    def load_dkim_privkey(self):
        if self.dkim_privkey_file is not None:
            self.dkim_privkey = pathlib.Path(self.dkim_privkey_file).read_bytes()
            self.dkim_privkey = self.dkim_privkey.replace(b'\r\n', b'\n')

    def update_aws(self, aws: AWSConfig):
        if self.provider == MailProvider.AMAZON_SES:
            if not self.amazon_ses.has_credentials():
                self.amazon_ses.access_key_id = aws.access_key_id
                self.amazon_ses.secret_access_key = aws.secret_access_key
            if self.amazon_ses.region is None:
                self.amazon_ses.region = aws.region

    @property
    def use_dkim(self):
        return self.dkim_selector is not None and len(self.dkim_privkey) > 0

    def __str__(self):
        return f'MailConfig\n' \
               f'- enabled = {self.enabled}\n' \
               f'- name = {self.name}\n' \
               f'- email = {self.email}\n' \
               f'- provider = {self.provider}\n' \
               f'- rate_limit_window = {self.rate_limit_window}\n' \
               f'- rate_limit_count = {self.rate_limit_count}\n' \
               f'- dkim_selector = {self.dkim_selector}\n' \
               f'- dkim_privkey_file = {self.dkim_privkey_file}\n'


class MailerConfig:

    def __init__(self, db: DatabaseConfig, log: LoggingConfig,
                 mail: MailConfig, sentry: SentryConfig,
                 general: GeneralConfig, aws: AWSConfig,
                 experimental: ExperimentalConfig):
        self.db = db
        self.log = log
        self.mail = mail
        self.sentry = sentry
        self.general = general
        self.aws = aws
        self.experimental = experimental

        # Use AWS credentials for Amazon SES if not provided
        self.mail.update_aws(aws)

    def __str__(self):
        return f'MailerConfig\n' \
               f'====================\n' \
               f'{self.db}' \
               f'{self.log}' \
               f'{self.mail}' \
               f'{self.sentry}' \
               f'{self.general}' \
               f'{self.experimental}' \
               f'====================\n'


class MailerConfigParser(DSWConfigParser):

    def __init__(self):
        super().__init__(keys=MailerConfigKeys)
        self.keys = MailerConfigKeys  # type: type[MailerConfigKeys]

    @property
    def mail(self):
        smtp = MailSMTPConfig(
            host=self.get(self.keys.mail_smtp.host),
            port=self.get(self.keys.mail_smtp.port),
            security=self.get(self.keys.mail_smtp.security),
            username=self.get(self.keys.mail_smtp.username),
            password=self.get(self.keys.mail_smtp.password),
            timeout=int(self.get(self.keys.mail_smtp.timeout)),
        )
        if smtp.host == '':
            smtp = MailSMTPConfig(
                host=self.get(self.keys.mail_legacy_smtp.host),
                port=self.get(self.keys.mail_legacy_smtp.port),
                security=self.get(self.keys.mail_legacy_smtp.security),
                auth_enabled=self.get(self.keys.mail_legacy_smtp.auth_enabled),
                username=self.get(self.keys.mail_legacy_smtp.username),
                password=self.get(self.keys.mail_legacy_smtp.password),
                ssl=self.get(self.keys.mail_legacy_smtp.ssl),
                timeout=int(self.get(self.keys.mail_legacy_smtp.timeout)),
            )

        amazon_ses = MailAmazonSESConfig(
            access_key_id=self.get(self.keys.mail_amazon_ses.access_key_id),
            secret_access_key=self.get(self.keys.mail_amazon_ses.secret_access_key),
            region=self.get(self.keys.mail_amazon_ses.region),
        )

        return MailConfig(
            enabled=self.get(self.keys.mail.enabled),
            name=self.get(self.keys.mail.name),
            email=self.get(self.keys.mail.email),
            provider=self.get(self.keys.mail.provider),
            smtp=smtp,
            amazon_ses=amazon_ses,
            rate_limit_window=int(self.get(self.keys.mail.rate_limit_window)),
            rate_limit_count=int(self.get(self.keys.mail.rate_limit_count)),
            dkim_selector=self.get(self.keys.mail.dkim_selector),
            dkim_privkey_file=self.get(self.keys.mail.dkim_privkey_file),
        )

    @property
    def experimental(self) -> ExperimentalConfig:
        return ExperimentalConfig(
            job_timeout=self.get(self.keys.experimental.job_timeout),
        )

    @property
    def config(self) -> MailerConfig:
        cfg = MailerConfig(
            db=self.db,
            log=self.logging,
            mail=self.mail,
            sentry=self.sentry,
            general=self.general,
            aws=self.aws,
            experimental=self.experimental,
        )
        cfg.mail.load_dkim_privkey()
        return cfg


def merge_mail_configs(cfg: MailerConfig, db_cfg: DBInstanceConfigMail | None) -> MailConfig:
    if db_cfg is None:
        return cfg.mail

    smtp = MailSMTPConfig()
    amazon_ses = MailAmazonSESConfig()
    if db_cfg.provider.lower() == 'smtp':
        if db_cfg.smtp_host is None:
            smtp.host = cfg.mail.smtp.host
            smtp.port = cfg.mail.smtp.port
            smtp.security = cfg.mail.smtp.security
            smtp.username = cfg.mail.smtp.username
            smtp.password = cfg.mail.smtp.password
            smtp.timeout = cfg.mail.smtp.timeout
        else:
            smtp.host = db_cfg.smtp_host
            smtp.port = db_cfg.smtp_port
            smtp.security = db_cfg.smtp_security
            smtp.username = db_cfg.smtp_username
            smtp.password = db_cfg.smtp_password
            smtp.timeout = db_cfg.timeout
    elif db_cfg.provider.lower() == 'amazonses':
        if db_cfg.aws_access_key_id is None and db_cfg.aws_secret_access_key is None:
            amazon_ses.access_key_id = cfg.mail.amazon_ses.access_key_id
            amazon_ses.secret_access_key = cfg.mail.amazon_ses.secret_access_key
            amazon_ses.region = cfg.mail.amazon_ses.region
        else:
            amazon_ses.access_key_id = db_cfg.aws_access_key_id
            amazon_ses.secret_access_key = db_cfg.aws_secret_access_key
            amazon_ses.region = db_cfg.aws_region

    result = MailConfig(
        enabled=cfg.mail.enabled,
        name=db_cfg.sender_name,
        email=db_cfg.sender_email,
        provider=db_cfg.provider,
        smtp=smtp,
        amazon_ses=amazon_ses,
        rate_limit_window=db_cfg.rate_limit_window,
        rate_limit_count=db_cfg.rate_limit_count,
        dkim_privkey_file=None,
        dkim_selector=None,
    )
    result.update_aws(cfg.aws)
    return result
