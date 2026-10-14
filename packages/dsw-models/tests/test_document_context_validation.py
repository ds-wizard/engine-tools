"""validate_context: one broken context per error (WEP 24, `dsw-tdk validate-context`)."""
import copy

import pytest
from conftest import load_synthetic

from dsw.models.document_context.hash import compute_context_hash
from dsw.models.document_context.validation import pointer, validate_context


CH = '00000000-0000-0000-0000-000000000101'
OPTIONS = f'{CH}.00000000-0000-0000-0000-000000000201'
FOLLOW_UP = f'{OPTIONS}.00000000-0000-0000-0000-000000000301.00000000-0000-0000-0000-000000000208'
MULTI = f'{CH}.00000000-0000-0000-0000-000000000202'
LIST = f'{CH}.00000000-0000-0000-0000-000000000203'
ITEM_SELECT = f'{CH}.00000000-0000-0000-0000-000000000206'
FILE = f'{CH}.00000000-0000-0000-0000-000000000207'
INTEGRATION = f'{CH}.00000000-0000-0000-0000-000000000205'
UNKNOWN = '99999999-9999-9999-9999-999999999999'


def context(change=None, name='document_context.json') -> dict:
    ctx = copy.deepcopy(load_synthetic(name))
    if change is not None:
        change(ctx)
    ctx['hash'] = compute_context_hash(ctx)
    return ctx


def errors(ctx: dict) -> list[str]:
    return [f'{issue.path}: {issue.message}' for issue in validate_context(ctx)
            if issue.severity == 'error']


def reply(value: dict) -> dict:
    return {'value': value, 'createdBy': None, 'createdAt': '2026-09-14T10:00:00Z'}


@pytest.mark.parametrize('name', ['document_context.json', 'document_context_km_editor.json'])
def test_synthetic_contexts_are_valid(name):
    assert errors(context(name=name)) == []


def test_schema_errors_stop_the_other_checks():
    ctx = context(lambda c: c['questionnaire'].pop('replies'))
    assert errors(ctx) == ['/questionnaire/replies: Field required']


def test_exactly_one_source():
    found = errors(context(lambda c: c.update(project=None)))
    assert len(found) == 1
    assert 'Exactly one of project and knowledgeModelEditor' in found[0]


def test_metamodel_version():
    assert errors(context(lambda c: c.update(metamodelVersion='18.3'))) == [
        '/metamodelVersion: 18.3 is not 19.x']


def test_hash():
    ctx = context()
    ctx['hash'] = 'sha256:0'
    found = errors(ctx)
    assert len(found) == 1
    assert found[0].startswith('/hash: does not match the content, which gives sha256:')


def put_reply(path, value):
    return lambda c: c['questionnaire']['replies'].__setitem__(path, reply(value))


@pytest.mark.parametrize(('change', 'path', 'message'), [
    (put_reply(f'{UNKNOWN}.00000000-0000-0000-0000-000000000201', {'type': 'StringReply', 'value': 'x'}),
     f'{UNKNOWN}.00000000-0000-0000-0000-000000000201', f'chapter {UNKNOWN} is not in the knowledge model'),
    (put_reply(f'{CH}.{UNKNOWN}', {'type': 'StringReply', 'value': 'x'}),
     f'{CH}.{UNKNOWN}', f'question {UNKNOWN} is not in chapter {CH}'),
    (put_reply(f'{OPTIONS}.{UNKNOWN}.00000000-0000-0000-0000-000000000208', {'type': 'StringReply', 'value': 'x'}),
     f'{OPTIONS}.{UNKNOWN}.00000000-0000-0000-0000-000000000208', f'{UNKNOWN} is not an answer'),
    (put_reply(f'{LIST}.{UNKNOWN}.00000000-0000-0000-0000-000000000204', {'type': 'StringReply', 'value': 'x'}),
     f'{LIST}.{UNKNOWN}.00000000-0000-0000-0000-000000000204', f'{UNKNOWN} is not an item of the list'),
    (put_reply(f'{INTEGRATION}.{UNKNOWN}.{UNKNOWN}', {'type': 'StringReply', 'value': 'x'}),
     f'{INTEGRATION}.{UNKNOWN}.{UNKNOWN}', 'has no follow-up or item questions'),
    (put_reply('not-a-path', {'type': 'StringReply', 'value': 'x'}),
     'not-a-path', 'is not a path of UUIDs'),
])
def test_reply_paths_resolve(change, path, message):
    found = errors(context(change))
    assert len(found) == 1, found
    assert found[0].startswith(pointer('questionnaire', 'replies', path))
    assert message in found[0]


def test_reply_below_an_unchosen_answer_is_fine():
    # the backend keeps the follow-up replies when another answer is chosen
    def choose_other_answer(c):
        c['questionnaire']['replies'][OPTIONS]['value']['value'] = '00000000-0000-0000-0000-000000000302'
    ctx = context(choose_other_answer)
    assert FOLLOW_UP in ctx['questionnaire']['replies']
    assert errors(ctx) == []


@pytest.mark.parametrize(('path', 'value', 'message'), [
    (OPTIONS, {'type': 'StringReply', 'value': 'x'}, 'a StringReply cannot answer the OptionsQuestion'),
    (OPTIONS, {'type': 'AnswerReply', 'value': UNKNOWN}, f'{UNKNOWN} is not an answer of'),
    (MULTI, {'type': 'MultiChoiceReply', 'value': [UNKNOWN]}, f'{UNKNOWN} is not a choice of'),
    (FILE, {'type': 'FileReply', 'value': UNKNOWN}, f'file {UNKNOWN} is not in questionnaire.files'),
    (ITEM_SELECT, {'type': 'ItemSelectReply', 'value': UNKNOWN}, f'{UNKNOWN} is not an item of the list'),
])
def test_reply_values(path, value, message):
    found = errors(context(put_reply(path, value)))
    assert len(found) == 1, found
    assert message in found[0]


def test_labels_phase_and_version():
    def change(c):
        c['questionnaire']['labels'][f'{CH}.{UNKNOWN}'] = []
        c['questionnaire']['phaseUuid'] = UNKNOWN
        c['questionnaire']['versionUuid'] = UNKNOWN
    found = errors(context(change))
    assert [f.split(':')[0] for f in found] == [
        pointer('questionnaire', 'labels', f'{CH}.{UNKNOWN}'),
        '/questionnaire/phaseUuid', '/questionnaire/versionUuid']


def test_warnings_sort_order_and_required_questions():
    def change(c):
        files = c['questionnaire']['files']
        files.append({**files[0], 'uuid': '00000000-0000-0000-0000-000000000000'})
        del c['questionnaire']['replies'][OPTIONS]
    issues = validate_context(context(change))
    assert all(issue.severity == 'warning' for issue in issues)
    messages = {issue.path: issue.message for issue in issues}
    assert messages['/questionnaire/files'] == 'is not sorted by UUID'
    assert 'is required now and unanswered' in messages[pointer('questionnaire', 'replies', OPTIONS)]


def test_pointer_escapes():
    assert pointer('a/b', 'c~d', 0) == '/a~1b/c~0d/0'
