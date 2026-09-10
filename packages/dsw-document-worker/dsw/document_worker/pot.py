from __future__ import annotations

import dataclasses
import io
import logging
import re
import typing
import uuid

import babel
import jinja2.exceptions
import jinja2.ext
from babel.messages.catalog import Catalog
from babel.messages.extract import DEFAULT_KEYWORDS, extract
from babel.messages.pofile import write_po

from dsw.command_queue import CommandJobError

from . import consts
from .context import Context


if typing.TYPE_CHECKING:
    from dsw.database.model import DBDocumentTemplateFile, PersistentCommand


LOG = logging.getLogger(__name__)

COMMENT_TAGS = ('TRANSLATORS:',)
EXTRACT_METHOD = typing.cast('typing.Any', jinja2.ext.babel_extract)
COORDINATE_PATTERN = re.compile(r'^[A-Za-z0-9._-]+$')
NO_WRAP = 0
EXTRACT_OPTIONS = {
    'encoding': consts.DEFAULT_ENCODING,
    'extensions': ','.join(consts.JINJA_EXTENSIONS),
    'silent': 'false',
    'newstyle_gettext': 'true',
    'trimmed': str(consts.JINJA_I18N_TRIMMED).lower(),
}


@dataclasses.dataclass(frozen=True)
class PotFileRequest:
    command_uuid: str
    tenant_uuid: str
    document_template_uuid: str
    organization_id: str
    template_id: str
    version: str
    language: str

    @property
    def coordinates(self) -> str:
        return f'{self.organization_id}:{self.template_id}:{self.version}'

    @property
    def file_name(self) -> str:
        return f'{self.organization_id}_{self.template_id}_{self.version}.pot'

    @staticmethod
    def load(command: PersistentCommand) -> PotFileRequest:
        body = command.body
        template_uuid = body.get('documentTemplateUuid', '')
        try:
            template_uuid = str(uuid.UUID(str(template_uuid)))
        except ValueError as e:
            raise CommandJobError.create(
                job_id=str(template_uuid),
                message='Invalid document template UUID in command body',
                try_again=False,
                exc=e,
            ) from e
        coordinates = {
            'organizationId': str(body.get('organizationId', '')),
            'templateId': str(body.get('templateId', '')),
            'version': str(body.get('version', '')),
        }
        for name, value in coordinates.items():
            if COORDINATE_PATTERN.match(value) is None:
                raise CommandJobError.create(
                    job_id=template_uuid,
                    message=f'Invalid value of "{name}" in command body',
                    try_again=False,
                )
        return PotFileRequest(
            command_uuid=command.uuid,
            tenant_uuid=command.tenant_uuid,
            document_template_uuid=template_uuid,
            organization_id=coordinates['organizationId'],
            template_id=coordinates['templateId'],
            version=coordinates['version'],
            language=str(body.get('language') or consts.DEFAULT_LANGUAGE),
        )


@dataclasses.dataclass
class ExtractionResult:
    catalog: Catalog
    failed_files: list[str]


def extract_messages(content: str) -> list[tuple]:
    return list(extract(
        method=EXTRACT_METHOD,
        fileobj=io.BytesIO(content.encode(consts.DEFAULT_ENCODING)),
        keywords=DEFAULT_KEYWORDS,
        comment_tags=COMMENT_TAGS,
        options=EXTRACT_OPTIONS,
    ))


def make_catalog(*, project: str, version: str, language: str) -> Catalog:
    locale: babel.Locale | None = None
    try:
        locale = babel.Locale.parse(language.replace('-', '_'))
    except (ValueError, babel.UnknownLocaleError):
        LOG.warning('Cannot parse language "%s" - POT file without locale info', language)
    return Catalog(
        locale=locale,
        domain=consts.DEFAULT_LOCALE_DOMAIN,
        project=project,
        version=version,
        charset=consts.DEFAULT_ENCODING,
        fuzzy=False,
    )


