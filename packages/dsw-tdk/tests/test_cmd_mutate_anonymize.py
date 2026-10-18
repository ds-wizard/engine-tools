import json
import pathlib

import click.testing
import pytest

from dsw.models.document_context.validation import validate_context
from dsw.tdk import main
from dsw.tdk.context import generate
from dsw.tdk.context.anonymize import anonymize_context
from dsw.tdk.context.inputs import sample_input
from dsw.tdk.context.mutate import mutate_context
from dsw.tdk.context.profiles import PROFILE_BY_NAME, PROFILES


def base_context(profile: str = 'full', source: str = 'project') -> dict:
    return generate.generate_context(sample_input(1), generate.Options(
        profile=PROFILE_BY_NAME[profile], seed=1, source=source)).context


def mutated(base: dict, profile: str, seed: int = 2) -> dict:
    return mutate_context(generate.input_from_context(base), generate.Options(
        profile=PROFILE_BY_NAME[profile], seed=seed)).context


def errors(context: dict) -> list[str]:
    return [str(i) for i in validate_context(context) if i.severity == 'error']


@pytest.mark.parametrize('profile', PROFILES)
@pytest.mark.parametrize('source', ['project', 'km-editor'])
def test_mutated_contexts_are_valid(profile, source):
    context = mutated(base_context('full', source), profile)
    assert errors(context) == []


def test_empty_rate_drops_every_reply():
    base = base_context('full')
    context = mutated(base, 'empty')
    assert context['questionnaire']['replies'] == {}
    admins = [u for u in context['project']['users'] if 'ADMIN' in u['perms']]
    assert admins  # the owner stays


def test_full_rate_only_adds():
    base = base_context('full')
    context = mutated(base, 'full')
    assert set(base['questionnaire']['replies']) <= set(context['questionnaire']['replies'])
    assert len(context['project']['users']) >= len(base['project']['users'])


def test_typical_rate_changes_some_but_not_all():
    base = base_context('full')
    context = mutated(base, 'typical')
    before, after = base['questionnaire']['replies'], context['questionnaire']['replies']
    changed = sum(1 for path in before if after.get(path) != before[path])
    assert 0 < changed < len(before)
    assert context['hash'] != base['hash']


def test_removed_items_take_their_replies_and_item_selects():
    context = mutated(base_context('full'), 'edge', seed=5)
    replies = context['questionnaire']['replies']
    items = {item for reply in replies.values() if reply['value']['type'] == 'ItemListReply'
             for item in reply['value']['value']}
    for reply in replies.values():
        if reply['value']['type'] == 'ItemSelectReply':
            assert reply['value']['value'] in items
    assert errors(context) == []  # item paths resolve only through listed items


def test_mutation_is_deterministic():
    base = base_context('full')
    assert generate.dumps(mutated(base, 'typical')) == generate.dumps(mutated(base, 'typical'))


def string_values(data) -> list[str]:
    if isinstance(data, str):
        return [data]
    if isinstance(data, dict):
        return [s for value in data.values() for s in string_values(value)]
    if isinstance(data, list):
        return [s for value in data for s in string_values(value)]
    return []


def personal_values(context: dict) -> set[str]:
    project = context['project']
    values = set(project['projectTags'])
    values |= {project['name']}
    for permission in project['users']:
        user = permission['user']
        values |= {user['firstName'] + user['lastName'], user['email']}
    for permission in project['groups']:
        values.add(permission['group']['name'])
    values |= {f['fileName'] for f in context['questionnaire']['files']}
    values |= {v['name'] for v in context['questionnaire']['versions']}
    return {value for value in values if value and len(value) > 3}


def test_anonymization_leaves_no_original_value():
    base = base_context('full')
    anonymized = anonymize_context(base, seed=9).context
    # the knowledge model (also in the report), config and workspace are kept on purpose
    scrubbed = {key: value for key, value in anonymized.items()
                if key not in ('knowledgeModel', 'knowledgeModelPackage', 'config', 'workspace')}
    scrubbed['questionnaire'] = {**scrubbed['questionnaire'], 'report': None}
    leaked = sorted(personal_values(base) & set(string_values(scrubbed)))
    assert leaked == []
    assert errors(anonymized) == []
    for permission in anonymized['project']['users']:
        assert permission['user']['email'].startswith('anon-')
        assert permission['user']['email'].endswith('@example.org')
        assert permission['user']['imageUrl'] is None


def test_anonymization_keeps_structure_and_is_deterministic():
    base = base_context('full')
    first = anonymize_context(base, seed=9).context
    assert generate.dumps(first) == generate.dumps(anonymize_context(base, seed=9).context)
    assert generate.dumps(first) != generate.dumps(anonymize_context(base, seed=10).context)
    assert first['knowledgeModel'] == base['knowledgeModel']
    assert first['config'] == base['config'] and first['workspace'] == base['workspace']
    assert set(first['questionnaire']['replies']) == set(base['questionnaire']['replies'])
    assert [u['user']['uuid'] for u in first['project']['users']] == \
        [u['user']['uuid'] for u in base['project']['users']]
    # the same original always gets the same placeholder
    names = {}
    for before, after in zip(base['project']['users'], first['project']['users'], strict=True):
        names.setdefault(before['user']['firstName'], set()).add(after['user']['firstName'])
    assert all(len(placeholders) == 1 for placeholders in names.values())


def test_numbers_and_dates_are_kept():
    base = base_context('full')
    anonymized = anonymize_context(base, seed=9).context
    questions = base['knowledgeModel']['entities']['questions']
    for path, reply in base['questionnaire']['replies'].items():
        question = questions[path.rsplit('.', 1)[-1]]
        if question.get('valueType') in ('NumberQuestionValueType', 'DateQuestionValueType'):
            assert anonymized['questionnaire']['replies'][path]['value'] == reply['value']
            assert anonymized['questionnaire']['replies'][path]['createdAt'] == reply['createdAt']


# CLI

def run(*args: str):
    return click.testing.CliRunner().invoke(main, args=['--no-config', 'generate-context', *args])


def test_cli_anonymize_only_gives_one_copy(tmp_path: pathlib.Path):
    base = tmp_path / 'base.json'
    base.write_text(generate.dumps(base_context('full')), encoding='utf-8')
    out = tmp_path / 'out'
    result = run('--from', str(base), '--anonymize', '--seed', '3', '-o', str(out))
    assert result.exit_code == 0, result.output
    assert [p.name for p in out.iterdir()] == ['anonymized-3-0.json']


def test_cli_mutate_then_anonymize(tmp_path: pathlib.Path):
    base = tmp_path / 'base.json'
    base.write_text(generate.dumps(base_context('full')), encoding='utf-8')
    out = tmp_path / 'out'
    result = run('--from', str(base), '--mutate', '--anonymize', '--profile', 'typical',
                 '--count', '2', '--seed', '3', '-o', str(out))
    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in out.iterdir()) == ['typical-3-0.json', 'typical-3-1.json']
    for path in out.iterdir():
        assert errors(json.loads(path.read_text(encoding='utf-8'))) == []


@pytest.mark.parametrize('flag', ['--mutate', '--anonymize'])
def test_cli_needs_from(tmp_path, flag):
    result = run('--sample', flag, '-o', str(tmp_path))
    assert result.exit_code == 2
    assert 'need --from' in result.output
