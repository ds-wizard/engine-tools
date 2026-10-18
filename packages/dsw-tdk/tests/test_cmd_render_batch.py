import datetime
import json
import pathlib

import click.testing
import pytest

from dsw.models.document_context.validation import validate_context
from dsw.tdk import main
from dsw.tdk.context import generate
from dsw.tdk.context.document import NIL_UUID, DocumentOptions, fill_document
from dsw.tdk.context.inputs import sample_input
from dsw.tdk.context.profiles import PROFILE_BY_NAME, PROFILES
from dsw.tdk.model import Format, Template


NOW = datetime.datetime(2030, 1, 2, 3, 4, 5, tzinfo=datetime.UTC)
TEMPLATE_DOCUMENT = {'uuid': NIL_UUID, 'id': 'test.render01', 'version': '1.0.0',
                     'workspaceUuid': None}
JSON_FORMAT = {'uuid': 'd3e98eb6-344d-481f-8e37-6a67b6cd1ad2', 'name': 'JSON Data'}


def template_and_format() -> tuple[Template, Format]:
    template = Template(id='test.render01', version='1.0.0')
    format_spec = Format(uuid=JSON_FORMAT['uuid'], name=JSON_FORMAT['name'])
    return template, format_spec


def fixture_context(fixtures_path: pathlib.Path) -> dict:
    context = fixtures_path / 'test_render01' / 'context.json'
    return json.loads(context.read_text(encoding='utf-8'))


def errors(context: dict) -> list[str]:
    return [str(i) for i in validate_context(context) if i.severity == 'error']


# filling document

def test_fill_stub(fixtures_path: pathlib.Path):
    context = fixture_context(fixtures_path)
    assert context['document'] is None
    warnings = fill_document(context, *template_and_format(), DocumentOptions(now=NOW))
    assert warnings == []
    assert context['document'] == {
        'uuid': NIL_UUID, 'name': 'My Plan', 'language': None, 'locale': None,
        'preview': True, 'eventUuid': None, 'createdBy': None,
        'createdAt': '2030-01-02T03:04:05Z',
        'documentTemplate': TEMPLATE_DOCUMENT, 'format': JSON_FORMAT,
    }
    assert errors(context) == []


def test_fill_keeps_existing_and_options_override(fixtures_path: pathlib.Path):
    context = fixture_context(fixtures_path)
    fill_document(context, *template_and_format(), DocumentOptions(now=NOW))
    context['document'].update(uuid='33333333-0000-0000-0000-000000000001', name='Kept',
                               preview=False, createdAt='2029-01-01T00:00:00Z')
    fill_document(context, *template_and_format(), DocumentOptions(now=NOW))
    document = context['document']
    assert (document['uuid'], document['name'], document['preview'], document['createdAt']) == \
        ('33333333-0000-0000-0000-000000000001', 'Kept', False, '2029-01-01T00:00:00Z')

    event = '44444444-0000-0000-0000-000000000001'
    fill_document(context, *template_and_format(), DocumentOptions(
        now=NOW, language='cs', with_locale=True, preview=True, event_uuid=event,
        name='Renamed'))
    document = context['document']
    assert (document['language'], document['preview'], document['eventUuid'],
            document['name']) == ('cs', True, event, 'Renamed')
    assert document['locale'] == {'uuid': NIL_UUID, 'name': 'cs', 'code': 'cs',
                                  'createdAt': '2030-01-02T03:04:05Z',
                                  'updatedAt': '2030-01-02T03:04:05Z'}
    fill_document(context, *template_and_format(), DocumentOptions(now=NOW, language='de'))
    assert (context['document']['language'], context['document']['locale']) == ('de', None)
    assert errors(context) == []


