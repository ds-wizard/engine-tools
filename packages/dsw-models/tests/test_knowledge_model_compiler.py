import collections
from datetime import UTC, datetime
from uuid import UUID

import pytest
from conftest import REFERENCE_BUNDLES, load_reference

from dsw.models.common import KeyValue
from dsw.models.knowledge_model import events as ev
from dsw.models.knowledge_model import flat, graph
from dsw.models.knowledge_model.bundle import (
    PackageChainError,
    compile_bundle,
    events_of_chain,
    package_chain,
)
from dsw.models.knowledge_model.compiler import compile_events
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.strictness import load


KM = UUID(int=1)
_counter = iter(range(1000, 1_000_000))


def u(n: int) -> UUID:
    return UUID(int=n)


def event(content, entity: int, parent: int = 1) -> ev.Event:
    return ev.Event(uuid=u(next(_counter)), parent_uuid=u(parent), entity_uuid=u(entity),
                    content=content, created_at=datetime(2026, 1, 1, tzinfo=UTC))


def unchanged(content_type, **changes):
    data = {}
    for name, field in content_type.model_fields.items():
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, ev.EditEventField):
            data[name] = annotation.change(changes[name]) if name in changes else annotation.no_change()
    return content_type(**data)


def base_events():
    return [
        event(ev.AddKnowledgeModelEventContent(annotations=[]), 1, 0),
        event(ev.AddChapterEventContent(title='Chapter', annotations=[]), 10),
        event(ev.AddTagEventContent(name='Tag', color='#000', annotations=[]), 20),
        event(ev.AddTagEventContent(name='Tag 2', color='#000', annotations=[]), 21),
        event(ev.AddOptionsQuestionEventContent(title='Q', annotations=[], tag_uuids=[u(20), u(21)]), 30, 10),
        event(ev.AddAnswerEventContent(label='Yes', annotations=[], metric_measures=[]), 40, 30),
        event(ev.AddListQuestionEventContent(title='List', annotations=[], tag_uuids=[u(20)]), 31, 10),
    ]


def compile_with_ignored(events):
    ignored = []
    km = compile_events(events, on_ignored=lambda e, reason: ignored.append((e.entity_uuid, reason)))
    return km, ignored


def test_basic_structure():
    km, ignored = compile_with_ignored(base_events())
    assert ignored == []
    assert km.uuid == KM
    assert km.chapter_uuids == [u(10)]
    assert km.entities.chapters[u(10)].question_uuids == [u(30), u(31)]
    assert km.entities.questions[u(30)].answer_uuids == [u(40)]


def test_add_question_with_missing_parent_is_stored_unlinked():
    km, ignored = compile_with_ignored([
        *base_events(),
        event(ev.AddValueQuestionEventContent(title='V', annotations=[], tag_uuids=[],
                                             value_type='StringQuestionValueType', validations=[]), 32, 99),
    ])
    assert u(32) in km.entities.questions
    assert ignored == [(u(32), 'parent not found, question stored unlinked')]


def test_add_question_under_non_list_question_is_stored_unlinked_silently():
    km, ignored = compile_with_ignored([
        *base_events(),
        event(ev.AddListQuestionEventContent(title='Item', annotations=[], tag_uuids=[]), 32, 30),
        event(ev.AddListQuestionEventContent(title='Item', annotations=[], tag_uuids=[]), 33, 31),
    ])
    assert ignored == []
    assert u(32) in km.entities.questions
    assert km.entities.questions[u(31)].item_template_question_uuids == [u(33)]
    km_graph = graph.KnowledgeModel(km)
    assert km_graph.unreachable == [km_graph[u(32)]]


def test_add_answer_with_missing_parent_is_dropped():
    km, ignored = compile_with_ignored([
        *base_events(),
        event(ev.AddAnswerEventContent(label='No', annotations=[], metric_measures=[]), 41, 99),
    ])
    assert u(41) not in km.entities.answers
    assert ignored == [(u(41), 'parent not found')]


def test_edit_with_type_change_converts_question():
    km, _ = compile_with_ignored([
        *base_events(),
        event(unchanged(ev.EditValueQuestionEventContent, title='Now value'), 30, 10),
    ])
    question = km.entities.questions[u(30)]
    assert isinstance(question, flat.ValueQuestion)
    assert question.title == 'Now value'
    assert question.tag_uuids == [u(20), u(21)]
    assert question.value_type == 'StringQuestionValueType'
    assert u(40) in km.entities.answers  # the answer stays, unreachable


def test_edit_missing_entity_is_ignored():
    _, ignored = compile_with_ignored([
        *base_events(),
        event(unchanged(ev.EditChapterEventContent, title='X'), 99),
    ])
    assert ignored == [(u(99), 'entity not found')]


def test_delete_tag_removes_first_occurrence_only():
    events = base_events()
    events.append(event(unchanged(ev.EditOptionsQuestionEventContent,
                                  tag_uuids=[u(20), u(21), u(20)]), 30, 10))
    events.append(event(ev.DeleteTagEventContent(), 20))
    km, _ = compile_with_ignored(events)
    assert km.tag_uuids == [u(21)]
    assert km.entities.questions[u(30)].tag_uuids == [u(21), u(20)]
    assert km.entities.questions[u(31)].tag_uuids == []


