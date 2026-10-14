import datetime
import json
import pathlib

import click.testing
import pytest

from dsw.models.document_context.validation import validate_context
from dsw.tdk import main
from dsw.tdk.context import generate
from dsw.tdk.context.inputs import sample_input
from dsw.tdk.context.profiles import PERMISSION_SETS, PROFILE_BY_NAME, PROFILES
from dsw.tdk.context.sample_km import SAMPLE_KM_PATH, render_sample_km


SOURCES = ('project', 'km-editor')


def make(profile: str, variant: int = 0, source: str = 'project', seed: int = 1, **options):
    return generate.generate_context(sample_input(seed), generate.Options(
        profile=PROFILE_BY_NAME[profile], variant=variant, seed=seed, source=source, **options))


def replies_of(context: dict, title: str) -> list:
    questions = context['knowledgeModel']['entities']['questions']
    uuids = {uuid for uuid, question in questions.items() if question['title'] == title}
    return [reply['value'] for path, reply in context['questionnaire']['replies'].items()
            if path.rsplit('.', 1)[-1] in uuids]


def test_sample_km_file_is_in_sync_with_its_builder():
    # regenerate with: python -m dsw.tdk.context.sample_km
    assert SAMPLE_KM_PATH.read_text(encoding='utf-8') == render_sample_km()


@pytest.mark.parametrize('source', SOURCES)
@pytest.mark.parametrize('profile', PROFILES)
@pytest.mark.parametrize('variant', [0, 1])
def test_every_generated_context_is_valid(profile, source, variant):
    context = make(profile, variant, source).context
    assert [str(i) for i in validate_context(context) if i.severity == 'error'] == []
    assert context['document'] is None
    assert (context['project'] is None) == (source == 'km-editor')


def test_same_seed_same_bytes_other_seed_other_bytes():
    first = generate.dumps(make('typical', seed=7).context)
    assert first == generate.dumps(make('typical', seed=7).context)
    assert first != generate.dumps(make('typical', seed=8).context)
    assert first.endswith('}\n')


def test_profile_facts():
    empty = make('empty').context
    assert empty['questionnaire']['replies'] == {}
    assert len(empty['project']['users']) == 1
    assert empty['project']['users'][0]['perms'] == list(PERMISSION_SETS[-1])

    minimal = make('minimal').context
    datasets = replies_of(minimal, 'Datasets you will produce')
    assert [len(value['value']) for value in datasets] == [1]
    assert replies_of(minimal, 'Name') == []  # item questions stay unanswered
    assert minimal['questionnaire']['phaseUuid'] == minimal['knowledgeModel']['phaseUuids'][0]

    full = make('full').context
    assert (len(full['project']['users']), len(full['project']['groups']),
            len(full['questionnaire']['versions'])) == (10, 3, 5)
    assert full['questionnaire']['phaseUuid'] == full['knowledgeModel']['phaseUuids'][-1]
    topics = replies_of(full, 'Which topics does the project cover?')[0]['value']
    assert len(topics) == 4


@pytest.mark.parametrize('variant', [0, 1, 2, 3])
def test_edge_profile_round_robin(variant):
    context = make('edge', variant).context
    project = context['project']
    assert len(project['users']) == 50
    assert {tuple(p['perms']) for p in project['users']} == {tuple(s) for s in PERMISSION_SETS}
    assert project['visibility'] == generate.VISIBILITIES[variant % 4]
    assert project['sharing'] == generate.SHARING_MODES[variant % 4]
    assert (project['createdBy'] is None) == (variant % 2 == 1)
    topics = replies_of(context, 'Which topics does the project cover?')[0]['value']
    assert len(topics) == (4 if variant % 2 else 0)
    phases = [None, *context['knowledgeModel']['phaseUuids']]
    assert context['questionnaire']['phaseUuid'] == phases[variant % len(phases)]


