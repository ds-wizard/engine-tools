import copy
from uuid import UUID

import pytest
from conftest import REFERENCE_BUNDLES, load_reference

from dsw.models.errors import MigrationError
from dsw.models.knowledge_model import flat
from dsw.models.knowledge_model.bundle import compile_bundle
from dsw.models.knowledge_model.migrations import migrate_bundle, migrate_events
from dsw.models.knowledge_model.migrations import steps
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.strictness import UnknownKeys, load


KM = '10000000-0000-0000-0000-000000000000'
CHAPTER = '20000000-0000-0000-0000-000000000000'
QUESTION = '30000000-0000-0000-0000-000000000000'
ANSWER = '40000000-0000-0000-0000-000000000000'
VALUE = '50000000-0000-0000-0000-000000000000'
INTEGRATION = '60000000-0000-0000-0000-000000000000'
WIDGET = '70000000-0000-0000-0000-000000000000'
CTX = steps.MigrationContext(created_at='2018-01-01T00:00:00Z')


def e(n: int) -> str:
    return f'90000000-0000-0000-0000-{n:012d}'


def v1_package(events, **fields):
    return {'id': 'org:km:1.0.0', 'name': 'Old KM', 'organizationId': 'org', 'kmId': 'km',
            'version': '1.0.0', 'metamodelVersion': 1, 'description': 'Old', 'createdAt':
            '2018-01-01T12:00:00.5Z', 'events': events, **fields}


# the shape of knowledge model events at metamodel version 1
V1_EVENTS = [
    {'eventType': 'AddKnowledgeModelEvent', 'uuid': e(1), 'path': [], 'kmUuid': KM, 'name': 'Old KM'},
    {'eventType': 'EditKnowledgeModelEvent', 'uuid': e(2), 'path': [], 'kmUuid': KM,
     'name': {'changed': True, 'value': 'Renamed'}, 'chapterUuids': {'changed': True, 'value': [CHAPTER]},
     'tagUuids': {'changed': False}},
    {'eventType': 'AddChapterEvent', 'uuid': e(3), 'path': [{'type': 'km', 'uuid': KM}],
     'chapterUuid': CHAPTER, 'title': 'Chapter', 'text': 'Text'},
    {'eventType': 'AddQuestionEvent', 'uuid': e(4), 'path': [{'type': 'km', 'uuid': KM},
                                                           {'type': 'chapter', 'uuid': CHAPTER}],
     'questionUuid': QUESTION, 'questionType': 'OptionsQuestion', 'title': 'Question', 'text': None,
     'requiredLevel': 2, 'tagUuids': []},
    {'eventType': 'AddAnswerEvent', 'uuid': e(5), 'path': [{'type': 'question', 'uuid': QUESTION}],
     'answerUuid': ANSWER, 'label': 'Yes', 'advice': None, 'metricMeasures': []},
    {'eventType': 'AddQuestionEvent', 'uuid': e(6), 'path': [{'type': 'chapter', 'uuid': CHAPTER}],
     'questionUuid': VALUE, 'questionType': 'ValueQuestion', 'title': 'Value', 'text': None,
     'requiredLevel': None, 'tagUuids': [], 'valueType': 'NumberValue'},
    {'eventType': 'EditQuestionEvent', 'uuid': e(7), 'path': [{'type': 'chapter', 'uuid': CHAPTER}],
     'questionUuid': VALUE, 'questionType': 'ValueQuestion', 'title': {'changed': False},
     'text': {'changed': False}, 'requiredLevel': {'changed': True, 'value': 4},
     'tagUuids': {'changed': False}, 'expertUuids': {'changed': False},
     'referenceUuids': {'changed': False}, 'valueType': {'changed': True, 'value': 'TextValue'}},
]


def test_migrate_v1_bundle():
    bundle = {'id': 'org:km:1.0.0', 'name': 'Old KM', 'organizationId': 'org', 'kmId': 'km',
              'version': '1.0.0', 'metamodelVersion': 1,
              'packages': [v1_package(V1_EVENTS, parentPackageId=None)]}
    snapshot = copy.deepcopy(bundle)
    migrated = migrate_bundle(bundle)
    assert bundle == snapshot  # input untouched
    assert migrated['metamodelVersion'] == 20
    package = migrated['packages'][0]
    assert package['metamodelVersion'] == 20
    assert all(set(event) == {'uuid', 'parentUuid', 'entityUuid', 'createdAt', 'content'}
               for event in package['events'])
    assert {event['createdAt'] for event in package['events']} == {'2018-01-01T12:00:00.5Z'}
    parsed = load(KnowledgeModelBundle, migrated, unknown_keys=UnknownKeys.IGNORE)
    km = compile_bundle(parsed)
    assert [km.entities.phases[p].title for p in km.phase_uuids] == [
        'Before Submitting the Proposal', 'Before Submitting the DMP',
        'Before Finishing the Project', 'After Finishing the Project']
    assert [km.entities.metrics[m].abbreviation for m in km.metric_uuids] == ['F', 'A', 'I', 'R', 'G', 'O']
    question = km.entities.questions[UUID(QUESTION)]
    assert question.required_phase_uuid == km.phase_uuids[1]
    assert km.entities.chapters[UUID(CHAPTER)].question_uuids == [UUID(QUESTION), UUID(VALUE)]
    value = km.entities.questions[UUID(VALUE)]
    assert isinstance(value, flat.ValueQuestion)
    assert value.value_type == 'TextQuestionValueType'
    assert value.required_phase_uuid == km.phase_uuids[3]
    assert value.validations == []