def test_delete_question_cascades_but_keeps_choices():
    km, _ = compile_with_ignored([
        *base_events(),
        event(ev.AddMultiChoiceQuestionEventContent(title='M', annotations=[], tag_uuids=[]), 32, 10),
        event(ev.AddChoiceEventContent(label='C', annotations=[]), 50, 32),
        event(ev.AddValueQuestionEventContent(title='F', annotations=[], tag_uuids=[],
                                             value_type='StringQuestionValueType', validations=[]), 33, 40),
        event(ev.DeleteQuestionEventContent(), 32, 10),
        event(ev.DeleteQuestionEventContent(), 30, 10),
    ])
    assert set(km.entities.questions) == {u(31)}
    assert km.entities.answers == {}
    assert set(km.entities.choices) == {u(50)}
    assert km.entities.chapters[u(10)].question_uuids == [u(31)]


def test_move_question():
    km, ignored = compile_with_ignored([
        *base_events(),
        event(unchanged(ev.EditChapterEventContent, question_uuids=[u(30), u(31), u(30)]), 10),
        event(ev.MoveQuestionEventContent(target_uuid=u(31)), 30, 10),
    ])
    assert ignored == []
    assert km.entities.chapters[u(10)].question_uuids == [u(31)]
    assert km.entities.questions[u(31)].item_template_question_uuids == [u(30)]


def test_integration_variables_and_delete():
    api = ev.AddApiIntegrationEventContent(
        name='API', variables=['a'], allow_custom_reply=True, request_method='GET', request_url='',
        request_headers=[], request_allow_empty_search=True, response_item_template='',
        test_q='', test_variables={}, annotations=[])
    km, _ = compile_with_ignored([
        *base_events(),
        event(api, 60),
        event(ev.AddIntegrationQuestionEventContent(title='I', annotations=[], tag_uuids=[],
                                                   integration_uuid=u(60), variables={'a': 'x'}), 34, 10),
        event(unchanged(ev.EditApiIntegrationEventContent, variables=['a', 'b']), 60),
    ])
    assert km.entities.questions[u(34)].variables == {'a': 'x', 'b': ''}
    km = compile_events([event(ev.DeleteIntegrationEventContent(), 60)], km)
    question = km.entities.questions[u(34)]
    assert isinstance(question, flat.ValueQuestion)
    assert question.title == 'I'


def test_integration_type_change_resets_fields():
    plugin = ev.AddPluginIntegrationEventContent(
        name='Plugin', plugin_uuid=u(7), plugin_integration_id='ror',
        plugin_integration_settings={'a': 1}, annotations=[KeyValue(key='k', value='v')])
    km, _ = compile_with_ignored([
        *base_events(),
        event(plugin, 60),
        event(unchanged(ev.EditApiIntegrationEventContent, request_url='https://x'), 60),
    ])
    integration = km.entities.integrations[u(60)]
    assert isinstance(integration, flat.ApiIntegration)
    assert (integration.name, integration.request_method, integration.request_url) == ('', 'GET', 'https://x')
    assert integration.annotations == [KeyValue(key='k', value='v')]


def test_delete_resource_collection_deletes_pages():
    km, _ = compile_with_ignored([
        *base_events(),
        event(ev.AddResourceCollectionEventContent(title='RC', annotations=[]), 70),
        event(ev.AddResourcePageEventContent(title='P', content='', annotations=[]), 71, 70),
        event(ev.DeleteResourceCollectionEventContent(), 70),
    ])
    assert km.entities.resource_pages == {}
    assert km.resource_collection_uuids == []


def test_compile_does_not_mutate_base():
    base, _ = compile_with_ignored(base_events())
    snapshot = base.model_copy(deep=True)
    compile_events([event(ev.DeleteChapterEventContent(), 10)], base)
    assert base == snapshot


REFERENCE_COUNTS = {
    'dmp.eosc.cz_czech-nrp-km_1.0.2.km.gz': (1469, 2, 105),
    'dsw_root_2.8.1.km.gz': (2010, 20, 113),
    'dsw_smp_1.2.4.km.gz': (412, 0, 53),
}


@pytest.mark.parametrize('name', REFERENCE_BUNDLES)
def test_reference_bundles_compile(name):
    bundle = load(KnowledgeModelBundle, load_reference(name))
    ignored = collections.Counter()
    km = compile_bundle(bundle, on_ignored=lambda e, reason: ignored.update([reason]))
    km_graph = graph.KnowledgeModel(km)
    entities, expected_ignored, unreachable = REFERENCE_COUNTS[name]
    assert len(km_graph) == entities
    assert sum(ignored.values()) == expected_ignored
    assert len(km_graph.unreachable) == unreachable
    assert km_graph.dangling == []


def test_package_chain():
    bundle = load(KnowledgeModelBundle, load_reference('dsw_smp_1.2.4.km.gz'))
    chain = package_chain(bundle)
    assert [p.id for p in chain][-2:] == ['dsw:smp:1.2.3', 'dsw:smp:1.2.4']
    assert package_chain(bundle, 'dsw:smp:1.1.0')[-1].id == 'dsw:smp:1.1.0'
    assert len(events_of_chain(bundle)) == sum(len(p.events) for p in bundle.packages)
    bundle.packages = bundle.packages[1:]
    with pytest.raises(PackageChainError, match='not in the bundle'):
        package_chain(bundle)