def test_km_editor_context():
    context = make('full', source='km-editor').context
    editor = context['knowledgeModelEditor']
    assert (editor['id'], editor['previousPackageId']) == ('tdk.sample', 'tdk.sample')
    questionnaire = context['questionnaire']
    assert (questionnaire['labels'], questionnaire['versions'], questionnaire['files'],
            questionnaire['phaseUuid']) == ({}, [], [], None)


@pytest.mark.parametrize('profile', ['typical', 'full', 'edge'])
def test_values_satisfy_their_validations(profile):
    context = make(profile, seed=3).context
    for value in replies_of(context, 'Acronym'):
        assert 2 <= len(value['value']) <= 12
    for value in replies_of(context, 'Budget in EUR'):
        assert 0 <= float(value['value']) <= 1_000_000
    for value in replies_of(context, 'Start date'):
        assert '2025-01-01' <= value['value'] <= '2030-12-31'
    for value in replies_of(context, 'Daily stand-up'):
        assert '08:00' <= value['value'] <= '12:00'
    for value in replies_of(context, 'Project website'):
        assert value['value'].startswith('https://example.org/')
    for value in replies_of(context, 'Grant number'):
        assert value['value'].isdigit() and 6 <= len(value['value']) <= 9
    files = {f['uuid']: f for f in context['questionnaire']['files']}
    for value in replies_of(context, 'Consent form'):
        assert files[value['value']]['contentType'] == 'application/pdf'
        assert files[value['value']]['fileSize'] <= 1_000_000


def test_edge_uses_exact_boundaries():
    budgets = {value['value'] for n in range(6)
               for value in replies_of(make('edge', n).context, 'Budget in EUR')}
    assert budgets <= {'0', '1000000'}


def test_unsatisfiable_regex_is_left_unanswered_with_a_warning():
    generated = make('full')
    assert replies_of(generated.context, 'Unsatisfiable code') == []
    assert any('regex' in warning for warning in generated.warnings)


def test_config_and_timestamps():
    context = make('typical', config={'appTitle': 'Mine'},
                   now=datetime.datetime(2030, 6, 1, tzinfo=datetime.UTC)).context
    assert set(context['config']) == set(generate.CONFIG_KEYS)
    assert context['config']['appTitle'] == 'Mine'
    assert context['project']['updatedAt'].startswith('2030-05-31')


# CLI

def run(*args: str):
    return click.testing.CliRunner().invoke(main, args=['--no-config', 'generate-context', *args])


def test_cli_writes_one_file_per_profile_and_variant(tmp_path: pathlib.Path):
    result = run('--sample', '--profile', 'minimal', '--profile', 'edge', '--count', '2',
                 '--seed', '5', '-o', str(tmp_path))
    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        'edge-5-0.json', 'edge-5-1.json', 'minimal-5-0.json', 'minimal-5-1.json']


def test_cli_single_file_and_from(tmp_path: pathlib.Path):
    base = tmp_path / 'base.json'
    assert run('--sample', '--seed', '5', '-o', str(base)).exit_code == 0
    result = run('--from', str(base), '--profile', 'full', '--seed', '6',
                 '-o', str(tmp_path / 'full.json'))
    assert result.exit_code == 0, result.output
    generated = json.loads((tmp_path / 'full.json').read_text())
    original = json.loads(base.read_text())
    for key in ('knowledgeModel', 'knowledgeModelPackage', 'config', 'workspace'):
        assert generated[key] == original[key]


@pytest.mark.parametrize(('args', 'message'), [
    ([], 'exactly one of'),
    (['--sample', '--km-package', 'x'], 'exactly one of'),
    (['--sample', '-D', 'illustrationsColor=#fff'], 'clientUrl, appTitle, primaryColor, logoUrl'),
])
def test_cli_usage_errors(tmp_path, args, message):
    result = run(*args, '-o', str(tmp_path))
    assert result.exit_code == 2
    assert message in result.output


def test_cli_without_seed_prints_it(tmp_path: pathlib.Path):
    result = run('--sample', '-o', str(tmp_path))
    assert result.exit_code == 0
    assert 'No --seed given, using' in result.output
