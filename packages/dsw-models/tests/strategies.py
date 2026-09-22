"""Hypothesis strategies producing valid knowledge models (every reference resolves)."""
import uuid

from hypothesis import strategies as st

from dsw.models.common import KeyValue
from dsw.models.knowledge_model import common, tree


def model(cls, **fields):
    """Build a pydantic model from field-name strategies (``st.builds`` would add aliases)."""
    return st.fixed_dictionaries(fields).map(lambda data: cls(**data))


TEXT = st.text(alphabet='abcdefghij XYZ', min_size=1, max_size=12)
OPTIONAL_TEXT = st.none() | TEXT
ANNOTATIONS = st.lists(model(KeyValue, key=TEXT, value=TEXT), max_size=2)
UUIDS = st.uuids(version=4)


def deterministic_uuids(seed: int = 0):
    counter = iter(range(seed, seed + 1_000_000))
    return lambda: uuid.UUID(int=next(counter) + (1 << 64))


@st.composite
def _leaves(draw):
    return {
        'tags': draw(st.lists(model(tree.Tag, uuid=UUIDS, name=TEXT, description=OPTIONAL_TEXT,
                                        color=st.just('#0033aa'), annotations=ANNOTATIONS),
                              max_size=3, unique_by=lambda t: t.uuid)),
        'phases': draw(st.lists(model(tree.Phase, uuid=UUIDS, title=TEXT,
                                          description=OPTIONAL_TEXT, annotations=ANNOTATIONS),
                                max_size=3, unique_by=lambda p: p.uuid)),
        'metrics': draw(st.lists(model(tree.Metric, uuid=UUIDS, title=TEXT,
                                           abbreviation=OPTIONAL_TEXT, description=OPTIONAL_TEXT,
                                           annotations=ANNOTATIONS),
                                 max_size=2, unique_by=lambda m: m.uuid)),
        'integrations': draw(st.lists(
            st.one_of(
                model(tree.ApiIntegration, uuid=UUIDS, name=TEXT, variables=st.lists(TEXT, max_size=2),
                          allow_custom_reply=st.booleans(), request_method=st.just('GET'),
                          request_url=TEXT, request_allow_empty_search=st.booleans(),
                          response_item_template=TEXT, test_q=st.just(''), annotations=ANNOTATIONS),
                model(tree.PluginIntegration, uuid=UUIDS, name=TEXT, plugin_uuid=UUIDS,
                          plugin_integration_id=TEXT,
                          plugin_integration_settings=st.dictionaries(TEXT, st.integers(), max_size=2),
                          annotations=ANNOTATIONS),
            ),
            max_size=2, unique_by=lambda i: i.uuid)),
        'pages': draw(st.lists(model(tree.ResourcePage, uuid=UUIDS, title=TEXT, content=TEXT,
                                         annotations=ANNOTATIONS),
                               max_size=3, unique_by=lambda p: p.uuid)),
    }


def _question(leaves, depth):
    tag_uuids = st.lists(st.sampled_from([t.uuid for t in leaves['tags']]), unique=True, max_size=2) \
        if leaves['tags'] else st.just([])
    phase = st.none() | st.sampled_from([p.uuid for p in leaves['phases']]) \
        if leaves['phases'] else st.none()
    references = st.lists(st.one_of(
        model(tree.URLReference, url=TEXT, label=TEXT, annotations=ANNOTATIONS),
        *([model(tree.ResourcePageReference,
                     resource_page_uuid=st.sampled_from([p.uuid for p in leaves['pages']]))]
          if leaves['pages'] else []),
        *([model(tree.CrossReference, target_uuid=st.sampled_from([t.uuid for t in leaves['tags']]),
                     description=TEXT)] if leaves['tags'] else []),
    ), max_size=2)
    common_fields = {
        'title': TEXT, 'text': OPTIONAL_TEXT, 'required_phase_uuid': phase, 'tag_uuids': tag_uuids,
        'annotations': ANNOTATIONS, 'references': references,
        'experts': st.lists(model(tree.Expert, name=TEXT, email=TEXT), max_size=1),
    }
    nested = st.lists(_question(leaves, depth - 1), max_size=2) if depth > 0 else st.just([])
    metric_measures = st.lists(model(
        common.MetricMeasure, metric_uuid=st.sampled_from([m.uuid for m in leaves['metrics']]),
        measure=st.floats(0, 1), weight=st.floats(0, 1)), max_size=1, unique_by=lambda m: m.metric_uuid) \
        if leaves['metrics'] else st.just([])
    variants = [
        model(tree.OptionsQuestion, **common_fields, answers=st.lists(model(
            tree.Answer, label=TEXT, advice=OPTIONAL_TEXT, metric_measures=metric_measures,
            follow_up_questions=nested), max_size=2)),
        model(tree.MultiChoiceQuestion, **common_fields,
                  choices=st.lists(model(tree.Choice, label=TEXT), max_size=2)),
        model(tree.ListQuestion, **common_fields, item_template_questions=nested),
        model(tree.ValueQuestion, **common_fields,
                  value_type=st.sampled_from(['StringQuestionValueType', 'NumberQuestionValueType'])),
        model(tree.ItemSelectQuestion, **common_fields),
        model(tree.FileQuestion, **common_fields, max_size=st.none() | st.integers(1, 10)),
    ]
    if leaves['integrations']:
        variants.append(model(tree.IntegrationQuestion, **common_fields,
                                  integration_uuid=st.sampled_from([i.uuid for i in leaves['integrations']])))
    return st.one_of(variants)


