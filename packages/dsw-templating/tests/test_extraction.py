"""Replies extraction (``ctx|extract_replies``) over the synthetic document context.

The synthetic context has one question of every type; here every question gets a key annotation
and every answer and choice a value annotation, under custom names, so that a configuration that
is not applied shows as an empty result.
"""
import copy
import json
import logging
import pathlib

import pytest

from dsw.templating.extraction import DEFAULT_CONFIG, SimpleExtractor, extract_replies
from dsw.templating.filters import to_context_obj


SYNTHETIC_CONTEXT = (pathlib.Path(__file__).parents[2] / 'dsw-models' / 'tests' / 'fixtures'
                     / 'synthetic' / 'document_context.json')
CHAPTER = '00000000-0000-0000-0000-000000000101'
OPTIONS = '00000000-0000-0000-0000-000000000201'
MULTI_CHOICE = '00000000-0000-0000-0000-000000000202'
LIST = '00000000-0000-0000-0000-000000000203'
ITEM_VALUE = '00000000-0000-0000-0000-000000000204'
FOLLOWUP = '00000000-0000-0000-0000-000000000208'
ANSWER_YES = '00000000-0000-0000-0000-000000000301'
ANSWER_NO = '00000000-0000-0000-0000-000000000302'
CHOICE = '00000000-0000-0000-0000-000000000601'
ITEM_1 = '50000000-0000-0000-0000-000000000001'
FILE = '60000000-0000-0000-0000-000000000001'
CUSTOM = {'annotations': {'key': 'my.key', 'value': 'my.value'}}
V2 = {'version': '2'}


def annotated_context(key: str, value: str) -> dict:
    ctx = json.loads(SYNTHETIC_CONTEXT.read_text(encoding='utf-8'))
    entities = ctx['knowledgeModel']['entities']
    for question in entities['questions'].values():
        question['annotations'].append({'key': key, 'value': question['questionType']})
    for entity in [*entities['answers'].values(), *entities['choices'].values()]:
        entity['annotations'].append({'key': value, 'value': 'code'})
    ctx['questionnaire']['replies'][f'{CHAPTER}.{MULTI_CHOICE}'] = {
        'value': {'type': 'MultiChoiceReply', 'value': [CHOICE]},
        'createdBy': None, 'createdAt': '2026-09-15T10:00:00Z',
    }
    return ctx


def set_value(ctx: dict, kind: str, uuid: str, annotation: str, value: str):
    for item in ctx['knowledgeModel']['entities'][kind][uuid]['annotations']:
        if item['key'] == annotation:
            item['value'] = value


@pytest.fixture(scope='module')
def custom_dc():
    return to_context_obj(annotated_context('my.key', 'my.value'))


@pytest.fixture(scope='module')
def default_dc():
    return to_context_obj(annotated_context('json.key', 'json.value'))


@pytest.fixture(scope='module')
def no_selected_dc():
    """The options question answered "No": the reply under "Yes"'s follow-up is stale."""
    ctx = annotated_context('json.key', 'json.value')
    ctx['questionnaire']['replies'][f'{CHAPTER}.{OPTIONS}']['value']['value'] = ANSWER_NO
    return to_context_obj(ctx)


@pytest.fixture(scope='module')
def unanswered_dc():
    ctx = annotated_context('json.key', 'json.value')
    del ctx['questionnaire']['replies'][f'{CHAPTER}.{OPTIONS}']
    return to_context_obj(ctx)


def test_custom_annotations_are_used(custom_dc):
    result = extract_replies(custom_dc, copy.deepcopy(CUSTOM))
    assert result['OptionsQuestion']['_value'] == 'code'
    assert result['OptionsQuestion']['ValueQuestion']['_value'] == '42'
    assert result['MultiChoiceQuestion'][0]['_value'] == 'code'
    assert [item['ValueQuestion']['_value'] for item in result['ListQuestion']] == \
        ['first item', 'second item']


def test_partial_config_keeps_other_defaults(default_dc):
    result = extract_replies(default_dc, {'options': {'include_reply_objects': True}})
    assert result['OptionsQuestion']['_value'] == 'code'  # default json.key / json.value
    assert '_reply' in result['IntegrationQuestion']


def test_config_and_defaults_are_not_modified(custom_dc):
    config = copy.deepcopy(CUSTOM)
    defaults = copy.deepcopy(DEFAULT_CONFIG)
    extract_replies(custom_dc, config)
    extract_replies(custom_dc)
    assert config == CUSTOM
    assert DEFAULT_CONFIG == defaults


def test_unknown_extractor_is_rejected(default_dc):
    with pytest.raises(ValueError, match='simple:3'):
        extract_replies(default_dc, {'version': '3'})


def test_reply_objects_on_every_question_type(default_dc):
    config = copy.deepcopy(DEFAULT_CONFIG)
    config['options']['include_reply_objects'] = True
    result = SimpleExtractor(default_dc, config).extract()
    for key in ('OptionsQuestion', 'IntegrationQuestion', 'ItemSelectQuestion', 'FileQuestion'):
        assert '_reply' in result[key], key
    assert '_reply' in result['OptionsQuestion']['ValueQuestion']
    # a list cannot carry the reply, so each choice and each item does
    choices = result['MultiChoiceQuestion']
    assert [choice['_uuid'] for choice in choices] == [CHOICE]
    assert all(choice['_reply'].choices[0].uuid == CHOICE for choice in choices)
    items = result['ListQuestion']
    assert len(items) == 2
    assert all(item['_reply'].items == [item['_uuid'] for item in items] for item in items)


