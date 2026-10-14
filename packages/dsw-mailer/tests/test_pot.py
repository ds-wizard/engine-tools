import hashlib
import pathlib
import types

import click.testing
import polib
import pytest

from dsw.mailer import pot
from dsw.mailer.cli import cli
from dsw.mailer.mailer import Mailer
from dsw.storage import ObjectInfo

from conftest import TEMPLATES_DIR


def test_build_pot_from_the_templates():
    data = pot.build_pot(TEMPLATES_DIR, 'dsw-mail-templates:5.0.0')
    assert data == pot.build_pot(TEMPLATES_DIR, 'dsw-mail-templates:5.0.0')
    catalog = polib.pofile(data.decode())
    assert catalog.metadata['Project-Id-Version'] == 'dsw-mail-templates:5.0.0'
    reset = catalog.find('Forgot your password? No problem, that happens to the best of us!')
    assert reset is not None
    assert ('wizard/resetPassword/message.txt.j2', '5') in reset.occurrences
    # the registry and wizard templates and the common parts are in one POT
    files = {name.split('/')[0] for entry in catalog for name, _ in entry.occurrences}
    assert files == {'_common', 'registry', 'wizard'}
    assert pot.project_id_version(data) == ('dsw-mail-templates', '5.0.0')


def test_plural_messages(tmp_path: pathlib.Path):
    (tmp_path / 'a.html.j2').write_text(
        '{% trans count=n %}One day{% pluralize %}{{ count }} days{% endtrans %}\n'
        '{% do x.append(1) %}{{ _("Hello") }}')
    catalog = polib.pofile(pot.build_pot(tmp_path, 'k:1').decode())
    assert [(e.msgid, e.msgid_plural) for e in catalog] == \
        [('One day', '%(count)s days'), ('Hello', '')]


@pytest.mark.parametrize('header', ['', 'Project-Id-Version: 5.0.0\\n', 'Project-Id-Version: k:\\n'])
def test_project_id_version_must_have_kind_and_version(header):
    data = f'msgid ""\nmsgstr "{header}"\n'.encode()
    with pytest.raises(ValueError, match='<kind>:<version>'):
        pot.project_id_version(data)


MD5 = 'a' * 32


def stored(version: str | None, etag: str = MD5) -> ObjectInfo:
    return ObjectInfo(metadata={} if version is None else {'version': version}, etag=etag)


@pytest.mark.parametrize(('info', 'force', 'expected'), [
    (None, False, pot.SyncResult.UPLOADED),
    (stored('4.35.0'), False, pot.SyncResult.REPLACED),
    (stored('5.0.0rc1'), False, pot.SyncResult.REPLACED),
    (stored('5.0.0'), False, pot.SyncResult.UP_TO_DATE),
    (stored('5.0.0', etag='b' * 32), False, pot.SyncResult.REPLACED),  # rebuilt
    (stored('5.0.1'), False, pot.SyncResult.NEWER_STORED),  # never downgrade
    (stored('5.0.0.post3.dev0+abc'), False, pot.SyncResult.NEWER_STORED),
    (stored('5.0.1'), True, pot.SyncResult.REPLACED),
    (stored('5.0.0'), True, pot.SyncResult.UP_TO_DATE),  # nothing to replace
    (stored(None), False, pot.SyncResult.REPLACED),
    (stored('garbage'), False, pot.SyncResult.REPLACED),
])
def test_decide(info, force, expected):
    assert pot.decide(info, '5.0.0', MD5, force=force) == expected


class FakeInstanceS3:

    def __init__(self, info: ObjectInfo | None = None, fail: bool = False):
        self.info = info
        self.fail = fail
        self.stored: list[tuple[str, bytes, dict]] = []

    def head_instance_object(self, *, object_name):
        if self.fail:
            raise ConnectionError('S3 is down')
        return self.info

    def store_instance_object(self, *, object_name, content_type, data, metadata):
        self.stored.append((object_name, data, metadata))
        self.info = ObjectInfo(metadata=metadata, etag=hashlib.md5(data).hexdigest())


