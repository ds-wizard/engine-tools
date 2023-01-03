import shlex
from typing import List, Optional, Type

from dsw.config import DSWConfigParser
from dsw.config.keys import ConfigKey, ConfigKeys, ConfigKeysContainer,\
    cast_str, cast_optional_int, cast_bool, cast_optional_str
from dsw.config.model import GeneralConfig, SentryConfig, DatabaseConfig,\
    S3Config, LoggingConfig, CloudConfig, ConfigModel

from .consts import DocumentNamingStrategy


class _DocumentsKeys(ConfigKeysContainer):
    naming_strategy = ConfigKey(
        yaml_path=['documents', 'naming', 'strategy'],
        var_names=['DOCUMENTS_NAMING_STRATEGY'],
        default='sanitize',
        cast=cast_str,
    )


class _ExperimentalKeys(ConfigKeysContainer):
    pdf_only = ConfigKey(
        yaml_path=['experimental', 'pdfOnly'],
        var_names=['EXPERIMENTAL_PDF_ONLY'],
        default=False,
        cast=cast_bool,
    )
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
    pdf_watermark = ConfigKey(
        yaml_path=['experimental', 'pdfWatermark'],
        var_names=['EXPERIMENTAL_PDF_WATERMARK'],
        default='/app/data/watermark.pdf',
        cast=cast_optional_str,
    )
    pdf_watermark_top = ConfigKey(
        yaml_path=['experimental', 'pdfWatermarkTop'],
        var_names=['EXPERIMENTAL_PDF_WATERMARK_TOP'],
        default=True,
        cast=cast_bool,
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


class _CommandWkhtmltopdfKeys(ConfigKeysContainer):
    executable = ConfigKey(
        yaml_path=['externals', 'wkhtmltopdf', 'executable'],
        var_names=['WKHTMLTOPDF_EXECUTABLE'],
        default='wkhtmltopdf',
        cast=cast_str,
    )
    args = ConfigKey(
        yaml_path=['externals', 'wkhtmltopdf', 'args'],
        var_names=['WKHTMLTOPDF_ARGS'],
        default='',
        cast=cast_str,
    )
    timeout = ConfigKey(
        yaml_path=['externals', 'wkhtmltopdf', 'timeout'],
        var_names=['WKHTMLTOPDF_TIMEOUT'],
        default=None,
        cast=cast_optional_int,
    )


class DocWorkerConfigKeys(ConfigKeys):
    documents = _DocumentsKeys
    experimental = _ExperimentalKeys
    cmd_pandoc = _CommandPandocKeys
    cmd_wkhtmltopdf = _CommandWkhtmltopdfKeys


class DocumentsConfig(ConfigModel):

    def __init__(self, naming_strategy: str):
        self.naming_strategy = DocumentNamingStrategy.get(naming_strategy)


class ExperimentalConfig(ConfigModel):

    def __init__(self, pdf_only: bool, job_timeout: Optional[int],
                 max_doc_size: Optional[float],
                 pdf_watermark: str, pdf_watermark_top: bool):
        self.pdf_only = pdf_only
        self.job_timeout = job_timeout
        self.max_doc_size = max_doc_size
        self.pdf_watermark = pdf_watermark
        self.pdf_watermark_top = pdf_watermark_top


class CommandConfig:

    def __init__(self, executable: str, args: str, timeout: float):
        self.executable = executable
        self.args = args
        self.timeout = timeout

    @property
    def command(self) -> List[str]:
        return [self.executable] + shlex.split(self.args)


class TemplateRequestsConfig:

    def __init__(self, enabled: bool, limit: int, timeout: int):
        self.enabled = enabled
        self.limit = limit
        self.timeout = timeout

    @staticmethod
    def load(data: dict):
        return TemplateRequestsConfig(
            enabled=data.get('enabled', False),
            limit=data.get('limit', 100),
            timeout=data.get('timeout', 1),
        )


class TemplateConfig:

    def __init__(self, ids: List[str], requests: TemplateRequestsConfig,
                 secrets: dict[str, str]):
        self.ids = ids
        self.requests = requests
        self.secrets = secrets

    @staticmethod
    def load(data: dict):
        return TemplateConfig(
            ids=data.get('ids', []),
            requests=TemplateRequestsConfig.load(
                data.get('requests', {}),
            ),
            secrets=data.get('secrets', {}),
        )


class TemplatesConfig:

    def __init__(self, templates: List[TemplateConfig]):
        self.templates = templates

    def get_config(self, template_id: str) -> Optional[TemplateConfig]:
        for template in self.templates:
            if any((template_id.startswith(prefix)
                    for prefix in template.ids)):
                return template
        return None


class DocumentWorkerConfig:

    def __init__(self, db: DatabaseConfig, s3: S3Config, log: LoggingConfig,
                 doc: DocumentsConfig, pandoc: CommandConfig, wkhtmltopdf: CommandConfig,
                 templates: TemplatesConfig, experimental: ExperimentalConfig,
                 cloud: CloudConfig, sentry: SentryConfig, general: GeneralConfig):
        self.db = db
        self.s3 = s3
        self.log = log
        self.doc = doc
        self.pandoc = pandoc
        self.wkhtmltopdf = wkhtmltopdf
        self.templates = templates
        self.experimental = experimental
        self.cloud = cloud
        self.sentry = sentry
        self.general = general

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
               f'WkHtmlToPdf: {self.wkhtmltopdf}' \
               f'====================\n'


class DocumentWorkerConfigParser(DSWConfigParser):

    TEMPLATES_SECTION = 'templates'

    def __init__(self):
        super().__init__(keys=DocWorkerConfigKeys)
        self.keys = DocWorkerConfigKeys  # type: Type[DocWorkerConfigKeys]

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
    def wkhtmltopdf(self) -> CommandConfig:
        return CommandConfig(
            executable=self.get(self.keys.cmd_wkhtmltopdf.executable),
            args=self.get(self.keys.cmd_wkhtmltopdf.args),
            timeout=self.get(self.keys.cmd_wkhtmltopdf.timeout),
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
            pdf_only=self.get(self.keys.experimental.pdf_only),
            job_timeout=self.get(self.keys.experimental.job_timeout),
            max_doc_size=self.get(self.keys.experimental.max_doc_size),
            pdf_watermark=self.get(self.keys.experimental.pdf_watermark),
            pdf_watermark_top=self.get(self.keys.experimental.pdf_watermark_top),
        )

    @property
    def config(self) -> DocumentWorkerConfig:
        return DocumentWorkerConfig(
            db=self.db,
            s3=self.s3,
            log=self.logging,
            doc=self.documents,
            pandoc=self.pandoc,
            wkhtmltopdf=self.wkhtmltopdf,
            templates=self.templates,
            experimental=self.experimental,
            cloud=self.cloud,
            sentry=self.sentry,
            general=self.general,
        )
