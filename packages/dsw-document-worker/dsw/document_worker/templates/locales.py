from __future__ import annotations

import gettext
import logging
import typing

import polib

from .. import consts
from ..context import Context


if typing.TYPE_CHECKING:
    from pathlib import Path

    from dsw.templating import TemplateLocale


LOG = logging.getLogger(__name__)


class LocaleLoader:

    def __init__(self, *, cache_dir: Path, tenant_uuid: str):
        self.cache_dir = cache_dir
        self.tenant_uuid = tenant_uuid

    def load(self, locale: TemplateLocale) -> gettext.NullTranslations:
        locale_dir = self.cache_dir / locale.uuid
        mo_path = locale_dir / consts.LOCALE_MO_FILE_NAME
        stamp_path = locale_dir / consts.LOCALE_STAMP_FILE_NAME
        if not self._is_cached(mo_path, stamp_path, locale):
            locale_dir.mkdir(parents=True, exist_ok=True)
            stamp_path.unlink(missing_ok=True)
            self._prepare_mo_file(locale, mo_path)
            stamp_path.write_text(locale.updated_at, encoding=consts.DEFAULT_ENCODING)
        with mo_path.open('rb') as fp:
            return gettext.GNUTranslations(fp)

    @staticmethod
    def _is_cached(mo_path: Path, stamp_path: Path, locale: TemplateLocale) -> bool:
        if not mo_path.exists() or not stamp_path.exists():
            return False
        return stamp_path.read_text(encoding=consts.DEFAULT_ENCODING) == locale.updated_at

    def _prepare_mo_file(self, locale: TemplateLocale, mo_path: Path):
        if self._download(locale, consts.LOCALE_MO_FILE_NAME, mo_path):
            LOG.debug('Using compiled locale %s from S3', locale.uuid)
            return
        po_path = mo_path.parent / consts.LOCALE_PO_FILE_NAME
        if not self._download(locale, consts.LOCALE_PO_FILE_NAME, po_path):
            raise RuntimeError(f'Cannot download locale file of {locale.uuid}')
        polib.pofile(str(po_path)).save_as_mofile(str(mo_path))
        LOG.debug('Compiled locale %s from PO file', locale.uuid)
        Context.get().app.s3.store_document_template_locale(
            tenant_uuid=self.tenant_uuid,
            locale_uuid=locale.uuid,
            file_name=consts.LOCALE_MO_FILE_NAME,
            content_type='application/octet-stream',
            data=mo_path.read_bytes(),
        )

    def _download(self, locale: TemplateLocale, file_name: str, target_path: Path) -> bool:
        return Context.get().app.s3.download_document_template_locale(
            tenant_uuid=self.tenant_uuid,
            locale_uuid=locale.uuid,
            file_name=file_name,
            target_path=target_path,
        )