@pytest.fixture
def templates(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / 'a.txt.j2').write_text('{% trans %}Hello{% endtrans %}')
    (tmp_path / 'locale').mkdir()
    (tmp_path / 'locale' / 'mail.pot').write_bytes(pot.build_pot(tmp_path, 'fw-mail-templates:5.0.0'))
    return tmp_path


def test_sync_uploads_then_is_up_to_date(templates):
    s3 = FakeInstanceS3()
    assert pot.sync_default_pot(s3, templates) == pot.SyncResult.UPLOADED
    assert s3.stored[0][0] == 'mail-templates/mail.pot'
    assert s3.stored[0][2] == {'version': '5.0.0'}
    assert pot.sync_default_pot(s3, templates) == pot.SyncResult.UP_TO_DATE
    assert len(s3.stored) == 1


def test_sync_keeps_a_newer_pot_unless_forced(templates):
    s3 = FakeInstanceS3(stored('5.1.0'))
    assert pot.sync_default_pot(s3, templates) == pot.SyncResult.NEWER_STORED
    assert s3.stored == []
    assert pot.sync_default_pot(s3, templates, force=True) == pot.SyncResult.REPLACED
    assert s3.stored[0][2] == {'version': '5.0.0'}


def startup_mailer(templates: pathlib.Path, s3, *, enabled: bool = True) -> Mailer:
    Mailer._default_pot_synced = False  # noqa: SLF001
    mailer = Mailer.__new__(Mailer)
    mailer.workdir = templates
    mailer.cfg = types.SimpleNamespace(mail=types.SimpleNamespace(sync_default_pot=enabled))
    mailer.ctx = types.SimpleNamespace(app=types.SimpleNamespace(s3=s3))
    return mailer


def test_startup_sync_never_blocks(templates, caplog):
    startup_mailer(templates, FakeInstanceS3(fail=True))._sync_default_pot_at_startup()  # noqa: SLF001
    assert 'Cannot sync the default mail POT: S3 is down' in caplog.text


def test_startup_sync_once_per_process_and_switchable(templates):
    s3 = FakeInstanceS3()
    mailer = startup_mailer(templates, s3)
    mailer._sync_default_pot_at_startup()  # noqa: SLF001
    s3.info = None
    mailer._sync_default_pot_at_startup()  # noqa: SLF001
    assert len(s3.stored) == 1
    s3 = FakeInstanceS3()
    startup_mailer(templates, s3, enabled=False)._sync_default_pot_at_startup()  # noqa: SLF001
    assert s3.stored == []


def test_startup_without_a_pot(tmp_path, caplog):
    s3 = FakeInstanceS3()
    startup_mailer(tmp_path, s3)._sync_default_pot_at_startup()  # noqa: SLF001
    assert s3.stored == []
    assert 'dsw-mailer make-pot' in caplog.text


def test_cli_make_pot(templates):
    result = click.testing.CliRunner().invoke(cli, obj={}, args=[
        'make-pot', str(templates), '--kind', 'fw-mail-templates', '--version', '5.0.2'])
    assert result.exit_code == 0, result.output
    assert pot.project_id_version((templates / 'locale' / 'mail.pot').read_bytes()) == \
        ('fw-mail-templates', '5.0.2')


def test_cli_make_pot_needs_templates():
    result = click.testing.CliRunner().invoke(cli, obj={}, args=['make-pot'])
    assert result.exit_code == 2
    assert 'Missing the templates directory' in result.output


def test_cli_make_pot_ignores_a_missing_config(templates, monkeypatch, tmp_path):
    # the image sets APPLICATION_CONFIG_PATH, but builds the POT without a config
    monkeypatch.setenv('APPLICATION_CONFIG_PATH', str(tmp_path / 'missing.yml'))
    result = click.testing.CliRunner().invoke(cli, obj={}, args=['make-pot', str(templates)])
    assert result.exit_code == 0, result.output


def test_cli_missing_config_for_a_command_that_needs_it(templates, tmp_path):
    result = click.testing.CliRunner().invoke(cli, obj={}, args=[
        '-c', str(tmp_path / 'missing.yml'), '-w', str(templates), 'sync-default-pot'])
    assert result.exit_code == 2
    assert 'missing.yml' in result.output
