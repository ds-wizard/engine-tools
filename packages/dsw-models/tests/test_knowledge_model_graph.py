from uuid import UUID

import pytest
from conftest import load_synthetic
from hypothesis import HealthCheck, given, settings
from strategies import deterministic_uuids, tree_knowledge_models

from dsw.models.knowledge_model import convert, flat, graph, visitor
from dsw.models.project.replies import Reply
from dsw.models.project.walker import walk_replies
from dsw.models.strictness import load


def u(suffix: str) -> UUID:
    return UUID(f'00000000-0000-0000-0000-{suffix.rjust(12, "0")}')


@pytest.fixture
def km() -> graph.KnowledgeModel:
    return convert.flat_to_graph(load(flat.KnowledgeModel, load_synthetic('knowledge_model.json')))


def test_graph_structure(km):
    assert [c.title for c in km.chapters] == ['Chapter']
    chapter = km.chapters[0]
    assert [type(q).__name__ for q in chapter.questions] == [
        'OptionsQuestion', 'MultiChoiceQuestion', 'ListQuestion', 'IntegrationQuestion',
        'ItemSelectQuestion', 'FileQuestion',
    ]
    options = chapter.questions[0]
    assert isinstance(options, graph.OptionsQuestion)
    assert options.title == options.entity.title == 'Options'
    assert options.parent is chapter
    assert options.required_phase is km.phases[0]
    assert [t.name for t in options.tags] == ['Tag']
    assert [type(r).__name__ for r in options.references] == [
        'ResourcePageReference', 'URLReference', 'CrossReference']
    follow_up = options.answers[0].follow_up_questions[0]
    assert follow_up.entity_path == (chapter.uuid, options.uuid, options.answers[0].uuid, follow_up.uuid)
    assert follow_up.ancestors == [options.answers[0], options, chapter]
    assert options.annotation('a') == '1'
    assert options.annotation_values('a') == ['1', '2']
    assert options.answers[0].metric_measures[0].metric is km.metrics[0]


def test_graph_reverse_indexes(km):
    list_question = km[u('203')]
    item_select = km[u('206')]
    assert isinstance(list_question, graph.ListQuestion)
    assert list_question.item_select_questions == [item_select]
    assert item_select.list_question is list_question
    assert km.tags[0].questions == [km[u('201')]]
    assert km.integrations[0].questions == [km[u('205')]]
    assert km.phases[1].questions == [km[u('207')]]
    assert km.phases[1].order == 1
    assert km[u('c01')].references == [km[u('501')]]
    assert km.references_to(km[u('202')]) == [km[u('503')]]
    assert km[u('c01')].parent is km.resource_collections[0]


def test_graph_is_clean(km):
    assert km.dangling == []
    assert km.shared == []
    assert km.collisions == []
    assert km.unreachable == []
    assert len(km) == sum(len(entities) for entities in km.flat.entities.model_dump().values())


def test_graph_records_problems():
    data = load_synthetic('knowledge_model.json')
    entities = data['entities']
    chapter = entities['chapters'][str(u('101'))]
    chapter['questionUuids'].append(str(u('999')))             # missing
    chapter['questionUuids'].append(str(u('301')))             # an answer, not a question
    chapter['questionUuids'].append(str(u('208')))             # already a follow-up
    entities['phases'][str(u('a03'))] = {'uuid': str(u('a03')), 'title': 'Orphan'}
    km = convert.flat_to_graph(load(flat.KnowledgeModel, data))
    assert {(d.field, d.target_uuid, d.reason) for d in km.dangling} == {
        ('questionUuids', u('999'), 'missing'),
        ('questionUuids', u('301'), 'wrong_type'),
    }
    assert km.shared == [(km[u('208')], km.chapters[0])]
    assert km[u('208')].parent is km[u('301')]
    assert [node.uuid for node in km.unreachable] == [u('a03')]