def extract_catalog(files: list[DBDocumentTemplateFile], *, project: str,
                    version: str, language: str) -> ExtractionResult:
    catalog = make_catalog(project=project, version=version, language=language)
    failed_files = []
    for file in sorted(files, key=lambda f: f.file_name):
        try:
            messages = extract_messages(file.content)
        except jinja2.exceptions.TemplateSyntaxError as e:
            LOG.warning('Skipping file "%s" that cannot be parsed: %s', file.file_name, str(e))
            failed_files.append(file.file_name)
            continue
        for lineno, message, comments, context in messages:
            catalog.add(
                message,
                None,
                [(file.file_name, lineno)],
                auto_comments=comments,
                context=context,
            )
    return ExtractionResult(catalog=catalog, failed_files=failed_files)


def render_pot_file(result: ExtractionResult) -> bytes:
    lines = [f'# Translations template for {result.catalog.project}.']
    if result.failed_files:
        lines.append(f'# Skipped files that could not be parsed: '
                     f'{", ".join(result.failed_files)}')
    result.catalog.header_comment = '\n'.join(lines) + '\n'
    buffer = io.BytesIO()
    write_po(buffer, result.catalog, width=NO_WRAP, omit_header=False, sort_output=True)
    return buffer.getvalue()


class PotFileJob:

    def __init__(self, command: PersistentCommand):
        self.ctx = Context.get()
        self.rq = PotFileRequest.load(command)
        self.ctx.tenant_uuid = self.rq.tenant_uuid

    def run(self):
        template = self.ctx.app.db.fetch_template(
            template_uuid=self.rq.document_template_uuid,
            tenant_uuid=self.rq.tenant_uuid,
        )
        if template is None:
            LOG.warning('Document template %s not found, skipping POT file generation',
                        self.rq.document_template_uuid)
            return
        if template.coordinates != self.rq.coordinates:
            LOG.warning('Command coordinates %s differ from the ones in DB (%s)',
                        self.rq.coordinates, template.coordinates)
        files = self._fetch_template_files()
        LOG.info('Extracting messages from %d file(s) of template %s',
                 len(files), self.rq.coordinates)
        result = extract_catalog(
            files,
            project=self.rq.coordinates,
            version=self.rq.version,
            language=self.rq.language,
        )
        LOG.info('Extracted %d message(s), %d file(s) skipped',
                 len(result.catalog), len(result.failed_files))
        self._store_pot_file(render_pot_file(result))
        self._mark_pot_file_ready()

    def _fetch_template_files(self) -> list[DBDocumentTemplateFile]:
        db_files = self.ctx.app.db.fetch_template_files(
            template_uuid=self.rq.document_template_uuid,
            tenant_uuid=self.rq.tenant_uuid,
        )
        return [f for f in db_files
                if f.file_name.endswith(consts.JINJA_FILE_EXTENSIONS)]

    def _store_pot_file(self, data: bytes):
        try:
            self.ctx.app.s3.ensure_bucket()
            self.ctx.app.s3.store_document_template_pot(
                tenant_uuid=self.rq.tenant_uuid,
                template_uuid=self.rq.document_template_uuid,
                file_name=self.rq.file_name,
                data=data,
            )
        except Exception as e:
            raise CommandJobError.create(
                job_id=self.rq.document_template_uuid,
                message='Failed to store the POT file in S3',
                exc=e,
            ) from e
        LOG.info('POT file %s stored in S3', self.rq.file_name)

    def _mark_pot_file_ready(self):
        try:
            self.ctx.app.db.update_document_template_pot_file_ready(
                template_uuid=self.rq.document_template_uuid,
                tenant_uuid=self.rq.tenant_uuid,
                ready=True,
            )
        except Exception as e:
            raise CommandJobError.create(
                job_id=self.rq.document_template_uuid,
                message='Failed to mark the POT file as ready',
                exc=e,
            ) from e
