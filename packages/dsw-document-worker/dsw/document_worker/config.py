import dataclasses
import shlex

from dsw.config import DSWConfigParser
from dsw.config.keys import ConfigKey, ConfigKeys, ConfigKeysContainer, \
    cast_str, cast_optional_int
from dsw.config.model import GeneralConfig, SentryConfig, DatabaseConfig, \
    S3Config, LoggingConfig, CloudConfig, ConfigModel

from .consts import DocumentNamingStrategy


# pylint: disable-next=too-few-public-methods
class _DocumentsKeys(ConfigKeysContainer):
    naming_strategy = ConfigKey(
        yaml_path=['documents', 'naming', 'strategy'],
        var_names=['DOCUMENTS_NAMING_STRATEGY'],
        default='sanitize',
        cast=cast_str,
    )


# pylint: disable-next=too-few-public-methods
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


# pylint: disable-next=too-few-public-methods
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


# pylint: disable-next=too-few-public-methods
class DocWorkerConfigKeys(ConfigKeys):
    documents = _DocumentsKeys
    experimental = _ExperimentalKeys
    cmd_pandoc = _CommandPandocKeys


@dataclasses.dataclass
class DocumentsConfig(ConfigModel):
    naming_strategy: str

    def __init__(self, naming_strategy: str):
        self.naming_strategy = DocumentNamingStrategy.get(naming_strategy)


@dataclasses.dataclass
class ExperimentalConfig(ConfigModel):
    job_timeout: int | None
    max_doc_size: int | None


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

    def get_config(self, template_id: str) -> TemplateConfig | None:
        for template in self.templates:
            if any((template_id.startswith(prefix)
                    for prefix in template.ids)):
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
               f'Pandoc: {self.pandoc}' \
               f'====================\n'


class DocumentWorkerConfigParser(DSWConfigParser):
    TEMPLATES_SECTION = 'templates'

    def __init__(self):
        super().__init__(keys=DocWorkerConfigKeys)
        self.keys = DocWorkerConfigKeys  # type: type[DocWorkerConfigKeys]

    @property
    def documents(self) -> DocumentsConfig:
        return DocumentsConfig(
            naming_strategy=self.get(self.keys.documents.naming_strategy)
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
        )
