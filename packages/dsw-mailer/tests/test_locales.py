# cspell:ignore Servus
import datetime
import gettext
import pathlib

import pytest

from dsw.mailer.locales import LocaleLoader, match_code, resolve_mail_locale

from conftest import TENANT, mail_locale, po_bytes


@pytest.mark.parametrize(('code', 'available', 'expected'), [
    ('de', ['cs', 'de'], 'de'),
    ('de-AT', ['de', 'de-AT'], 'de-AT'),  # exact first
    ('de-AT', ['de'], 'de'),  # then the base language
    ('de', ['de-AT'], None),  # but not the other way round
    ('PT-br', ['pt-BR'], 'pt-BR'),
    ('fr', ['de'], None),
])
def test_match_code(code, available, expected):
    found = match_code(code, [mail_locale(c) for c in available])
    assert (None if found is None else found.code) == expected


@pytest.mark.parametrize(('ui_code', 'locales', 'expected'), [
    ('de', [mail_locale('de'), mail_locale('cs', default=True)], 'de'),
    ('de', [mail_locale('de', enabled=False), mail_locale('cs', default=True)], 'cs'),
    ('fr', [mail_locale('en'), mail_locale('cs', default=True)], 'cs'),
    (None, [mail_locale('de'), mail_locale('cs', default=True)], 'cs'),
    ('fr', [mail_locale('de'), mail_locale('en')], 'en'),
    ('fr', [mail_locale('de'), mail_locale('en', enabled=False)], None),
    (None, [], None),
])
def test_resolve_mail_locale(ui_code, locales, expected):
    found = resolve_mail_locale(ui_code, locales)
    assert (None if found is None else found.code) == expected


def german(translations: gettext.NullTranslations) -> str:
    return translations.gettext('Hello')


def test_compiles_po_and_stores_mo(fake_s3, tmp_path: pathlib.Path):
    locale = mail_locale('de')
    fake_s3.objects[(locale.uuid, 'mail.po')] = po_bytes({'Hello': 'Hallo'})
    loader = LocaleLoader(s3=fake_s3, cache_dir=tmp_path, tenant_uuid=TENANT)
    assert german(loader.load(locale)) == 'Hallo'
    assert fake_s3.downloads == [(locale.uuid, 'mail.mo'), (locale.uuid, 'mail.po')]
    assert fake_s3.stored == [(locale.uuid, 'mail.mo')]

    # the next mailer uses the stored mail.mo without compiling
    other = LocaleLoader(s3=fake_s3, cache_dir=tmp_path / 'other', tenant_uuid=TENANT)
    fake_s3.downloads.clear()
    assert german(other.load(locale)) == 'Hallo'
    assert fake_s3.downloads == [(locale.uuid, 'mail.mo')]
    assert fake_s3.stored == [(locale.uuid, 'mail.mo')]


def test_local_cache_until_the_po_is_replaced(fake_s3, tmp_path: pathlib.Path):
    locale = mail_locale('de')
    fake_s3.objects[(locale.uuid, 'mail.po')] = po_bytes({'Hello': 'Hallo'})
    loader = LocaleLoader(s3=fake_s3, cache_dir=tmp_path, tenant_uuid=TENANT)
    loader.load(locale)
    fake_s3.downloads.clear()
    assert german(loader.load(locale)) == 'Hallo'
    assert fake_s3.downloads == []  # cached locally

    # the backend replaces the PO, deletes mail.mo and bumps updated_at
    del fake_s3.objects[(locale.uuid, 'mail.mo')]
    fake_s3.objects[(locale.uuid, 'mail.po')] = po_bytes({'Hello': 'Servus'})
    replaced = mail_locale('de', updated_at=locale.updated_at + datetime.timedelta(minutes=1))
    assert german(loader.load(replaced)) == 'Servus'


def test_missing_po(fake_s3, tmp_path: pathlib.Path):
    loader = LocaleLoader(s3=fake_s3, cache_dir=tmp_path, tenant_uuid=TENANT)
    with pytest.raises(RuntimeError, match='Cannot download mail.po'):
        loader.load(mail_locale('de'))
