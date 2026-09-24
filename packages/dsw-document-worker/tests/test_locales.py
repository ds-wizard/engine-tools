import gettext

import polib
import pytest

from dsw.document_worker import consts
from dsw.document_worker.templates.locales import LocaleLoader
from dsw.templating import TemplateLocale


LOCALE_UUID = '44444444-4444-4444-4444-444444444444'
TENANT_UUID = '22222222-2222-2222-2222-222222222222'


def make_locale(updated_at='2026-01-01T00:00:00Z') -> TemplateLocale:
    return TemplateLocale(
        uuid=LOCALE_UUID,
        name='Czech',
        code='cs',
        updated_at=updated_at,
    )


def make_po_bytes(translations: dict[str, str]) -> bytes:
    po = polib.POFile()
    po.metadata = {
        'Content-Type': 'text/plain; charset=utf-8',
        'Language': 'cs',
    }
    for msgid, msgstr in translations.items():
        po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    return str(po).encode('utf-8')


@pytest.fixture
def loader(fake_context):
    return LocaleLoader(
        cache_dir=fake_context.workdir / consts.LOCALES_CACHE_DIR,
        tenant_uuid=TENANT_UUID,
    )


def test_load_locale_data():
    locale = TemplateLocale.load({
        'uuid': LOCALE_UUID,
        'name': 'Czech',
        'code': 'cs',
        'updatedAt': '2026-01-01T00:00:00Z',
    })
    assert locale is not None
    assert locale.uuid == LOCALE_UUID
    assert locale.code == 'cs'


def test_load_locale_none():
    assert TemplateLocale.load(None) is None


def test_load_locale_rejects_non_uuid():
    assert TemplateLocale.load({'uuid': 'not-a-uuid', 'name': 'X', 'code': 'cs'}) is None


def test_load_locale_rejects_missing_uuid():
    assert TemplateLocale.load({'name': 'X', 'code': 'cs'}) is None


def test_po_is_compiled_and_cached_in_s3(fake_context, loader):
    fake_context.s3.objects[f'{LOCALE_UUID}/{consts.LOCALE_PO_FILE_NAME}'] = make_po_bytes(
        {'Hello': 'Ahoj'},
    )
    translations = loader.load(make_locale())
    assert isinstance(translations, gettext.GNUTranslations)
    assert translations.gettext('Hello') == 'Ahoj'
    assert f'{LOCALE_UUID}/{consts.LOCALE_MO_FILE_NAME}' in fake_context.s3.stored


def test_compiled_mo_from_s3_is_preferred(fake_context, loader):
    po = polib.pofile(str(_write_po(fake_context, {'Hello': 'Ahoj'})))
    mo_path = fake_context.workdir / 'source.mo'
    po.save_as_mofile(str(mo_path))
    fake_context.s3.objects = {
        f'{LOCALE_UUID}/{consts.LOCALE_MO_FILE_NAME}': mo_path.read_bytes(),
    }
    translations = loader.load(make_locale())
    assert translations.gettext('Hello') == 'Ahoj'
    assert fake_context.s3.stored == []


def test_missing_locale_raises(loader):
    with pytest.raises(RuntimeError):
        loader.load(make_locale())


def test_cache_hit_avoids_s3(fake_context, loader):
    fake_context.s3.objects[f'{LOCALE_UUID}/{consts.LOCALE_PO_FILE_NAME}'] = make_po_bytes(
        {'Hello': 'Ahoj'},
    )
    loader.load(make_locale())
    fake_context.s3.downloads.clear()
    translations = loader.load(make_locale())
    assert translations.gettext('Hello') == 'Ahoj'
    assert fake_context.s3.downloads == []


def test_changed_updated_at_invalidates_cache(fake_context, loader):
    fake_context.s3.objects[f'{LOCALE_UUID}/{consts.LOCALE_PO_FILE_NAME}'] = make_po_bytes(
        {'Hello': 'Ahoj'},
    )
    loader.load(make_locale())
    fake_context.s3.objects = {
        f'{LOCALE_UUID}/{consts.LOCALE_PO_FILE_NAME}': make_po_bytes({'Hello': 'Nazdar'}),
    }
    fake_context.s3.downloads.clear()
    translations = loader.load(make_locale(updated_at='2026-02-02T00:00:00Z'))
    assert translations.gettext('Hello') == 'Nazdar'
    assert fake_context.s3.downloads != []


def test_mo_without_stamp_is_a_miss(fake_context, loader):
    fake_context.s3.objects[f'{LOCALE_UUID}/{consts.LOCALE_PO_FILE_NAME}'] = make_po_bytes(
        {'Hello': 'Ahoj'},
    )
    loader.load(make_locale())
    locale_dir = fake_context.workdir / consts.LOCALES_CACHE_DIR / LOCALE_UUID
    (locale_dir / consts.LOCALE_STAMP_FILE_NAME).unlink()
    (locale_dir / consts.LOCALE_MO_FILE_NAME).write_bytes(b'truncated')
    fake_context.s3.downloads.clear()

    translations = loader.load(make_locale())
    assert translations.gettext('Hello') == 'Ahoj'
    assert fake_context.s3.downloads != []


def _write_po(fake_context, translations):
    po_path = fake_context.workdir / 'source.po'
    po_path.write_bytes(make_po_bytes(translations))
    return po_path
