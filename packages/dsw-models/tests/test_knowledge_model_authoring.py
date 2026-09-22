from uuid import UUID

import pytest
from conftest import assert_same_json, load_reference, load_synthetic
from strategies import deterministic_uuids
from test_knowledge_model_transformations import clock

from dsw.models.knowledge_model import common, flat, graph
from dsw.models.knowledge_model.builder import KnowledgeModelBuilder
from dsw.models.knowledge_model.bundle import compile_bundle
from dsw.models.knowledge_model.compiler import compile_events
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.knowledge_model.validation import validate
from dsw.models.strictness import load


def u(suffix: str) -> UUID:
    return UUID(f'00000000-0000-0000-0000-{suffix.rjust(12, "0")}')


def build_synthetic() -> KnowledgeModelBuilder:
    """The synthetic fixture knowledge model, written with the builder."""
    b = KnowledgeModelBuilder(uuid=u('1'), annotations={'km': 'synthetic'})
    chapter = b.chapter('Chapter', uuid=u('101'))
    tag = b.tag('Tag', uuid=u('801'))
    api = b.api_integration(
        'API', uuid=u('701'), variables=['domain'], request_url='https://api.example.org/search?q={{ q }}',
        request_headers={'Authorization': '{{ secrets.apiKey }}'}, response_list_field='items',
        response_item_template='{{ item.name }}', request_allow_empty_search=False)
    b.km.entities.integrations[u('701')].test_q = 'data'
    b.km.entities.integrations[u('701')].test_variables = {'domain': 'biology'}
    b.km.entities.integrations[u('701')].test_response = common.TypeHintExchange.model_validate(
        load_synthetic('knowledge_model.json')['entities']['integrations'][str(u('701'))]['testResponse'])
    b.plugin_integration('Plugin', uuid=u('702'), plugin_uuid=u('d01'), plugin_integration_id='ror',
                         settings={'limit': 10, 'nested': [True, None, 'x']})
    metric = b.metric('Findability', abbreviation='F', uuid=u('901'))
    before = b.phase('Before submitting', uuid=u('a01'))
    b.phase('Before finishing', description='Last phase', uuid=u('a02'))
    collection = b.resource_collection('Resources', uuid=u('b01'))
    page = collection.page('Page', '# Page', uuid=u('c01'))

    options = chapter.options_question('Options', uuid=u('201'), text='Pick *one*', required_phase=before,
                                       tags=[tag], annotations=[common.KeyValue(key='a', value='1'),
                                                                common.KeyValue(key='a', value='2')])
    options.expert('Expert', 'expert@example.org', uuid=u('401'))
    options.resource_page_reference(page, uuid=u('501'))
    options.url_reference('https://example.org', 'Example', uuid=u('502'))
    yes = options.answer('Yes', advice='Good choice', uuid=u('301'), metric_measures=[(metric, 1.0, 0.5)])
    options.answer('No', uuid=u('302'))
    multi = chapter.multi_choice_question('Multi-choice', uuid=u('202'))
    multi.choice('Choice', uuid=u('601'))
    options.cross_reference(multi, 'See also', uuid=u('503'))
    items = chapter.list_question('List', uuid=u('203'))
    items.value_question('Value', uuid=u('204'), validations=[
        v for v in flat.KnowledgeModel.model_validate(load_synthetic('knowledge_model.json'))
        .entities.questions[u('204')].validations])
    chapter.integration_question('Integration', uuid=u('205'), integration=api, variables={'domain': 'biology'})
    chapter.item_select_question('Item select', uuid=u('206'), list_question=items)
    chapter.file_question('File', uuid=u('207'), required_phase=u('a02'), max_size=1048576,
                          file_types='application/pdf')
    yes.value_question('Follow-up', uuid=u('208'), value_type='NumberQuestionValueType')
    return b


def test_builder_reproduces_synthetic_fixture():
    km = build_synthetic().build()
    assert_same_json(load_synthetic('knowledge_model.json'), km.to_json_data())


def test_builder_events_and_bundle():
    builder = KnowledgeModelBuilder(uuid_factory=deterministic_uuids())
    chapter = builder.chapter('Data')
    question = chapter.options_question('Reuse existing data?')
    question.answer('Yes').value_question('Which data?')
    question.answer('No')
    km = builder.build()
    assert compile_events(builder.to_events(clock=clock())) == km
    bundle = builder.to_bundle(organization_id='example', km_id='data', version='1.0.0',
                               name='Data KM', clock=clock())
    bundle = load(KnowledgeModelBundle, bundle.to_json_data())  # strict round trip
    assert bundle.packages[0].id == 'example:data:1.0.0'
    assert compile_bundle(bundle) == km


