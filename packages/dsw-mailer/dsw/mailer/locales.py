"""Mail template locales: which one a recipient gets, and its compiled translations (WEP 27, B6).

A mail template locale is a PO file per tenant at ``mail-template-locales/<uuid>/mail.po``. The
compiled ``mail.mo`` is cached next to it in S3 by the first mailer that needs it, and locally
by ``(uuid, updated_at)``; the backend deletes it and bumps ``updated_at`` when the PO changes.
"""
from __future__ import annotations

import gettext
import logging
import typing

import polib


if typing.TYPE_CHECKING:
    import pathlib
    from collections.abc import Iterable

    from dsw.database.model import DBMailTemplateLocale
    from dsw.storage import S3Storage


LOG = logging.getLogger(__name__)

PO_FILE_NAME = 'mail.po'
MO_FILE_NAME = 'mail.mo'
STAMP_FILE_NAME = 'updated_at'
MO_CONTENT_TYPE = 'application/octet-stream'
#: the last resort before the built-in English
ENGLISH_CODE = 'en'


def match_code[T: DBMailTemplateLocale](code: str, locales: Iterable[T]) -> T | None:
    """The locale with exactly this code, otherwise with its base language.

    ``de-AT`` matches ``de``, but ``de`` does not match ``de-AT``. Codes are BCP 47, compared
    case-insensitively.
    """
    by_code = {locale.code.casefold(): locale for locale in locales}
    wanted = code.casefold()
    return by_code.get(wanted) or by_code.get(wanted.split('-', 1)[0])


def resolve_mail_locale[T: DBMailTemplateLocale](ui_code: str | None,
                                                  locales: Iterable[T]) -> T | None:
    """The mail template locale for a recipient whose UI locale has ``ui_code``.

    In order: the match of the UI locale code, the tenant's default, the ``en`` locale, and
    ``None`` for the built-in English. Disabled locales are skipped.
    """
    enabled = [locale for locale in locales if locale.enabled]
    if ui_code:
        found = match_code(ui_code, enabled)
        if found is not None:
            return found
    default = next((locale for locale in enabled if locale.default_locale), None)
    if default is not None:
        return default
    return next((locale for locale in enabled
                 if locale.code.casefold() == ENGLISH_CODE), None)


class LocaleLoader:
    """Translations of a mail template locale, compiled once and cached in S3 and locally."""

    def __init__(self, *, s3: S3Storage, cache_dir: pathlib.Path, tenant_uuid: str):
        self.s3 = s3
        self.cache_dir = cache_dir
        self.tenant_uuid = tenant_uuid

    def load(self, locale: DBMailTemplateLocale) -> gettext.GNUTranslations:
        locale_dir = self.cache_dir / locale.uuid
        mo_path = locale_dir / MO_FILE_NAME
        stamp_path = locale_dir / STAMP_FILE_NAME
        stamp = locale.updated_at.isoformat()
        if not mo_path.exists() or not stamp_path.exists() or \
                stamp_path.read_text(encoding='utf-8') != stamp:
            locale_dir.mkdir(parents=True, exist_ok=True)
            stamp_path.unlink(missing_ok=True)
            self._prepare_mo_file(locale, mo_path)
            stamp_path.write_text(stamp, encoding='utf-8')
        with mo_path.open('rb') as fp:
            return gettext.GNUTranslations(fp)

    def _prepare_mo_file(self, locale: DBMailTemplateLocale, mo_path: pathlib.Path):
        if self._download(locale, MO_FILE_NAME, mo_path):
            LOG.debug('Using compiled mail template locale %s from S3', locale.uuid)
            return
        po_path = mo_path.parent / PO_FILE_NAME
        if not self._download(locale, PO_FILE_NAME, po_path):
            raise RuntimeError(f'Cannot download {PO_FILE_NAME} of mail template locale '
                               f'{locale.uuid}')
        polib.pofile(str(po_path)).save_as_mofile(str(mo_path))
        LOG.info('Compiled mail template locale %s (%s), storing %s',
                 locale.uuid, locale.code, MO_FILE_NAME)
        self.s3.store_mail_template_locale(
            tenant_uuid=self.tenant_uuid,
            locale_uuid=locale.uuid,
            file_name=MO_FILE_NAME,
            content_type=MO_CONTENT_TYPE,
            data=mo_path.read_bytes(),
        )

    def _download(self, locale: DBMailTemplateLocale, file_name: str,
                  target_path: pathlib.Path) -> bool:
        return self.s3.download_mail_template_locale(
            tenant_uuid=self.tenant_uuid,
            locale_uuid=locale.uuid,
            file_name=file_name,
            target_path=target_path,
        )
