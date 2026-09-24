"""The template-facing document context, built from real contexts by the worker's own filter.

The object model itself lives in ``dsw.models.document_context.graph``; what is asserted here is
that ``ctx|to_context_obj`` keeps producing it for the contexts the worker actually receives —
the synthetic one and one generated over a released knowledge model with replies to (almost)
every question.
"""
import copy
import gzip
import json
import pathlib
import uuid

from dsw.templating.filters import to_context_obj
from dsw.models.knowledge_model import graph as km_graph
from dsw.models.knowledge_model.bundle import compile_bundle
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.project.report import generate_report
from dsw.models.strictness import load
from dsw.models.document_context.wire import DocumentContext as WireDocumentContext


MODELS_FIXTURES = pathlib.Path(__file__).parents[2] / 'dsw-models' / 'tests' / 'fixtures'
SYNTHETIC_CONTEXT = MODELS_FIXTURES / 'synthetic' / 'document_context.json'
REFERENCE_BUNDLE = MODELS_FIXTURES / 'reference' / 'dmp.eosc.cz_czech-nrp-km_1.0.2.km.gz'


def enrich(ctx: dict) -> dict:
    """What the worker adds before templates see the context."""
    ctx = copy.deepcopy(ctx)
    config = ctx['config']
    config.update({
        'serviceName': 'FAIR Wizard', 'serviceNameShort': 'FW', 'serviceUrl': 'https://fw.example.org',
        'serviceDomainName': 'fw.example.org', 'appTitle': config['appTitle'] or 'FAIR Wizard',
        'appTitleShort': config['appTitleShort'] or 'FW', 'primaryColor': config['primaryColor'] or '#0033aa',
        'illustrationsColor': config['illustrationsColor'] or '#e95e2a', 'logoUrl': config['logoUrl'] or '',
    })
    ctx['extras'] = {}
    return ctx


def generated_context() -> dict:
    """The synthetic context with the compiled Czech NRP knowledge model and replies to every question."""
    base = json.loads(SYNTHETIC_CONTEXT.read_text(encoding='utf-8'))
    with gzip.open(REFERENCE_BUNDLE, 'rt', encoding='utf-8') as file:
        km = compile_bundle(load(KnowledgeModelBundle, json.load(file)))
    graph = km_graph.KnowledgeModel(km)
    file_uuid = base['project']['files'][0]['uuid']
    counter = iter(range(1, 1_000_000))
    replies: dict[str, dict] = {}
    items_of: dict[str, list[str]] = {}

    def reply(value: dict) -> dict:
        return {'value': value, 'createdBy': None, 'createdAt': '2026-09-15T10:00:00Z'}

    def visit(question, prefix: str, depth: int) -> None:
        path = f'{prefix}.{question.uuid}'
        n = next(counter)
        if n % 7 == 0 or depth > 6:
            return  # leave some questions unanswered
        if isinstance(question, km_graph.OptionsQuestion) and question.answers:
            answer = question.answers[n % len(question.answers)]
            replies[path] = reply({'type': 'AnswerReply', 'value': str(answer.uuid)})
            for follow_up in answer.follow_up_questions:
                visit(follow_up, f'{path}.{answer.uuid}', depth + 1)
        elif isinstance(question, km_graph.ListQuestion):
            items = [str(uuid.UUID(int=next(counter))) for _ in range(2)]
            items_of[str(question.uuid)] = items
            replies[path] = reply({'type': 'ItemListReply', 'value': items})
            for item in items:
                for item_question in question.item_template_questions:
                    visit(item_question, f'{path}.{item}', depth + 1)
        elif isinstance(question, km_graph.MultiChoiceQuestion):
            value = [str(choice.uuid) for choice in question.choices[: n % 3]]
            replies[path] = reply({'type': 'MultiChoiceReply', 'value': value})
        elif isinstance(question, km_graph.IntegrationQuestion):
            content = ({'type': 'PlainType', 'value': f'Plain *{n}*'} if n % 2 else
                       {'type': 'IntegrationType', 'value': f'Item {n}\n\nmore', 'raw': {'id': n}})
            replies[path] = reply({'type': 'IntegrationReply', 'value': content})
        elif isinstance(question, km_graph.ItemSelectQuestion):
            items = items_of.get(str(question.entity.list_question_uuid), [])
            if items:
                replies[path] = reply({'type': 'ItemSelectReply', 'value': items[0]})
        elif isinstance(question, km_graph.FileQuestion):
            replies[path] = reply({'type': 'FileReply', 'value': file_uuid})
        else:
            text = ['2026-01-01', '42.5', '**bold** text\\', f'line {n}\n- a\n- b'][n % 4]
            replies[path] = reply({'type': 'StringReply', 'value': text})

    for chapter in graph.chapters:
        for question in chapter.questions:
            visit(question, str(chapter.uuid), 0)

    ctx = copy.deepcopy(base)
    ctx['knowledgeModel'] = km.to_json_data()
    ctx['project']['replies'] = replies
    ctx['project']['phaseUuid'] = str(km.phase_uuids[1])
    ctx['project']['labels'] = {path: [base['project']['labels'][next(iter(base['project']['labels']))][0]]
                                for path in list(replies)[:5]}
    content = load(WireDocumentContext, ctx)
    report = generate_report(content.knowledge_model, content.project.replies, content.project.phase_uuid)
    ctx['report'] = report.to_json_data()
    return ctx


def test_synthetic_context():
    dc = to_context_obj(enrich(json.loads(SYNTHETIC_CONTEXT.read_text(encoding='utf-8'))))
    assert dc.km.chapters
    assert dc.current_phase.title


def test_metric_without_measure():
    ctx = enrich(json.loads(SYNTHETIC_CONTEXT.read_text(encoding='utf-8')))
    ctx['report']['chapterReports'][0]['metrics'][0]['measure'] = None
    dc = to_context_obj(ctx)
    assert dc.report.chapter_reports[0].metrics[0].measure is None


def test_generated_reference_context():
    dc = to_context_obj(enrich(generated_context()))
    assert len(dc.replies) > 300


# the parts real templates use most, asserted explicitly
def test_template_hot_paths():
    dc = to_context_obj(enrich(generated_context()))
    assert dc.project.created_by is not None
    assert dc.project.versions and dc.project.version is not None
    assert dc.pkg.id and dc.pkg.org_id and dc.pkg.km_id and dc.pkg.version
    assert dc.config.client_url and dc.config.service_name
    assert dc.doc.created_at is not None
    assert dc.report.total_report.indications
    assert dc.current_phase.title
    assert dc.km.chapters and dc.e.choices
    first = next(iter(dc.replies.values()))
    assert dc.replies[first.path] is first