def test_step_10_converts_maps_to_sorted_lists_and_fails_on_lists():
    [event] = steps.step_10({'eventType': 'AddIntegrationEvent', 'uuid': e(1),
                             'annotations': {'b': '2', 'a': '1'}, 'requestHeaders': {}}, CTX)
    assert event['annotations'] == [{'key': 'a', 'value': '1'}, {'key': 'b', 'value': '2'}]
    assert event['requestHeaders'] == []
    assert event['createdAt'] == CTX.created_at
    [edit] = steps.step_10({'eventType': 'EditTagEvent', 'annotations': {'changed': False}}, CTX)
    assert edit['annotations'] == {'changed': False}
    with pytest.raises(MigrationError, match='key-value list'):
        migrate_events([{'eventType': 'AddTagEvent', 'uuid': e(1), 'annotations': []}], 10,
                       '2020-01-01T00:00:00Z', 11)


def test_step_09_integration_templates():
    [event] = steps.step_09({'eventType': 'EditIntegrationEvent', 'responseIdField': {'changed': True, 'value': 'id'},
                             'responseNameField': {'changed': False}}, CTX)
    assert event == {'eventType': 'EditIntegrationEvent',
                     'responseItemId': {'changed': True, 'value': '{{item.id}}'},
                     'responseItemTemplate': {'changed': False}}


def test_step_14_resource_page_references():
    [add] = steps.step_14({'eventType': 'AddReferenceEvent', 'referenceType': 'ResourcePageReference',
                           'shortUuid': 'abc'}, CTX)
    assert add == {'eventType': 'AddReferenceEvent', 'referenceType': 'ResourcePageReference',
                   'resourcePageUuid': None}
    [url] = steps.step_14({'eventType': 'AddReferenceEvent', 'referenceType': 'URLReference', 'url': 'x'}, CTX)
    assert url == {'eventType': 'AddReferenceEvent', 'referenceType': 'URLReference', 'url': 'x'}


def test_step_18_wraps_content_except_already_wrapped():
    [flat_event] = steps.step_18({'uuid': e(1), 'parentUuid': KM, 'entityUuid': CHAPTER,
                                  'createdAt': 'x', 'eventType': 'DeleteChapterEvent'}, CTX)
    assert flat_event['content'] == {'eventType': 'DeleteChapterEvent'}
    page = {'uuid': e(2), 'eventType': 'AddResourcePageEvent', 'title': 'P', 'content': '# text'}
    assert steps.step_18(page, CTX)[0]['content'] == {'eventType': 'AddResourcePageEvent', 'title': 'P',
                                                      'content': '# text'}
    wrapped = {'uuid': e(3), 'content': {'eventType': 'AddTagEvent'}}
    assert steps.step_18(wrapped, CTX) == [wrapped]


def test_step_19_legacy_and_widget_integrations():
    legacy = {'uuid': e(1), 'parentUuid': KM, 'entityUuid': INTEGRATION, 'createdAt': 'x', 'content': {
        'eventType': 'AddIntegrationEvent', 'integrationType': 'ApiLegacyIntegration', 'name': 'API',
        'variables': ['q'], 'requestUrl': 'u', 'requestBody': None, 'requestMethod': 'GET',
        'requestHeaders': [], 'requestEmptySearch': False, 'responseListField': None,
        'responseItemTemplate': 't', 'annotations': [], 'itemUrl': 'dropped', 'logo': 'dropped'}}
    widget = {**legacy, 'entityUuid': WIDGET,
              'content': {'eventType': 'AddIntegrationEvent', 'integrationType': 'WidgetIntegration'}}
    edit = {**legacy, 'content': {'eventType': 'EditIntegrationEvent',
                                  'integrationType': 'ApiLegacyIntegration', 'name': {'changed': False}}}
    [migrated_legacy, migrated_edit] = migrate_events([legacy, widget, edit], 19, '2024-01-01T00:00:00Z')
    content = migrated_legacy['content']
    assert content['integrationType'] == 'ApiIntegration'
    assert content['requestAllowEmptySearch'] is False
    assert (content['allowCustomReply'], content['testQ'], content['testResponse']) == (True, '', None)
    assert 'itemUrl' not in content
    assert migrated_edit['content']['requestUrl'] == {'changed': False}
    assert migrated_edit['content']['allowCustomReply'] == {'changed': False}
    assert migrate_events([{'uuid': e(9)}], 19, '2024-01-01T00:00:00Z') == []


def test_parent_package_id_fills_links():
    migrated = migrate_bundle({'packages': [v1_package([], parentPackageId='org:km:0.9.0',
                                                       forkOfPackageId='org:other:1.0.0')]})
    package = migrated['packages'][0]
    assert 'parentPackageId' not in package
    assert package['previousPackageId'] == 'org:km:0.9.0'
    assert package['forkOfPackageId'] == 'org:other:1.0.0'
    assert package['mergeCheckpointPackageId'] == 'org:km:0.9.0'


@pytest.mark.parametrize(('package', 'message'), [
    ({'metamodelVersion': 21, 'createdAt': 'x', 'events': []}, 'only up to 20'),
    ({'metamodelVersion': 0, 'createdAt': '2020-01-01T00:00:00Z', 'events': []}, 'Unsupported metamodel version 0'),
    ({'metamodelVersion': 5, 'events': []}, 'no createdAt'),
    ({'createdAt': 'x', 'events': []}, 'no valid metamodelVersion'),
])
def test_invalid_packages(package, message):
    with pytest.raises(MigrationError, match=message):
        migrate_bundle({'packages': [package]})


@pytest.mark.parametrize('name', REFERENCE_BUNDLES)
def test_current_bundles_are_unchanged(name):
    data = load_reference(name)
    migrated = migrate_bundle(data)
    for original, package in zip(data['packages'], migrated['packages'], strict=True):
        for link in ('previousPackageId', 'forkOfPackageId', 'mergeCheckpointPackageId'):
            original.setdefault(link, None)
        assert package == original