def test_graph_survives_cycles():
    data = load_synthetic('knowledge_model.json')
    answer = data['entities']['answers'][str(u('301'))]
    answer['followUpUuids'].append(str(u('201')))  # the answer's own question
    km = convert.flat_to_graph(load(flat.KnowledgeModel, data))
    assert km[u('201')].parent is km.chapters[0]
    assert (km[u('201')], km[u('301')]) in km.shared
    assert len(list(visitor.iter_nodes(km))) == len(km)


class _Recorder(visitor.KnowledgeModelVisitor):

    def __init__(self):
        self.events = []

    def visit_question(self, node):
        self.events.append(('question', node.title))

    def visit_options_question(self, node):
        self.events.append(('options', node.title))

    def visit_answer(self, node):
        self.events.append(('answer', node.label))
        return visitor.SKIP if node.label == 'Yes' else None

    def leave_chapter(self, node):
        self.events.append(('leave', node.title))


def test_visitor_dispatch_skip_and_leave(km):
    recorder = _Recorder()
    visitor.walk(km, recorder)
    assert recorder.events == [
        ('options', 'Options'),
        ('answer', 'Yes'),
        ('answer', 'No'),
        ('question', 'Multi-choice'),
        ('question', 'List'),
        ('question', 'Value'),
        ('question', 'Integration'),
        ('question', 'Item select'),
        ('question', 'File'),
        ('leave', 'Chapter'),
    ]


def test_visitor_orders(km):
    depth = [n.uuid for n in visitor.iter_nodes(km, order='depth')]
    breadth = [n.uuid for n in visitor.iter_nodes(km, order='breadth')]
    assert set(depth) == set(breadth) == set(km.reachable)
    assert depth.index(u('208')) < depth.index(u('202'))
    assert breadth.index(u('202')) < breadth.index(u('208'))


def test_walk_replies():
    context = load_synthetic('document_context.json')
    km = convert.flat_to_graph(load(flat.KnowledgeModel, context['knowledgeModel']))
    replies = {path: load(Reply, reply) for path, reply in context['project']['replies'].items()}
    walked = [(qp.question.title, qp.reply is not None, qp.depth) for qp in walk_replies(km, replies)]
    assert walked == [
        ('Options', True, 0),
        ('Follow-up', True, 2),
        ('Multi-choice', False, 0),
        ('List', True, 0),
        ('Value', True, 2),
        ('Value', True, 2),
        ('Integration', True, 0),
        ('Item select', True, 0),
        ('File', True, 0),
    ]
    items = [qp.item_uuids for qp in walk_replies(km, replies) if qp.item_uuids]
    assert len(items) == 2


def test_tree_round_trip_of_synthetic_model():
    km = load(flat.KnowledgeModel, load_synthetic('knowledge_model.json'))
    tree_km = convert.flat_to_tree(km)
    assert tree_km.chapters[0].questions[0].answers[0].follow_up_questions[0].title == 'Follow-up'
    assert convert.tree_to_flat(tree_km) == km


def test_tree_to_flat_assigns_and_checks_uuids():
    tree_km = convert.flat_to_tree(load(flat.KnowledgeModel, load_synthetic('knowledge_model.json')))
    tree_km.chapters[0].uuid = None
    tree_km.chapters[0].questions[1].uuid = None
    km = convert.tree_to_flat(tree_km, uuid_factory=deterministic_uuids())
    assert km.chapter_uuids == [UUID(int=1 << 64)]
    assert km.entities.chapters[UUID(int=1 << 64)].question_uuids[1] == UUID(int=(1 << 64) + 1)
    tree_km.chapters[0].questions[2].uuid = tree_km.chapters[0].questions[0].uuid
    with pytest.raises(convert.ConversionError, match='used by more than one entity'):
        convert.tree_to_flat(tree_km)


@settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
@given(tree_knowledge_models())
def test_generated_models_are_consistent(tree_km):
    km = convert.tree_to_flat(tree_km, uuid_factory=deterministic_uuids())
    assert convert.tree_to_flat(convert.flat_to_tree(km)) == km
    km_graph = convert.flat_to_graph(km)
    assert km_graph.dangling == []
    assert km_graph.shared == []
    assert km_graph.unreachable == []
    assert len(list(visitor.iter_nodes(km_graph))) == len(km_graph)