def test_fill_warns_about_another_template_and_format(fixtures_path: pathlib.Path):
    context = fixture_context(fixtures_path)
    fill_document(context, *template_and_format(), DocumentOptions(now=NOW))
    workspace = '55555555-0000-0000-0000-000000000001'
    context['document']['documentTemplate'] = {
        'uuid': '66666666-0000-0000-0000-000000000001', 'id': 'other.template',
        'version': '2.0.0', 'workspaceUuid': workspace}
    context['document']['format'] = {'uuid': NIL_UUID, 'name': 'PDF'}
    warnings = fill_document(context, *template_and_format(), DocumentOptions(now=NOW))
    assert len(warnings) == 2
    assert 'other.template:2.0.0' in warnings[0] and 'test.render01:1.0.0' in warnings[0]
    assert '"PDF"' in warnings[1]
    assert context['document']['documentTemplate'] == {
        'uuid': '66666666-0000-0000-0000-000000000001', 'id': 'test.render01',
        'version': '1.0.0', 'workspaceUuid': workspace}
    assert context['document']['format'] == JSON_FORMAT


# CLI

def render(fixtures_path: pathlib.Path, *args: str, template: str = 'test_render01'):
    return click.testing.CliRunner().invoke(main, args=[
        '--no-config', '--no-dot-env', 'render', (fixtures_path / template).as_posix(), *args,
    ])


