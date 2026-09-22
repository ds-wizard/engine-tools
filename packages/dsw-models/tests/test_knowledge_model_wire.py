import copy

import pydantic
import pytest
from conftest import REFERENCE_BUNDLES, assert_same_json, load_reference, load_synthetic

from dsw.models.knowledge_model import events, flat
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.strictness import UnknownKeys, load


@pytest.mark.parametrize('name', REFERENCE_BUNDLES)
def test_reference_bundle_round_trip(name):
    data = load_reference(name)
    bundle = load(KnowledgeModelBundle, data)
    assert bundle.metamodel_version == 20
    assert_same_json(data, bundle.to_json_data())


def test_flat_knowledge_model_round_trip():
    data = load_synthetic('knowledge_model.json')
    km = load(flat.KnowledgeModel, data)
    assert {type(q) for q in km.entities.questions.values()} >= {
        flat.OptionsQuestion, flat.MultiChoiceQuestion, flat.ListQuestion, flat.ValueQuestion,
        flat.IntegrationQuestion, flat.ItemSelectQuestion, flat.FileQuestion,
    }
    assert_same_json(data, km.to_json_data())


def test_flat_nullable_keys_may_be_missing():
    data = load_synthetic('knowledge_model.json')
    question = data['entities']['questions']['00000000-0000-0000-0000-000000000206']
    del question['text'], question['requiredPhaseUuid'], question['listQuestionUuid']
    km = load(flat.KnowledgeModel, data)
    dumped = km.to_json_data()['entities']['questions']['00000000-0000-0000-0000-000000000206']
    assert dumped['text'] is None
    assert dumped['listQuestionUuid'] is None


def test_flat_unknown_key_is_rejected_or_dropped():
    data = copy.deepcopy(load_synthetic('knowledge_model.json'))
    data['entities']['tags']['00000000-0000-0000-0000-000000000801']['newField'] = 1
    with pytest.raises(pydantic.ValidationError, match='Unknown keys for Tag: newField'):
        load(flat.KnowledgeModel, data)
    km = load(flat.KnowledgeModel, data, unknown_keys=UnknownKeys.IGNORE)
    assert 'newField' not in km.to_json_data()['entities']['tags']['00000000-0000-0000-0000-000000000801']


def test_synthetic_events_round_trip():
    data = load_synthetic('km_events.json')
    parsed = [load(events.Event, item) for item in data]
    assert_same_json(data, [event.to_json_data() for event in parsed])


def test_edit_event_field():
    field = events.EditEventField[str].model_validate({'changed': False})
    assert field.to_json_data() == {'changed': False}
    field = events.EditEventField[str | None].model_validate({'changed': True, 'value': None})
    assert field.to_json_data() == {'changed': True, 'value': None}
    assert events.EditEventField[int].change(3).to_json_data() == {'changed': True, 'value': 3}
    assert events.EditEventField[int].no_change().to_json_data() == {'changed': False}
    with pytest.raises(pydantic.ValidationError, match='requires a value'):
        events.EditEventField[str].model_validate({'changed': True})


def test_event_discriminates_nested_variants():
    data = load_synthetic('km_events.json')
    types = [type(load(events.Event, item).content) for item in data]
    assert types == [
        events.AddMultiChoiceQuestionEventContent,
        events.AddItemSelectQuestionEventContent,
        events.AddFileQuestionEventContent,
        events.AddPluginIntegrationEventContent,
        events.EditPluginIntegrationEventContent,
        events.MoveExpertEventContent,
        events.EditApiIntegrationEventContent,
    ]


def test_plugin_integration_event_has_no_variables():
    data = load_synthetic('km_events.json')[3]
    data['content']['variables'] = []
    with pytest.raises(pydantic.ValidationError, match='Unknown keys'):
        load(events.Event, data)