def test_validate_synthetic_model():
    # the fixture puts every validation kind on one string question on purpose
    issues = validate(build_synthetic().build())
    assert {i.code for i in issues} == {'validation-type-mismatch'}
    assert len(issues) == 8
    assert validate(load(flat.KnowledgeModel, load_synthetic('knowledge_model.json'))) == issues


def test_validate_reports_problems():
    b = KnowledgeModelBuilder(uuid_factory=deterministic_uuids())
    chapter = b.chapter('Chapter')
    options = chapter.options_question('One answer only')
    answer = options.answer('Yes', metric_measures=[(u('999'), 2.0, 1.0)])
    chapter.multi_choice_question('')
    b.tag('Tag', color='blue')
    api = b.api_integration('API', request_url='x', response_item_template='x', variables=['a'])
    chapter.integration_question('Integration', integration=api, variables={'b': ''})
    chapter.item_select_question('Select', list_question=options)
    chapter.value_question('Number', value_type='NumberQuestionValueType',
                           validations=[common.MinLengthQuestionValidation(value=1)])
    km = b.build()
    km.entities.chapters[chapter.uuid].question_uuids.append(options.uuid)
    km.entities.answers[answer.uuid].follow_up_uuids.append(options.uuid)
    km.entities.tags[u('555')] = flat.Tag(uuid=u('555'), name='Orphan', color='#000000')
    issues = validate(km)
    codes = {(issue.severity, issue.code) for issue in issues}
    assert codes == {
        ('error', 'missing-reference'),
        ('error', 'wrong-reference-kind'),
        ('error', 'containment-cycle'),
        ('error', 'duplicate-in-list'),
        ('error', 'metric-measure-range'),
        ('warning', 'too-few-answers'),
        ('warning', 'no-choices'),
        ('warning', 'empty-title'),
        ('warning', 'invalid-color'),
        ('warning', 'integration-variables-mismatch'),
        ('warning', 'validation-type-mismatch'),
        ('info', 'unreachable-entity'),
    }
    assert [issue.severity for issue in issues] == sorted(
        (issue.severity for issue in issues), key=['error', 'warning', 'info'].index)
    cycle = next(issue for issue in issues if issue.code == 'containment-cycle')
    assert cycle.location == "Chapter 'Chapter' › OptionsQuestion 'One answer only' › Answer 'Yes'"
    assert 'break the cycle' in cycle.hint


def test_validate_multiple_parents():
    b = KnowledgeModelBuilder(uuid_factory=deterministic_uuids())
    first = b.chapter('First')
    second = b.chapter('Second')
    question = first.value_question('Shared')
    km = b.build()
    km.entities.chapters[second.uuid].question_uuids.append(question.uuid)
    [issue] = validate(km)
    assert (issue.code, issue.location) == ('multiple-parents', "Chapter 'First' › ValueQuestion 'Shared'")
    assert "Chapter 'Second'" in issue.message


def test_validate_uuid_shared_by_two_collections():
    b = KnowledgeModelBuilder(uuid_factory=deterministic_uuids())
    chapter = b.chapter('Chapter')
    tag = b.tag('Tag')
    km = b.build()
    km.entities.tags[chapter.uuid] = km.entities.tags.pop(tag.uuid).model_copy(
        update={'uuid': chapter.uuid})
    km.tag_uuids = [chapter.uuid]
    km_graph = graph.KnowledgeModel(km)
    [(kept, other)] = km_graph.collisions
    assert (kept.kind, other.kind) == ('chapter', 'tag')
    assert km_graph[chapter.uuid] is kept
    codes = [(issue.severity, issue.code) for issue in validate(km_graph)]
    assert ('error', 'duplicate-uuid') in codes
    assert ('error', 'wrong-reference-kind') in codes  # tagUuids now points to a chapter


@pytest.mark.parametrize(('name', 'warnings'), [
    ('dsw_smp_1.2.4.km.gz', 0),
    ('dsw_root_2.8.1.km.gz', 14),
    ('dmp.eosc.cz_czech-nrp-km_1.0.2.km.gz', 9),
])
def test_validate_reference_bundles(name, warnings):
    issues = validate(compile_bundle(load(KnowledgeModelBundle, load_reference(name))))
    assert [i for i in issues if i.severity == 'error'] == []
    assert len([i for i in issues if i.severity == 'warning']) == warnings
