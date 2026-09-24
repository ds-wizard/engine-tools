import dataclasses

from dsw.templating.pot import extract_catalog, render_pot_file


@dataclasses.dataclass
class FakeTemplateFile:
    file_name: str
    content: str


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
