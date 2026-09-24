from __future__ import annotations

import dataclasses
import gettext
import logging
import uuid


LOG = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class TemplateLocale:
    uuid: str
    name: str
    code: str
    updated_at: str

    @staticmethod
    def load(data: dict | None) -> TemplateLocale | None:
        if not isinstance(data, dict):
            return None
        try:
            locale_uuid = str(uuid.UUID(str(data['uuid'])))
        except (KeyError, ValueError):
            LOG.warning('Ignoring locale without a valid UUID')
            return None
        return TemplateLocale(
            uuid=locale_uuid,
            name=str(data.get('name', '')),
            code=str(data.get('code', '')),
            updated_at=str(data.get('updatedAt', '')),
        )


@dataclasses.dataclass
class RenderContext:
    translations: gettext.NullTranslations
    language: str | None = None
    locale: TemplateLocale | None = None

    @staticmethod
    def null(language: str | None = None) -> RenderContext:
        return RenderContext(
            translations=gettext.NullTranslations(),
            language=language,
        )
