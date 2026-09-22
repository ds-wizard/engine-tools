import pydantic
import pytest
from conftest import assert_same_json, load_synthetic

from dsw.models.document_context.wire import DocumentContext
from dsw.models.project import replies
from dsw.models.strictness import UnknownKeys, load
from dsw.models.versions import DOCUMENT_TEMPLATE_METAMODEL_VERSION


def test_document_context_round_trip():
    data = load_synthetic('document_context.json')
    context = load(DocumentContext, data)
    assert context.parsed_metamodel_version == DOCUMENT_TEMPLATE_METAMODEL_VERSION
    assert {type(reply.value) for reply in context.project.replies.values()} == {
        replies.AnswerReplyValue, replies.StringReplyValue, replies.ItemListReplyValue,
        replies.IntegrationReplyValue, replies.ItemSelectReplyValue, replies.FileReplyValue,
    }
    assert_same_json(data, context.to_json_data())


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
    data['report']['chapterReports'][0]['metrics'][0]['measure'] = None
    context = load(DocumentContext, data)
    assert context.report.chapter_reports[0].metrics[0].measure is None
