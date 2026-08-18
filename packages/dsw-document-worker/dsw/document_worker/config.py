from __future__ import annotations

import dataclasses
import shlex
import typing

from dsw.config import DSWConfigParser
from dsw.config.keys import (
    ConfigKey,
    ConfigKeys,
    ConfigKeysContainer,
    cast_bool,
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

from . import consts


def cast_str_list(value: typing.Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = value.split(',')
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


class _DocumentsKeys(ConfigKeysContainer):
    naming_strategy = ConfigKey(
        yaml_path=['documents', 'naming', 'strategy'],
        var_names=['DOCUMENTS_NAMING_STRATEGY'],
        default='sanitize',
        cast=cast_str,
    )


class _ExperimentalKeys(ConfigKeysContainer):
    job_timeout = ConfigKey(
        yaml_path=['experimental', 'jobTimeout'],
        var_names=['EXPERIMENTAL_JOB_TIMEOUT'],
        default=None,
        cast=cast_optional_int,
    )
    max_doc_size = ConfigKey(
        yaml_path=['experimental', 'maxDocumentSize'],
        var_names=['EXPERIMENTAL_MAX_DOCUMENT_SIZE'],
        default=None,
        cast=cast_optional_int,
    )


class _SecurityKeys(ConfigKeysContainer):
    allow_external_resources = ConfigKey(
        yaml_path=['security', 'allowExternalResources'],
        var_names=['SECURITY_ALLOW_EXTERNAL_RESOURCES'],
        default=True,
        cast=cast_bool,
    )
    allow_private_network = ConfigKey(
        yaml_path=['security', 'allowPrivateNetwork'],
        var_names=['SECURITY_ALLOW_PRIVATE_NETWORK'],
        default=False,
        cast=cast_bool,
    )
    allowed_hosts = ConfigKey(
        yaml_path=['security', 'allowedHosts'],
        var_names=['SECURITY_ALLOWED_HOSTS'],
        default=None,
        cast=cast_str_list,
    )
    allowed_paths = ConfigKey(
        yaml_path=['security', 'allowedPaths'],
        var_names=['SECURITY_ALLOWED_PATHS'],
        default=None,
        cast=cast_str_list,
    )
    max_redirects = ConfigKey(
        yaml_path=['security', 'maxRedirects'],
        var_names=['SECURITY_MAX_REDIRECTS'],
        default=3,
        cast=cast_int,
    )


class _DocumentContextKeys(ConfigKeysContainer):
    service_name = ConfigKey(
        yaml_path=['documentContext', 'serviceName'],
        var_names=['DOCUMENT_CONTEXT_SERVICE_NAME'],
        default='Data Stewardship Wizard',
        cast=cast_str,
    )
    service_name_short = ConfigKey(
        yaml_path=['documentContext', 'serviceNameShort'],
        var_names=['DOCUMENT_CONTEXT_SERVICE_NAME_SHORT'],
        default='DSW',
        cast=cast_str,
    )
    service_url = ConfigKey(
        yaml_path=['documentContext', 'serviceUrl'],
        var_names=['DOCUMENT_CONTEXT_SERVICE_URL'],
        default='https://ds-wizard.org',
        cast=cast_str,
    )
    service_domain_name = ConfigKey(
        yaml_path=['documentContext', 'serviceDomainName'],
        var_names=['DOCUMENT_CONTEXT_SERVICE_DOMAIN_NAME'],
        default='ds-wizard.org',
        cast=cast_str,
    )
    default_primary_color = ConfigKey(
        yaml_path=['documentContext', 'defaultPrimaryColor'],
        var_names=['DOCUMENT_CONTEXT_DEFAULT_PRIMARY_COLOR'],
        default='#0033aa',
        cast=cast_str,
    )
    default_illustrations_color = ConfigKey(
        yaml_path=['documentContext', 'defaultIllustrationsColor'],
        var_names=['DOCUMENT_CONTEXT_DEFAULT_ILLUSTRATIONS_COLOR'],
        default='#0033aa',
        cast=cast_str,
    )
    default_logo_url = ConfigKey(
        yaml_path=['documentContext', 'defaultLogoUrl'],
        var_names=['DOCUMENT_CONTEXT_DEFAULT_LOGO_URL'],
        default='{{clientUrl}}/assets/logo.svg',
        cast=cast_str,
    )
    default_app_title = ConfigKey(
        yaml_path=['documentContext', 'defaultAppTitle'],
        var_names=['DOCUMENT_CONTEXT_DEFAULT_APP_TITLE'],
        default='DS Wizard',
        cast=cast_str,
    )
    default_app_title_short = ConfigKey(
        yaml_path=['documentContext', 'defaultAppTitleShort'],
        var_names=['DOCUMENT_CONTEXT_DEFAULT_APP_TITLE_SHORT'],
        default='DS Wizard',
        cast=cast_str,
    )


class _CommandPandocKeys(ConfigKeysContainer):
    executable = ConfigKey(
        yaml_path=['externals', 'pandoc', 'executable'],
        var_names=['PANDOC_EXECUTABLE'],
        default='pandoc',
        cast=cast_str,
    )
    args = ConfigKey(
        yaml_path=['externals', 'pandoc', 'args'],
        var_names=['PANDOC_ARGS'],
        default='--standalone',
        cast=cast_str,
    )
    timeout = ConfigKey(
        yaml_path=['externals', 'pandoc', 'timeout'],
        var_names=['PANDOC_TIMEOUT'],
        default=None,
        cast=cast_optional_int,
    )


class DocWorkerConfigKeys(ConfigKeys):
    documents = _DocumentsKeys
    experimental = _ExperimentalKeys
    cmd_pandoc = _CommandPandocKeys
    context = _DocumentContextKeys
    security = _SecurityKeys


@dataclasses.dataclass
class DocumentsConfig(ConfigModel):
    naming_strategy: str

    def __init__(self, naming_strategy: str):
        self.naming_strategy = consts.DocumentNamingStrategy.get(naming_strategy)


@dataclasses.dataclass
class ExperimentalConfig(ConfigModel):
    job_timeout: int | None
    max_doc_size: int | None


@dataclasses.dataclass
class SecurityConfig(ConfigModel):
    allow_external_resources: bool
    allow_private_network: bool
    allowed_hosts: list[str]
    allowed_paths: list[str]
    max_redirects: int


@dataclasses.dataclass
class DocumentContextConfig(ConfigModel):
    service_name: str
    service_name_short: str
    service_url: str
    service_domain_name: str
    default_primary_color: str
    default_illustrations_color: str
    default_logo_url: str
    default_app_title: str
    default_app_title_short: str


@dataclasses.dataclass
class CommandConfig:
    executable: str
    args: str
    timeout: float

    @property
    def command(self) -> list[str]:
        return [self.executable] + shlex.split(self.args)


@dataclasses.dataclass
class TemplateRequestsConfig:
    enabled: bool
    limit: int
    timeout: int

    @staticmethod
    def load(data: dict):
        return TemplateRequestsConfig(
            enabled=data.get('enabled', False),
            limit=data.get('limit', 100),
            timeout=data.get('timeout', 1),
        )


@dataclasses.dataclass
class TemplateConfig:
    ids: list[str]
    requests: TemplateRequestsConfig
    secrets: dict[str, str]
    send_sentry: bool

    @staticmethod
    def load(data: dict):
        return TemplateConfig(
            ids=data.get('ids', []),
            requests=TemplateRequestsConfig.load(
                data.get('requests', {}),
            ),
            secrets=data.get('secrets', {}),
            send_sentry=bool(data.get('sentry', False)),
        )


@dataclasses.dataclass
class TemplatesConfig:
    templates: list[TemplateConfig]

    def get_config(self, template_coordinates: str) -> TemplateConfig | None:
        for template in self.templates:
            if any(template_coordinates.startswith(prefix) for prefix in template.ids):
                return template
        return None


@dataclasses.dataclass
class DocumentWorkerConfig:
    db: DatabaseConfig
    s3: S3Config
    log: LoggingConfig
    doc: DocumentsConfig
    pandoc: CommandConfig
    templates: TemplatesConfig
    experimental: ExperimentalConfig
    cloud: CloudConfig
    sentry: SentryConfig
    general: GeneralConfig
    context: DocumentContextConfig
    security: SecurityConfig

    def __str__(self):
        return f'DocumentWorkerConfig\n' \
               f'====================\n' \
               f'{self.db}' \
               f'{self.s3}' \
               f'{self.log}' \
               f'{self.doc}' \
               f'{self.experimental}' \
               f'{self.cloud}' \
               f'{self.sentry}' \
               f'{self.general}' \
               f'{self.context}' \
               f'{self.security}' \
               f'Pandoc: {self.pandoc}' \
               f'====================\n'


class DocumentWorkerConfigParser(DSWConfigParser):
    TEMPLATES_SECTION = 'templates'

    def __init__(self):
        super().__init__(keys=DocWorkerConfigKeys)
        self.keys: type[DocWorkerConfigKeys] = DocWorkerConfigKeys

    @property
    def documents(self) -> DocumentsConfig:
        return DocumentsConfig(
            naming_strategy=self.get(self.keys.documents.naming_strategy),
        )

    @property
    def pandoc(self) -> CommandConfig:
        return CommandConfig(
            executable=self.get(self.keys.cmd_pandoc.executable),
            args=self.get(self.keys.cmd_pandoc.args),
            timeout=self.get(self.keys.cmd_pandoc.timeout),
        )

    @property
    def templates(self) -> TemplatesConfig:
        return TemplatesConfig(
            templates=[
                TemplateConfig.load(data)
                for data in self.cfg.get(self.TEMPLATES_SECTION, [])
            ],
        )

    @property
    def experimental(self) -> ExperimentalConfig:
        return ExperimentalConfig(
            job_timeout=self.get(self.keys.experimental.job_timeout),
            max_doc_size=self.get(self.keys.experimental.max_doc_size),
        )

    @property
    def context(self) -> DocumentContextConfig:
        return DocumentContextConfig(
            service_name=self.get(self.keys.context.service_name),
            service_name_short=self.get(self.keys.context.service_name_short),
            service_url=self.get(self.keys.context.service_url),
            service_domain_name=self.get(self.keys.context.service_domain_name),
            default_primary_color=self.get(self.keys.context.default_primary_color),
            default_illustrations_color=self.get(self.keys.context.default_illustrations_color),
            default_logo_url=self.get(self.keys.context.default_logo_url),
            default_app_title=self.get(self.keys.context.default_app_title),
            default_app_title_short=self.get(self.keys.context.default_app_title_short),
        )

    @property
    def security(self) -> SecurityConfig:
        return SecurityConfig(
            allow_external_resources=self.get(self.keys.security.allow_external_resources),
            allow_private_network=self.get(self.keys.security.allow_private_network),
            allowed_hosts=self.get(self.keys.security.allowed_hosts),
            allowed_paths=self.get(self.keys.security.allowed_paths),
            max_redirects=self.get(self.keys.security.max_redirects),
        )

    @property
    def config(self) -> DocumentWorkerConfig:
        return DocumentWorkerConfig(
            db=self.db,
            s3=self.s3,
            log=self.logging,
            doc=self.documents,
            pandoc=self.pandoc,
            templates=self.templates,
            experimental=self.experimental,
            cloud=self.cloud,
            sentry=self.sentry,
            general=self.general,
            context=self.context,
            security=self.security,
        )
