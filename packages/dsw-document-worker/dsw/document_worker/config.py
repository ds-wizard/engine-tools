import shlex
from typing import List, Optional

from dsw.config import DSWConfigParser
from dsw.config.model import GeneralConfig, SentryConfig, DatabaseConfig,\
    S3Config, LoggingConfig, CloudConfig

from .consts import DocumentNamingStrategy


class DocumentsConfig:

    def __init__(self, naming_strategy: str):
        self.naming_strategy = DocumentNamingStrategy.get(naming_strategy)

    def __str__(self):
        return f'DocumentsConfig\n' \
               f'- naming_strategy = {self.naming_strategy}\n'


class ExperimentalConfig:

    def __init__(self, pdf_only: bool, job_timeout: Optional[float],
                 max_doc_size: Optional[float],
                 pdf_watermark: str, pdf_watermark_top: bool):
        self.pdf_only = pdf_only
        self.job_timeout = job_timeout
        self.max_doc_size = max_doc_size
        self.pdf_watermark = pdf_watermark
        self.pdf_watermark_top = pdf_watermark_top

    def __str__(self):
        return f'ExperimentalConfig\n' \
               f'- pdf_only = {self.pdf_only}\n' \
               f'- job_timeout = {self.job_timeout}\n' \
               f'- max_doc_size = {self.max_doc_size}\n' \
               f'- pdf_watermark = {self.pdf_watermark}\n' \
               f'- pdf_watermark_top = {self.pdf_watermark_top}\n'


class CommandConfig:

    def __init__(self, executable: str, args: str, timeout: float):
        self.executable = executable
        self.args = args
        self.timeout = timeout

    @property
    def command(self) -> List[str]:
        return [self.executable] + shlex.split(self.args)

    def __str__(self):
        return f'CommandConfig\n' \
               f'- executable = {self.executable} ({type(self.executable)})\n' \
               f'- args = {self.args} ({type(self.args)})\n' \
               f'- timeout = {self.timeout} ({type(self.timeout)})\n'


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
        print(data)
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

    DOCS_SECTION = 'documents'
    DOCS_NAMING_SUBSECTION = 'naming'
    EXTERNAL_SECTION = 'externals'
    PANDOC_SUBSECTION = 'pandoc'
    WKHTMLTOPDF_SUBSECTION = 'wkhtmltopdf'
    TEMPLATES_SECTION = 'templates'
    EXPERIMENTAL_SECTION = 'experimental'

    DEFAULTS = {
        **DSWConfigParser.DEFAULTS,
        DOCS_SECTION: {
            DOCS_NAMING_SUBSECTION: {
                'strategy': 'sanitize'
            }
        },
        EXTERNAL_SECTION: {
            PANDOC_SUBSECTION: {
                'executable': 'pandoc',
                'args': '--standalone',
                'timeout': None,
            },
            WKHTMLTOPDF_SUBSECTION: {
                'executable': 'wkhtmltopdf',
                'args': '',
                'timeout': None,
            },
        },
        TEMPLATES_SECTION: [],
        EXPERIMENTAL_SECTION: {
            'pdfOnly': False,
            'jobTimeout': None,
            'maxDocumentSize': None,
            'pdfWatermark': '/app/data/watermark.pdf',
            'pdfWatermarkTop': True,
        },
    }

    @property
    def documents(self) -> DocumentsConfig:
        return DocumentsConfig(
            naming_strategy=self.get_or_default(self.DOCS_SECTION, self.DOCS_NAMING_SUBSECTION, 'strategy')
        )

    def _command_config(self, *path: str) -> CommandConfig:
        return CommandConfig(
            executable=self.get_or_default(*path, 'executable'),
            args=self.get_or_default(*path, 'args'),
            timeout=self.get_or_default(*path, 'timeout'),
        )

    @property
    def pandoc(self) -> CommandConfig:
        return self._command_config(self.EXTERNAL_SECTION, self.PANDOC_SUBSECTION)

    @property
    def wkhtmltopdf(self) -> CommandConfig:
        return self._command_config(self.EXTERNAL_SECTION, self.WKHTMLTOPDF_SUBSECTION)

    @property
    def templates(self) -> TemplatesConfig:
        templates_data = self.get_or_default(self.TEMPLATES_SECTION)
        templates = [TemplateConfig.load(data) for data in templates_data]
        return TemplatesConfig(
            templates=templates,
        )

    @property
    def experimental(self) -> ExperimentalConfig:
        return ExperimentalConfig(
            pdf_only=self.get_or_default(self.EXPERIMENTAL_SECTION, 'pdfOnly'),
            job_timeout=self.get_or_default(self.EXPERIMENTAL_SECTION, 'jobTimeout'),
            max_doc_size=self.get_or_default(self.EXPERIMENTAL_SECTION, 'maxDocumentSize'),
            pdf_watermark=self.get_or_default(self.EXPERIMENTAL_SECTION, 'pdfWatermark'),
            pdf_watermark_top=self.get_or_default(self.EXPERIMENTAL_SECTION, 'pdfWatermarkTop'),
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
