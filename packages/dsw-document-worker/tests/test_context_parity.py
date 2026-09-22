"""Parity of the template-facing document context between the worker and dsw-models.

``dsw.models.document_context.graph`` must expose exactly what ``ctx|to_context_obj`` exposes
today. Both object models are built from the same contexts and compared attribute by attribute
(properties included), recursively.
"""
import copy
import datetime
import gzip
import json
import pathlib
import uuid

import pytest

from dsw.document_worker.model import context as worker_context
from dsw.models.document_context import graph as models_context
from dsw.models.document_context.wire import DocumentContext as WireDocumentContext
from dsw.models.knowledge_model import graph as km_graph
from dsw.models.knowledge_model.bundle import compile_bundle
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.project.report import generate_report
from dsw.models.strictness import load


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


_SCALARS = (str, int, float, bool, type(None), datetime.datetime, uuid.UUID)


def assert_same_surface(old, new, path='dc', seen=None):
    seen = set() if seen is None else seen
    if isinstance(old, _SCALARS) or isinstance(new, _SCALARS):
        assert type(old) is type(new) and old == new, f'{path}: {old!r} != {new!r}'
        return
    if isinstance(old, (list, tuple)):
        assert isinstance(new, type(old)) and len(old) == len(new), f'{path}: {old!r} vs {new!r}'
        for index, (left, right) in enumerate(zip(old, new, strict=True)):
            assert_same_surface(left, right, f'{path}[{index}]', seen)
        return
    if isinstance(old, dict):
        assert isinstance(new, dict) and list(old) == list(new), f'{path}: keys differ'
        for key in old:
            assert_same_surface(old[key], new[key], f'{path}[{key!r}]', seen)
        return
    assert type(old).__name__ == type(new).__name__, f'{path}: {type(old)} vs {type(new)}'
    if (id(old), id(new)) in seen:
        return
    seen.add((id(old), id(new)))
    names = sorted(name for name in dir(old) if not name.startswith('_'))
    assert names == sorted(name for name in dir(new) if not name.startswith('_')), f'{path}: attributes differ'
    for name in names:
        left, right = _read(old, name), _read(new, name)
        if callable(left) and not isinstance(left, type):
            assert callable(right), f'{path}.{name}: callable differs'
            continue
        assert_same_surface(left, right, f'{path}.{name}', seen)


def _read(obj, name):
    try:
        return getattr(obj, name)
    except Exception as error:  # noqa: BLE001 (compare failing properties too)
        return ('raised', type(error).__name__, str(error))


def build_both(ctx: dict):
    old = worker_context.DocumentContext(ctx=copy.deepcopy(ctx))
    old.resolve_links()
    new = models_context.DocumentContext(ctx=copy.deepcopy(ctx))
    new.resolve_links()
    return old, new


def test_synthetic_context_parity():
    old, new = build_both(enrich(json.loads(SYNTHETIC_CONTEXT.read_text(encoding='utf-8'))))
    assert_same_surface(old, new)


def test_metric_without_measure():
    ctx = enrich(json.loads(SYNTHETIC_CONTEXT.read_text(encoding='utf-8')))
    ctx['report']['chapterReports'][0]['metrics'][0]['measure'] = None
    old, new = build_both(ctx)
    assert old.report.chapter_reports[0].metrics[0].measure is None
    assert_same_surface(old, new)


def test_generated_reference_context_parity():
    ctx = enrich(generated_context())
    old, new = build_both(ctx)
    assert len(old.replies) > 300
    assert_same_surface(old, new)


# the parts real templates use most, asserted explicitly
def test_template_hot_paths():
    old, new = build_both(enrich(generated_context()))
    for dc in (old, new):
        assert dc.project.created_by is not None
        assert dc.project.versions and dc.project.version is not None
        assert dc.pkg.id and dc.pkg.org_id and dc.pkg.km_id and dc.pkg.version
        assert dc.config.client_url and dc.config.service_name
        assert dc.doc.created_at is not None
        assert dc.report.total_report.indications
        assert dc.current_phase.title
        assert dc.km.chapters and dc.e.choices
    first = next(iter(old.replies.values()))
    assert str(first.path) == str(new.replies[first.path].path)


def test_markdown_rendering_parity():
    for text in ['**bold**\\', '- a\n- b', '<script>alert(1)</script>', '```\n- x\\\n```', None]:
        assert worker_context.render_markdown(text) == models_context.render_markdown(text)
    assert worker_context.strip_markdown('*a* b') == models_context.strip_markdown('*a* b')


@pytest.mark.parametrize('version', ['18.3', '18.9', '17.9', '18.2', 'x'])
def test_metamodel_version_check_parity(version):
    from dsw.document_worker.utils import check_metamodel_version  # noqa: PLC0415

    def outcome(check):
        try:
            check(version)
        except ValueError as error:
            return str(error)
        return None

    assert outcome(check_metamodel_version) == outcome(models_context.check_metamodel_version)
