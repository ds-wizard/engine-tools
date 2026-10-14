import dataclasses
import datetime
import pathlib
import shutil
import types

import polib
import pytest

from dsw.database.model import DBLocale, DBMailTemplateLocale, DBUserEntity
from dsw.mailer.context import Context


TENANT = '00000000-0000-0000-0000-0000000000aa'
NOW = datetime.datetime(2026, 10, 14, 12, 0, tzinfo=datetime.UTC)
TEMPLATES_DIR = pathlib.Path(__file__).parent.parent / 'templates'


def make_locale[T: DBLocale](cls: type[T], code: str, *, enabled: bool = True,
                             default: bool = False, updated_at: datetime.datetime = NOW) -> T:
    return cls(uuid=f'uuid-{cls.TABLE_NAME}-{code}', tenant_uuid=TENANT, code=code,
               name=code, pot_version=None, enabled=enabled, default_locale=default,
               official=False, created_at=NOW, updated_at=updated_at)


def mail_locale(code: str, **kwargs) -> DBMailTemplateLocale:
    return make_locale(DBMailTemplateLocale, code, **kwargs)


def ui_locale(code: str, **kwargs) -> DBLocale:
    return make_locale(DBLocale, code, **kwargs)


def po_bytes(translations: dict[str, str]) -> bytes:
    po = polib.POFile()
    po.metadata = {'Content-Type': 'text/plain; charset=UTF-8', 'Language': 'de'}
    for msgid, msgstr in translations.items():
        po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    return str(po).encode('utf-8')


@dataclasses.dataclass
class FakeDB:
    users: dict[str, DBUserEntity] = dataclasses.field(default_factory=dict)
    ui_locales: list[DBLocale] = dataclasses.field(default_factory=list)
    mail_locales: list[DBMailTemplateLocale] = dataclasses.field(default_factory=list)

    def get_user(self, user_uuid: str, tenant_uuid: str):
        return self.users.get(user_uuid)

    def get_locale(self, locale_uuid: str, tenant_uuid: str):
        return next((x for x in self.ui_locales if x.uuid == locale_uuid), None)

    def get_mail_template_locale(self, locale_uuid: str, tenant_uuid: str):
        return next((x for x in self.mail_locales if x.uuid == locale_uuid), None)

    def get_enabled_mail_template_locales(self, tenant_uuid: str):
        return [x for x in self.mail_locales if x.enabled]

    def add_user(self, uuid: str, locale: DBLocale | None) -> None:
        self.users[uuid] = DBUserEntity(uuid=uuid, first_name='Jane', last_name='Doe',
                                        email=f'{uuid}@example.org',
                                        locale=None if locale is None else locale.uuid)


class FakeS3:
    """Objects keyed by (locale uuid, file name), as in mail-template-locales/<uuid>/<file>."""

    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}
        self.downloads: list[tuple[str, str]] = []
        self.stored: list[tuple[str, str]] = []

    def download_mail_template_locale(self, *, tenant_uuid, locale_uuid, file_name,
                                      target_path: pathlib.Path) -> bool:
        self.downloads.append((locale_uuid, file_name))
        data = self.objects.get((locale_uuid, file_name))
        if data is None:
            return False
        target_path.write_bytes(data)
        return True

    def store_mail_template_locale(self, *, tenant_uuid, locale_uuid, file_name,
                                   content_type, data: bytes):
        self.stored.append((locale_uuid, file_name))
        self.objects[(locale_uuid, file_name)] = data


@pytest.fixture
def fake_db() -> FakeDB:
    return FakeDB()


@pytest.fixture
def fake_s3() -> FakeS3:
    return FakeS3()


@pytest.fixture
def context(fake_db: FakeDB, fake_s3: FakeS3, tmp_path: pathlib.Path):
    templates = tmp_path / 'templates'
    shutil.copytree(TEMPLATES_DIR, templates)
    previous = Context._instance  # noqa: SLF001
    Context._instance = types.SimpleNamespace(  # noqa: SLF001
        app=types.SimpleNamespace(db=fake_db, s3=fake_s3, workdir=templates),
    )
    yield Context.get()
    Context._instance = previous  # noqa: SLF001
