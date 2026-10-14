"""`render` fills ``document`` of a 19.0 context (WEP 24, "render fills document").

`get-context` and `generate-context` write ``document: null``; the document worker fills it from
the document being generated. Locally there is no document, so it is made up from the template
being rendered, the format, and the `render` options.
"""
from __future__ import annotations

import dataclasses
import datetime
import json
import typing

import pydantic

from dsw.models.common import format_timestamp
from dsw.models.document_context.validation import pointer
from dsw.models.document_context.wire import DocumentContext
from dsw.models.strictness import load


if typing.TYPE_CHECKING:
    import pathlib

    from ..model import Format, Template


NIL_UUID = '00000000-0000-0000-0000-000000000000'


@dataclasses.dataclass(frozen=True)
class DocumentOptions:
    """The `render` options that override ``document``; ``None`` keeps the value."""

    language: str | None = None
    #: with ``language``, make a locale for it instead of resetting it (`--po`)
    with_locale: bool = False
    preview: bool | None = None
    event_uuid: str | None = None
    name: str | None = None
    now: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC))


class InvalidContextError(RuntimeError):
    pass


def load_context(path: pathlib.Path) -> dict:
    """Parse and validate a 19.0 context; partial contexts are rejected."""
    try:
        context = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        raise InvalidContextError(f'{path}: not valid JSON ({e})') from e
    try:
        load(DocumentContext, context)
    except pydantic.ValidationError as e:
        problems = '\n'.join(f'  {pointer(*error["loc"]) or "/"}: {error["msg"]}'
                             for error in e.errors())
        raise InvalidContextError(f'{path}: not a valid document context '
                                  f'(metamodel 19.0):\n{problems}') from e
    return context


def fill_document(context: dict, template: Template, format_spec: Format,
                  options: DocumentOptions) -> list[str]:
    """Fill ``context['document']`` in place; returns warnings."""
    warnings: list[str] = []
    now = format_timestamp(options.now)
    document = context.get('document') or _stub(context, now)
    old_template = document.get('documentTemplate') or {}
    new_template = {
        'uuid': old_template.get('uuid') or template.uuid or NIL_UUID,
        'id': template.id,
        'version': template.version,
        'workspaceUuid': old_template.get('workspaceUuid'),
    }
    if old_template and (old_template.get('id'), old_template.get('version')) != \
            (template.id, template.version):
        warnings.append(f'The context is for template {old_template.get("id")}:'
                        f'{old_template.get("version")}, rendering with the local '
                        f'{template.id}:{template.version}')
    old_format = document.get('format')
    new_format = {'uuid': str(format_spec.uuid), 'name': format_spec.name}
    if old_format and old_format != new_format:
        warnings.append(f'The context is for format "{old_format.get("name")}", '
                        f'rendering "{format_spec.name}"')
    document = {**document, 'documentTemplate': new_template, 'format': new_format}
    if options.language is not None:
        document['language'] = options.language
        document['locale'] = None
        if options.with_locale:
            document['locale'] = {'uuid': NIL_UUID, 'name': options.language,
                                  'code': options.language, 'createdAt': now, 'updatedAt': now}
    if options.preview is not None:
        document['preview'] = options.preview
    if options.event_uuid is not None:
        document['eventUuid'] = options.event_uuid
    if options.name is not None:
        document['name'] = options.name
    context['document'] = document
    return warnings


def _stub(context: dict, now: str) -> dict:
    source = context.get('project') or context.get('knowledgeModelEditor') or {}
    return {
        'uuid': NIL_UUID,
        'name': source.get('name', ''),
        'language': None,
        'locale': None,
        'preview': True,
        'eventUuid': None,
        'createdBy': None,
        'createdAt': now,
    }
