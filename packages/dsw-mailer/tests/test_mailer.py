# cspell:ignore Passwort vergessen Kein
import gettext
import pathlib
import types

import polib
import pytest

from dsw.database.model import PersistentCommand
from dsw.mailer.mailer import Mailer, MailerCommand
from dsw.mailer.templates import TemplateRegistry

from conftest import TENANT, mail_locale, po_bytes, ui_locale


def command(recipients: list[dict], **body) -> PersistentCommand:
    return PersistentCommand(
        uuid='cmd-1', state='NewPersistentCommandState', component='Mailer',
        function='sendMail', body={
            'mode': 'wizard', 'template': 'resetPassword', 'recipients': recipients,
            'parameters': {'clientUrl': 'https://wizard.example.org', 'userFirstName': 'Jane',
                           'userUuid': 'u', 'hash': 'h'},
            **body,
        }, last_error_message=None, attempts=0, max_attempts=3, tenant_uuid=TENANT,
        created_by=None, created_at=None, updated_at=None,
    )


def mailer(tmp_path: pathlib.Path) -> Mailer:
    instance = Mailer.__new__(Mailer)
    instance.cache_dir = tmp_path / 'cache'
    return instance


def requests_for(tmp_path, cmd: PersistentCommand):
    return mailer(tmp_path)._get_msg_requests(MailerCommand.load(cmd))  # noqa: SLF001


@pytest.fixture
def tenant(fake_db, context):
    de, cs = ui_locale('de'), ui_locale('cs')
    fake_db.ui_locales += [de, cs, ui_locale('fr', enabled=False)]
    fake_db.mail_locales += [mail_locale('de'), mail_locale('cs'),
                             mail_locale('en', default=True)]
    fake_db.add_user('user-de', de)
    fake_db.add_user('user-cs', cs)
    fake_db.add_user('user-fr', fake_db.ui_locales[2])
    fake_db.add_user('user-none', None)
    return fake_db


def recipient(uuid: str | None) -> dict:
    return {'uuid': uuid, 'email': f'{uuid}@example.org'}


def test_one_mail_per_recipient_in_their_language(tmp_path, tenant):
    requests = requests_for(tmp_path, command([recipient('user-de'), recipient('user-cs')]))
    assert [(r.recipients[0].uuid, r.locale_uuid) for r in requests] == [
        ('user-de', 'uuid-mail_template_locale-de'),
        ('user-cs', 'uuid-mail_template_locale-cs'),
    ]
    assert [len(r.recipients) for r in requests] == [1, 1]
    # each request renders its own copy of the context
    assert requests[0].ctx is not requests[1].ctx
    assert requests[0].ctx['_meta']['recipients'] == requests[0].recipients


@pytest.mark.parametrize('uuid', ['user-fr', 'user-none', 'not-a-user', None])
def test_default_mail_locale(tmp_path, tenant, uuid):
    # disabled UI locale, no UI locale, unknown user, not a user yet
    requests = requests_for(tmp_path, command([recipient(uuid)]))
    assert [r.locale_uuid for r in requests] == ['uuid-mail_template_locale-en']


def test_send_as_one_in_english(tmp_path, tenant):
    requests = requests_for(tmp_path, command([recipient('user-de'), recipient('user-cs')],
                                              sendAsOne=True))
    assert len(requests) == 1
    assert requests[0].locale_uuid is None
    assert [r.uuid for r in requests[0].recipients] == ['user-de', 'user-cs']


def test_registry_mode_is_unchanged(tmp_path, tenant):
    requests = requests_for(tmp_path, command([recipient('user-de')], mode='registry'))
    assert [r.locale_uuid for r in requests] == [None]


def test_no_recipients(tmp_path, tenant):
    with pytest.raises(RuntimeError, match='No recipients'):
        requests_for(tmp_path, command([]))


def test_translations_fall_back_to_english(tmp_path, tenant, fake_s3):
    instance = mailer(tmp_path)
    rq = requests_for(tmp_path, command([recipient('user-de')]))[0]
    # the PO is missing in S3
    assert type(instance._translations(rq)) is gettext.NullTranslations  # noqa: SLF001
    fake_s3.objects[('uuid-mail_template_locale-de', 'mail.po')] = po_bytes({'x': 'y'})
    assert isinstance(instance._translations(rq), gettext.GNUTranslations)  # noqa: SLF001
    tenant.mail_locales[0].enabled = False
    assert type(instance._translations(rq)) is gettext.NullTranslations  # noqa: SLF001


def test_render_translated_builtin_template(tmp_path, tenant, context):
    templates = TemplateRegistry(cfg=types.SimpleNamespace(), workdir=context.app.workdir)
    rq = requests_for(tmp_path, command([recipient('user-de')]))[0]
    po = polib.pofile(po_bytes({
        'Forgot your password? No problem, that happens to the best of us!':
            'Passwort vergessen? Kein Problem!',
    }).decode())
    mo_path = tmp_path / 'de.mo'
    po.save_as_mofile(str(mo_path))
    with mo_path.open('rb') as fp:
        translations = gettext.GNUTranslations(fp)
    cfg = types.SimpleNamespace(name='Wizard', email='wizard@example.org')
    message = templates.render(rq, cfg, translations)
    assert 'Passwort vergessen? Kein Problem!' in message.plain_body
    assert message.recipients == ['user-de@example.org']
    # English again with null translations, on the same environment
    rq = requests_for(tmp_path, command([recipient('user-de')]))[0]
    message = templates.render(rq, cfg, gettext.NullTranslations())
    assert 'Forgot your password? No problem' in message.plain_body
