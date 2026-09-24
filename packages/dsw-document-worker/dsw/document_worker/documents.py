from __future__ import annotations

import typing

import pathvalidate
import slugify

from . import consts
from .context import Context


if typing.TYPE_CHECKING:
    from dsw.database.model import DBDocument
    from dsw.templating import DocumentFile


def _name_uuid(document: DBDocument) -> str:
    return document.uuid


def _name_sanitize(document: DBDocument) -> str:
    name = str(pathvalidate.sanitize_filename(document.name))
    if len(name) == 0:
        name = document.uuid
    return name


def _name_slugify(document: DBDocument) -> str:
    name = slugify.slugify(document.name)
    if len(name) == 0:
        name = document.uuid
    return name


class DocumentNameGiver:

    _FALLBACK: typing.Callable[[DBDocument], str] = _name_uuid
    _STRATEGIES: dict[str, typing.Callable[[DBDocument], str]] = {
        consts.DocumentNamingStrategy.UUID: _name_uuid,
        consts.DocumentNamingStrategy.SANITIZE: _name_sanitize,
        consts.DocumentNamingStrategy.SLUGIFY: _name_slugify,
    }

    @classmethod
    def name_document(cls, document_metadata: DBDocument,
                      document_file: DocumentFile) -> str:
        config = Context.get().app.cfg
        strategy = cls._STRATEGIES.get(config.doc.naming_strategy, cls._FALLBACK)
        return document_file.filename(strategy(document_metadata))