@st.composite
def tree_knowledge_models(draw, max_depth: int = 2, min_chapters: int = 0):
    leaves = draw(_leaves())
    chapters = draw(st.lists(model(tree.Chapter, title=TEXT, text=OPTIONAL_TEXT, annotations=ANNOTATIONS,
                                       questions=st.lists(_question(leaves, max_depth),
                                                          min_size=min(min_chapters, 1), max_size=3)),
                             min_size=min_chapters, max_size=3))
    pages = leaves['pages']
    collections = [tree.ResourceCollection(title='Collection', resource_pages=pages)] if pages else []
    return tree.KnowledgeModel(
        annotations=draw(ANNOTATIONS),
        chapters=chapters,
        tags=leaves['tags'],
        phases=leaves['phases'],
        metrics=leaves['metrics'],
        integrations=leaves['integrations'],
        resource_collections=collections,
    )


@st.composite
def knowledge_model_pairs(draw):
    """A flat knowledge model and a mutated copy (unreachable entities pruned)."""
    from dsw.models.knowledge_model import convert, flat
    from dsw.models.knowledge_model.compiler import convert_entity

    old = convert.tree_to_flat(draw(tree_knowledge_models(min_chapters=2)),
                               uuid_factory=deterministic_uuids())
    new = old.model_copy(deep=True)
    e = new.entities
    graft_seeds = iter(range(1, 1000))

    def pick(items):
        items = list(items)
        return draw(st.sampled_from(items)) if items else None

    for operation in draw(st.lists(st.sampled_from(
            ['retitle', 'drop', 'move', 'reorder', 'retype', 'delete_tag', 'relabel', 'graft']),
            min_size=1, max_size=8)):
        if operation == 'retitle' and (question := pick(e.questions.values())):
            question.title = draw(TEXT)
        elif operation == 'relabel' and (answer := pick(e.answers.values())):
            answer.label = draw(TEXT)
            answer.advice = draw(OPTIONAL_TEXT)
        elif operation == 'drop' and (chapter := pick(e.chapters.values())) and chapter.question_uuids:
            chapter.question_uuids.remove(pick(chapter.question_uuids))
        elif operation == 'move' and len(e.chapters) > 1 and (source := pick(e.chapters.values())):
            if source.question_uuids:
                question_uuid = pick(source.question_uuids)
                source.question_uuids.remove(question_uuid)
                target = pick(chapter for chapter in e.chapters.values() if chapter is not source)
                target.question_uuids.insert(0, question_uuid)
        elif operation == 'reorder':
            new.chapter_uuids.reverse()
            if chapter := pick(e.chapters.values()):
                chapter.question_uuids.reverse()
        elif operation == 'retype' and (question := pick(e.questions.values())):
            target_type = draw(st.sampled_from([flat.ValueQuestion, flat.OptionsQuestion,
                                                flat.ListQuestion, flat.FileQuestion]))
            e.questions[question.uuid] = convert_entity(question, target_type)
        elif operation == 'delete_tag' and (tag_uuid := pick(new.tag_uuids)):
            new.tag_uuids.remove(tag_uuid)
            del e.tags[tag_uuid]
            for question in e.questions.values():
                if tag_uuid in question.tag_uuids:
                    question.tag_uuids.remove(tag_uuid)
        elif operation == 'graft':
            seed = next(graft_seeds) * 100_000
            extra = convert.tree_to_flat(draw(tree_knowledge_models(max_depth=1)),
                                         uuid_factory=deterministic_uuids(seed))
            for name in type(e).model_fields:
                getattr(e, name).update(getattr(extra.entities, name))
            for name in ('chapter_uuids', 'tag_uuids', 'integration_uuids', 'metric_uuids',
                         'phase_uuids', 'resource_collection_uuids'):
                getattr(new, name).extend(getattr(extra, name))
    return old, convert.prune_unreachable(new)