def test_render_rejects_partial_context(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    context = tmp_path / 'partial.json'
    context.write_text('{"config": {"clientUrl": ""}, "document": {"name": "Doc"}}',
                       encoding='utf-8')
    result = render(fixtures_path, '-c', str(context), '-F', 'JSON Data',
                    '-o', str(tmp_path / 'out.json'))
    assert result.exit_code == 1
    assert f'{context}: not a valid document context' in result.output
    assert '/workspace: Field required' in result.output
    assert not (tmp_path / 'out.json').exists()


def test_render_warns_about_hash(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    context = fixture_context(fixtures_path)
    context['project']['name'] = 'Edited by hand'
    path = tmp_path / 'edited.json'
    path.write_text(json.dumps(context), encoding='utf-8')
    result = render(fixtures_path, '-c', str(path), '-F', 'JSON Data',
                    '-o', str(tmp_path / 'out.json'))
    assert result.exit_code == 0, result.output
    assert 'edited.json: hash does not match the content' in result.output


def test_render_fills_document(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    output = tmp_path / 'out.json'
    result = render(fixtures_path, '-c', str(fixtures_path / 'test_render01' / 'context.json'),
                    '-F', 'JSON Data', '-o', str(output), '--final', '-l', 'de',
                    '--event', '44444444-0000-0000-0000-000000000001',
                    '--document-name', 'Final plan')
    assert result.exit_code == 0, result.output
    document = json.loads(output.read_text(encoding='utf-8'))['document']
    assert (document['name'], document['language'], document['preview'],
            document['eventUuid']) == \
        ('Final plan', 'de', False, '44444444-0000-0000-0000-000000000001')
    assert document['documentTemplate'] == TEMPLATE_DOCUMENT
    assert document['format'] == JSON_FORMAT


@pytest.mark.parametrize('target', ['', 'saved.json'])
def test_write_context(fixtures_path: pathlib.Path, tmp_path: pathlib.Path, target: str):
    output = tmp_path / 'out.json'
    args = ['--write-context'] if not target else ['--write-context', str(tmp_path / target)]
    result = render(fixtures_path, '-c', str(fixtures_path / 'test_render01' / 'context.json'),
                    '-F', 'JSON Data', '-o', str(output), *args)
    assert result.exit_code == 0, result.output
    saved = json.loads((tmp_path / (target or 'out.context.json')).read_text(encoding='utf-8'))
    rendered = json.loads(output.read_text(encoding='utf-8'))
    assert errors(saved) == []  # including the hash
    assert 'extras' not in saved
    assert set(saved['config']) == set(generate.CONFIG_KEYS)
    assert saved['document'] == rendered['document']
    assert saved['questionnaire'] == rendered['questionnaire']


def batch_input(fixtures_path: pathlib.Path, tmp_path: pathlib.Path) -> pathlib.Path:
    contexts = tmp_path / 'contexts'
    contexts.mkdir()
    valid = (fixtures_path / 'test_render01' / 'context.json').read_text(encoding='utf-8')
    (contexts / 'a.json').write_text(valid, encoding='utf-8')
    (contexts / 'b-broken.json').write_text('{"document": null}', encoding='utf-8')
    (contexts / 'c.json').write_text(valid, encoding='utf-8')
    (contexts / 'ignored.txt').write_text('not a context', encoding='utf-8')
    return contexts


def test_batch_with_broken_context(fixtures_path: pathlib.Path, tmp_path: pathlib.Path,
                                   monkeypatch):
    monkeypatch.chdir(tmp_path)
    contexts = batch_input(fixtures_path, tmp_path)
    result = render(fixtures_path, '-c', 'contexts', '-F', 'JSON Data', '-F', 'HTML Document',
                    '-o', 'out', '--write-context')
    assert result.exit_code == 1, result.output
    assert '4 of 6 documents rendered' in result.output
    out = tmp_path / 'out'
    summary = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
    assert [(e['context'], e['format'], e['status'], e['output']) for e in summary] == [
        ('contexts/a.json', 'JSON Data', 'ok', 'a.json-data.json'),
        ('contexts/a.json', 'HTML Document', 'ok', 'a.html-document.html'),
        ('contexts/b-broken.json', 'JSON Data', 'error', None),
        ('contexts/b-broken.json', 'HTML Document', 'error', None),
        ('contexts/c.json', 'JSON Data', 'ok', 'c.json-data.json'),
        ('contexts/c.json', 'HTML Document', 'ok', 'c.html-document.html'),
    ]
    assert all(isinstance(e['durationMs'], int) for e in summary)
    assert summary[0]['error'] is None
    assert 'not a valid document context' in summary[2]['error']
    assert errors(json.loads((out / 'a.json-data.context.json').read_text(encoding='utf-8'))) == []
    assert (contexts / 'a.json').read_text(encoding='utf-8') == \
        (contexts / 'c.json').read_text(encoding='utf-8')


def test_batch_all_formats_into_default_directory(fixtures_path: pathlib.Path,
                                                  tmp_path: pathlib.Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    context = fixtures_path / 'test_render02' / 'context.json'
    result = render(fixtures_path, '-c', str(context), '--all-formats',
                    template='test_render02')
    summary = json.loads((tmp_path / 'output' / 'summary.json').read_text(encoding='utf-8'))
    assert len(summary) > 1
    assert result.exit_code == (1 if any(e['status'] == 'error' for e in summary) else 0)


def test_batch_one_format_has_no_format_part(fixtures_path: pathlib.Path,
                                             tmp_path: pathlib.Path):
    contexts = batch_input(fixtures_path, tmp_path)
    (contexts / 'b-broken.json').unlink()
    result = render(fixtures_path, '-c', str(contexts), '-F', 'JSON Data',
                    '-o', str(tmp_path / 'out'))
    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in (tmp_path / 'out').iterdir()) == \
        ['a.json', 'c.json', 'summary.json']


@pytest.mark.parametrize(('args', 'message'), [
    (['-F', 'JSON Data', '--all-formats'], 'either --format or --all-formats'),
    (['-F', 'JSON Data', '-F', 'HTML Document', '--write-context', 'x.json'],
     '--write-context takes no FILE'),
])
def test_batch_usage_errors(fixtures_path: pathlib.Path, tmp_path: pathlib.Path, args, message):
    result = render(fixtures_path, '-c', str(fixtures_path / 'test_render01' / 'context.json'),
                    *args, '-o', str(tmp_path / 'out'))
    assert result.exit_code == 2
    assert message in result.output


def test_empty_context_directory(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    result = render(fixtures_path, '-c', str(tmp_path), '-F', 'JSON Data')
    assert result.exit_code == 2
    assert 'No *.json file in directory' in result.output


def test_smoke_render_every_profile(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    contexts = tmp_path / 'contexts'
    contexts.mkdir()
    for profile in PROFILES:
        for source in ('project', 'km-editor'):
            context = generate.generate_context(sample_input(1), generate.Options(
                profile=PROFILE_BY_NAME[profile], seed=1, source=source)).context
            (contexts / f'{profile}-{source}.json').write_text(generate.dumps(context),
                                                               encoding='utf-8')
    result = render(fixtures_path, '-c', str(contexts), '-F', 'JSON Data',
                    '-F', 'Project JSON', '-o', str(tmp_path / 'out'))
    assert result.exit_code == 0, result.output
    summary = json.loads((tmp_path / 'out' / 'summary.json').read_text(encoding='utf-8'))
    assert len(summary) == 2 * 2 * len(PROFILES)
    assert {e['status'] for e in summary} == {'ok'}
