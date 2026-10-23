"""Replies extraction (``ctx|extract_replies``) over the synthetic document context.

The synthetic context has one question of every type; here every question gets a key annotation
and every answer and choice a value annotation, under custom names, so that a configuration that
is not applied shows as an empty result.
"""
import copy
import json
import pathlib

import pytest

from dsw.templating.extraction import DEFAULT_CONFIG, SimpleExtractor, extract_replies
from dsw.templating.filters import to_context_obj


SYNTHETIC_CONTEXT = (pathlib.Path(__file__).parents[2] / 'dsw-models' / 'tests' / 'fixtures'
                     / 'synthetic' / 'document_context.json')
CHAPTER = '00000000-0000-0000-0000-000000000101'
MULTI_CHOICE = '00000000-0000-0000-0000-000000000202'
CHOICE = '00000000-0000-0000-0000-000000000601'
CUSTOM = {'annotations': {'key': 'my.key', 'value': 'my.value'}}


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


@pytest.fixture(scope='module')
def custom_dc():
    return to_context_obj(annotated_context('my.key', 'my.value'))


@pytest.fixture(scope='module')
def default_dc():
    return to_context_obj(annotated_context('json.key', 'json.value'))


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
    with pytest.raises(ValueError, match='simple:2'):
        extract_replies(default_dc, {'version': '2'})


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
