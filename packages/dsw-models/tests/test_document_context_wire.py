import pydantic
import pytest
from conftest import assert_same_json, load_synthetic

from dsw.models.document_context.hash import compute_context_hash
from dsw.models.document_context.wire import DocumentContext
from dsw.models.project import replies
from dsw.models.strictness import UnknownKeys, load
from dsw.models.versions import DOCUMENT_TEMPLATE_METAMODEL_VERSION


@pytest.mark.parametrize('name', ['document_context.json', 'document_context_km_editor.json'])
def test_document_context_round_trip(name):
    data = load_synthetic(name)
    context = load(DocumentContext, data)
    assert context.parsed_metamodel_version == DOCUMENT_TEMPLATE_METAMODEL_VERSION
    assert context.hash == compute_context_hash(data)
    assert {type(reply.value) for reply in context.questionnaire.replies.values()} >= {
        replies.AnswerReplyValue, replies.StringReplyValue, replies.ItemListReplyValue,
        replies.IntegrationReplyValue, replies.ItemSelectReplyValue,
    }
    assert_same_json(data, context.to_json_data())


def test_project_and_km_editor_contexts():
    project = load(DocumentContext, load_synthetic('document_context.json'))
    assert project.knowledge_model_editor is None
    assert project.document.document_template.id == 'questionnaire-report'
    km_editor = load(DocumentContext, load_synthetic('document_context_km_editor.json'))
    assert km_editor.project is None
    assert km_editor.document is None
    assert km_editor.knowledge_model_editor.previous_package_version == '1.0.0'


def test_exactly_one_source():
    data = load_synthetic('document_context.json')
    editor = load_synthetic('document_context_km_editor.json')['knowledgeModelEditor']
    for invalid in ({**data, 'project': None}, {**data, 'knowledgeModelEditor': editor}):
        with pytest.raises(pydantic.ValidationError, match='Exactly one of project'):
            load(DocumentContext, invalid)


def test_document_may_be_missing():
    data = load_synthetic('document_context.json')
    del data['document']
    assert load(DocumentContext, data).document is None


@pytest.mark.parametrize(('section', 'key'), [
    ('config', 'appTitleShort'),  # removed in 5.0 (WEP 29)
    ('config', 'illustrationsColor'),
    (None, 'organization'),  # removed in 19.0
    (None, 'report'),
])
def test_removed_keys_are_unknown(section, key):
    data = load_synthetic('document_context.json')
    (data[section] if section else data)[key] = None
    with pytest.raises(pydantic.ValidationError, match=f'Unknown keys for .*: {key}'):
        load(DocumentContext, data)


def test_worker_enrichment_is_not_part_of_the_wire_model():
    data = load_synthetic('document_context.json')
    data['config']['serviceName'] = 'FAIR Wizard'
    data['extras'] = {'submissions': []}
    with pytest.raises(pydantic.ValidationError, match='Unknown keys'):
        load(DocumentContext, data)
    context = load(DocumentContext, data, unknown_keys=UnknownKeys.IGNORE)
    assert 'extras' not in context.to_json_data()


def test_metric_summary_measure_may_be_null():
    data = load_synthetic('document_context.json')
    data['questionnaire']['report']['chapterReports'][0]['metrics'][0]['measure'] = None
    context = load(DocumentContext, data)
    assert context.questionnaire.report.chapter_reports[0].metrics[0].measure is None


@pytest.mark.parametrize('name', ['document_context_worker_fixture.json',
                                  'document_context_km_editor_fixture.json',
                                  'document_context_hash_fixture.json'])
def test_backend_fixtures_differ_only_by_stale_config_keys(name):
    """The backend's shared fixtures still carry two config keys no 5.0 code writes."""
    data = load_synthetic(name)
    stale = {key: data['config'].pop(key) for key in ('appTitleShort', 'illustrationsColor')}
    assert stale == {'appTitleShort': None, 'illustrationsColor': '#e95e2a'}
    load(DocumentContext, data)