# simple:1 keeps its shapes; it only warns


def test_v1_unanswered_and_unselected_stay_absent(unanswered_dc, no_selected_dc):
    assert extract_replies(unanswered_dc)['OptionsQuestion'] is None
    assert 'ValueQuestion' not in extract_replies(no_selected_dc)['OptionsQuestion']


def test_v1_values_are_converted_loosely():
    ctx = annotated_context('json.key', 'json.value')
    set_value(ctx, 'answers', ANSWER_YES, 'json.value', '007')
    result = extract_replies(to_context_obj(ctx))
    assert result['OptionsQuestion']['_value'] == 7
    assert result['OptionsQuestion']['ValueQuestion']['_value'] == '42'


def test_duplicate_key_is_reported(caplog):
    ctx = annotated_context('json.key', 'json.value')
    entities = ctx['knowledgeModel']['entities']
    for question in entities['questions'].values():
        if question['questionType'] == 'FileQuestion':
            question['annotations'][-1]['value'] = 'IntegrationQuestion'
    with caplog.at_level(logging.WARNING, logger='dsw.templating.extraction'):
        result = extract_replies(to_context_obj(ctx))
    assert result['IntegrationQuestion']['_name'] == 'agreement.pdf'  # the later one wins
    assert ['"IntegrationQuestion" is written twice' in m for m in caplog.messages] == [True]


@pytest.mark.parametrize('config', [None, V2])
def test_list_without_key_is_reported_once(caplog, config):
    ctx = annotated_context('json.key', 'json.value')
    ctx['knowledgeModel']['entities']['questions'][LIST]['annotations'].pop()
    with caplog.at_level(logging.WARNING, logger='dsw.templating.extraction'):
        result = extract_replies(to_context_obj(ctx), config)
        extract_replies(to_context_obj(ctx), config)
    assert 'ListQuestion' not in result
    assert len(caplog.messages) == 2  # once per extraction
    assert f'list question {LIST} has no "json.key" annotation' in caplog.messages[0]


def test_unannotated_list_without_annotated_items_is_not_reported(caplog):
    ctx = annotated_context('json.key', 'json.value')
    questions = ctx['knowledgeModel']['entities']['questions']
    questions[LIST]['annotations'].pop()
    questions[ITEM_VALUE]['annotations'].pop()
    with caplog.at_level(logging.WARNING, logger='dsw.templating.extraction'):
        extract_replies(to_context_obj(ctx))
    assert caplog.messages == []


# simple:2


def test_v2_unanswered_options_question_is_complete(unanswered_dc):
    result = extract_replies(unanswered_dc, V2)
    assert result['OptionsQuestion'] == {
        '_uuid': None, '_label': None, '_value': None, '_path': f'{CHAPTER}.{OPTIONS}',
        'ValueQuestion': {'_value': None, '_path': f'{CHAPTER}.{OPTIONS}.{ANSWER_YES}.{FOLLOWUP}'},
    }


def test_v2_followups_of_unselected_answers_are_empty(no_selected_dc):
    options = extract_replies(no_selected_dc, V2)['OptionsQuestion']
    assert options['_uuid'] == ANSWER_NO
    # the stale reply under "Yes" is not used
    assert options['ValueQuestion']['_value'] is None


def test_v2_selected_answer_keeps_its_replies(default_dc):
    options = extract_replies(default_dc, V2)['OptionsQuestion']
    assert options['_uuid'] == ANSWER_YES
    assert options['ValueQuestion']['_value'] == 42  # a number question


def test_v2_every_object_has_a_value(default_dc):
    result = extract_replies(default_dc, V2)
    assert result['ItemSelectQuestion']['_value'] == ITEM_1
    assert result['FileQuestion']['_value'] == FILE
    item = result['ListQuestion'][0]
    assert item['_value'] == item['_uuid'] == ITEM_1
    assert item['_label'] == 'first item'
    assert item['_path'] == f'{CHAPTER}.{LIST}.{ITEM_1}'


@pytest.mark.parametrize(('annotation', 'value'), [
    ('true', True), ('false', False), ('12', 12), ('-3', -3), ('0', 0),
    ('007', '007'), ('1e3', '1e3'), ('nan', 'nan'), ('1_000', '1_000'), (' 7 ', ' 7 '),
    ('True', 'True'), ('yes', 'yes'), ('1.5', '1.5'),
])
def test_v2_values_are_converted_strictly(annotation, value):
    ctx = annotated_context('json.key', 'json.value')
    set_value(ctx, 'answers', ANSWER_YES, 'json.value', annotation)
    set_value(ctx, 'choices', CHOICE, 'json.value', annotation)
    result = extract_replies(to_context_obj(ctx), V2)
    assert result['OptionsQuestion']['_value'] == value
    assert type(result['OptionsQuestion']['_value']) is type(value)
    assert result['MultiChoiceQuestion'][0]['_value'] == value


def test_v2_reply_objects(default_dc):
    result = extract_replies(default_dc, {'version': '2', 'options': {'include_reply_objects': True}})
    assert '_reply' in result['ListQuestion'][0]
    assert '_reply' in result['MultiChoiceQuestion'][0]
