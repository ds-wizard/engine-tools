"""Extraction of translatable messages from Jinja templates into a POT file."""
from __future__ import annotations

import dataclasses
import io
import logging
import typing

import babel
import jinja2.exceptions
import jinja2.ext
from babel.messages.catalog import Catalog
from babel.messages.extract import DEFAULT_KEYWORDS, extract
from babel.messages.pofile import write_po

from . import consts


if typing.TYPE_CHECKING:
    from collections.abc import Iterable


LOG = logging.getLogger(__name__)

COMMENT_TAGS = ('TRANSLATORS:',)
EXTRACT_METHOD = typing.cast('typing.Any', jinja2.ext.babel_extract)
NO_WRAP = 0
EXTRACT_OPTIONS = {
    'encoding': consts.DEFAULT_ENCODING,
    'extensions': ','.join(consts.JINJA_EXTENSIONS),
    'silent': 'false',
    'newstyle_gettext': 'true',
    'trimmed': str(consts.JINJA_I18N_TRIMMED).lower(),
}


class SourceFile(typing.Protocol):
    """A template file: a path relative to the template root and its text."""

    @property
    def file_name(self) -> str: ...

    @property
    def content(self) -> str: ...


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


def extract_catalog(files: Iterable[SourceFile], *, project: str,
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
