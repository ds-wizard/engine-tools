import dataclasses
import types

import pytest

from dsw.command_queue import CommandJobError
from dsw.document_worker.pot import (
    PotFileRequest,
    extract_catalog,
    render_pot_file,
)


@dataclasses.dataclass
class FakeTemplateFile:
    file_name: str
    content: str


def make_command(**body):
    return types.SimpleNamespace(
        uuid='11111111-1111-1111-1111-111111111111',
        tenant_uuid='22222222-2222-2222-2222-222222222222',
        function='generatePotFile',
        body=body,
    )


def make_pot(*files, language='en'):
    result = extract_catalog(
        [FakeTemplateFile(name, content) for name, content in files],
        project='org:tid:1.0.0',
        version='1.0.0',
        language=language,
    )
    return result, render_pot_file(result).decode('utf-8')


def test_extract_trans_block():
    _, pot = make_pot(('src/a.j2', '{% trans %}Hello{% endtrans %}'))
    assert 'msgid "Hello"' in pot
    assert '#: src/a.j2:1' in pot


def test_extract_plural():
    _, pot = make_pot((
        'src/a.j2',
        '{% trans count %}{{ count }} item{% pluralize %}{{ count }} items{% endtrans %}',
    ))
    assert 'msgid "%(count)s item"' in pot
    assert 'msgid_plural "%(count)s items"' in pot
    assert 'msgstr[0] ""' in pot
    assert 'msgstr[1] ""' in pot


def test_extract_underscore_and_pgettext():
    _, pot = make_pot(('src/a.j2', "{{ _('World') }}\n{{ pgettext('menu', 'Open') }}"))
    assert 'msgid "World"' in pot
    assert 'msgctxt "menu"' in pot
    assert 'msgid "Open"' in pot


def test_extract_translators_comment():
    _, pot = make_pot((
        'src/a.j2',
        '{# TRANSLATORS: shown on top #}\n{% trans %}Hello{% endtrans %}',
    ))
    assert '#. shown on top' in pot


def test_extract_survives_do_extension():
    _, pot = make_pot(('src/a.j2', "{% do [] %}{{ _('Alpha') }}"))
    assert 'msgid "Alpha"' in pot


def test_extract_survives_loopcontrols_extension():
    _, pot = make_pot((
        'src/a.j2',
        "{% for i in [1] %}{% break %}{% endfor %}{{ _('Alpha') }}",
    ))
    assert 'msgid "Alpha"' in pot


def test_broken_file_is_isolated():
    result, pot = make_pot(
        ('src/broken.j2', '{% if %}'),
        ('src/ok.j2', "{{ _('Alpha') }}"),
    )
    assert result.failed_files == ['src/broken.j2']
    assert 'msgid "Alpha"' in pot
    assert 'Skipped files that could not be parsed: src/broken.j2' in pot


def test_header_fields():
    _, pot = make_pot(('src/a.j2', "{{ _('Alpha') }}"), language='cs')
    assert 'Project-Id-Version: org:tid:1.0.0 1.0.0' in pot
    assert 'Language: cs' in pot
    assert 'Plural-Forms: nplurals=' in pot
    assert 'charset=utf-8' in pot
    assert '#, fuzzy' not in pot


def test_header_without_known_language():
    _, pot = make_pot(('src/a.j2', "{{ _('Alpha') }}"), language='not a language')
    assert 'msgid "Alpha"' in pot
    assert 'Language:' not in pot
    assert 'Plural-Forms:' not in pot


def test_messages_are_sorted():
    _, pot = make_pot(('src/a.j2', "{{ _('Beta') }}{{ _('Alpha') }}"))
    assert pot.index('msgid "Alpha"') < pot.index('msgid "Beta"')


def test_request_load_ok():
    rq = PotFileRequest.load(make_command(
        documentTemplateUuid='33333333-3333-3333-3333-333333333333',
        organizationId='org',
        templateId='tid',
        version='1.0.0',
        language='cs',
    ))
    assert rq.coordinates == 'org:tid:1.0.0'
    assert rq.file_name == 'org_tid_1.0.0.pot'
    assert rq.language == 'cs'


def test_request_load_without_language():
    rq = PotFileRequest.load(make_command(
        documentTemplateUuid='33333333-3333-3333-3333-333333333333',
        organizationId='org',
        templateId='tid',
        version='1.0.0',
        language=None,
    ))
    assert rq.language == 'en'


def test_request_load_rejects_bad_uuid():
    with pytest.raises(CommandJobError) as e:
        PotFileRequest.load(make_command(
            documentTemplateUuid='not-a-uuid',
            organizationId='org',
            templateId='tid',
            version='1.0.0',
        ))
    assert not e.value.try_again


@pytest.mark.parametrize('field', ['organizationId', 'templateId', 'version'])
def test_request_load_rejects_traversal(field):
    body = {
        'documentTemplateUuid': '33333333-3333-3333-3333-333333333333',
        'organizationId': 'org',
        'templateId': 'tid',
        'version': '1.0.0',
    }
    body[field] = '../../etc/passwd'
    with pytest.raises(CommandJobError) as e:
        PotFileRequest.load(make_command(**body))
    assert not e.value.try_again
