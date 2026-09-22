from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from conftest import load_reference
from hypothesis import HealthCheck, given, settings
from strategies import deterministic_uuids, knowledge_model_pairs
from test_knowledge_model_compiler import base_events, event, u, unchanged

from dsw.models.common import KeyValue
from dsw.models.knowledge_model import events as ev
from dsw.models.knowledge_model import flat
from dsw.models.knowledge_model.bundle import compile_bundle, package_chain
from dsw.models.knowledge_model.compiler import compile_events
from dsw.models.knowledge_model.convert import prune_unreachable
from dsw.models.knowledge_model.diff import DiffError, decompile, diff
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.knowledge_model.squash import squash
from dsw.models.strictness import load


def clock(start=datetime(2026, 9, 14, 8, 0, tzinfo=UTC)):
    ticks = iter(range(1_000_000))
    return lambda: start + timedelta(milliseconds=next(ticks))


def at(event_: ev.Event, minute: int, day: int = 1) -> ev.Event:
    return event_.model_copy(update={'created_at': datetime(2026, 1, day, 0, minute, tzinfo=UTC)})


# squash
def test_simple_squash_merges_into_earlier_position():
    first = at(event(unchanged(ev.EditChapterEventContent, title='A'), 10), 1)
    other = at(event(unchanged(ev.EditTagEventContent, name='T'), 20), 2)
    second = at(event(unchanged(ev.EditChapterEventContent, text='B'), 10), 3)
    result = squash([first, other, second])
    assert [e.entity_uuid for e in result] == [u(10), u(20)]
    merged = result[0]
    assert (merged.uuid, merged.created_at) == (second.uuid, first.created_at)
    assert merged.content.title.value == 'A'
    assert merged.content.text.value == 'B'


def test_reorder_squash_merges_consecutive_list_edits():
    first = at(event(unchanged(ev.EditChapterEventContent, question_uuids=[u(1)]), 10), 1)
    second = at(event(unchanged(ev.EditChapterEventContent, question_uuids=[u(2)], title='X'), 10), 2)
    [merged] = squash([first, second])
    assert merged.content.question_uuids.value == [u(2)]
    assert merged.content.title.value == 'X'


def test_squash_keeps_days_and_type_changes_apart():
    edits = [
        at(event(unchanged(ev.EditChapterEventContent, title='A'), 10), 1, day=1),
        at(event(unchanged(ev.EditChapterEventContent, title='B'), 10), 1, day=2),
        at(event(unchanged(ev.EditValueQuestionEventContent, title='C'), 30), 2, day=2),
        at(event(unchanged(ev.EditOptionsQuestionEventContent, title='D'), 30), 3, day=2),
    ]
    assert len(squash(edits)) == 4


def test_squash_groups_by_utc_day():
    minus_one = timezone(timedelta(hours=-1))
    plus_two = timezone(timedelta(hours=2))
    same_utc_day = [  # 23:30 and 00:30 local, both 2 January in UTC
        event(unchanged(ev.EditChapterEventContent, title='A'), 10).model_copy(
            update={'created_at': datetime(2026, 1, 1, 23, 30, tzinfo=minus_one)}),
        event(unchanged(ev.EditChapterEventContent, text='B'), 10).model_copy(
            update={'created_at': datetime(2026, 1, 2, 0, 30, tzinfo=minus_one)}),
    ]
    assert len(squash(same_utc_day)) == 1
    same_local_day = [  # 01:30 and 02:30 local, 1 and 2 January in UTC
        event(unchanged(ev.EditChapterEventContent, title='A'), 10).model_copy(
            update={'created_at': datetime(2026, 1, 2, 1, 30, tzinfo=plus_two)}),
        event(unchanged(ev.EditChapterEventContent, text='B'), 10).model_copy(
            update={'created_at': datetime(2026, 1, 2, 2, 30, tzinfo=plus_two)}),
    ]
    assert len(squash(same_local_day)) == 2


def test_squash_keeps_resource_collection_reorder():
    # the backend loses this reorder; the port deliberately does not
    events = [
        at(event(ev.AddKnowledgeModelEventContent(annotations=[]), 1, 0), 0),
        at(event(ev.AddResourceCollectionEventContent(title='A', annotations=[]), 70), 1),
        at(event(ev.AddResourceCollectionEventContent(title='B', annotations=[]), 71), 2),
        at(event(unchanged(ev.EditKnowledgeModelEventContent,
                           resource_collection_uuids=[u(71), u(70)]), 1), 3),
        at(event(unchanged(ev.EditResourceCollectionEventContent, title='A2'), 70), 4),
        at(event(unchanged(ev.EditKnowledgeModelEventContent,
                           annotations=[KeyValue(key='k', value='v')]), 1), 5),
    ]
    squashed = squash(events)
    assert compile_events(squashed) == compile_events(events)
    assert compile_events(squashed).resource_collection_uuids == [u(71), u(70)]


@pytest.mark.parametrize('name', ['dsw_smp_1.2.4.km.gz', 'dmp.eosc.cz_czech-nrp-km_1.0.2.km.gz'])
def test_squash_per_package_preserves_reference_bundles(name):
    bundle = load(KnowledgeModelBundle, load_reference(name))
    chain = package_chain(bundle)
    original = compile_events(e for package in chain for e in package.events)
    squashed = compile_events(e for package in chain for e in squash(package.events))
    assert squashed == original


# diff and decompile
def test_decompile_and_diff_simple():
    old = compile_events(base_events())
    new = old.model_copy(deep=True)
    new.entities.questions[u(30)].title = 'Changed'
    new.entities.chapters[u(10)].question_uuids.reverse()
    events = diff(old, new, uuid_factory=deterministic_uuids(), clock=clock())
    assert [type(e.content) for e in events] == [ev.EditChapterEventContent, ev.EditOptionsQuestionEventContent]
    assert events[1].content.title.value == 'Changed'
    assert not events[1].content.tag_uuids.changed
    assert compile_events(events, old) == new
    assert diff(new, new) == []
    assert compile_events(decompile(new)) == new


def test_diff_moves_between_parents():
    old = compile_events(base_events())
    new = old.model_copy(deep=True)
    new.entities.chapters[u(10)].question_uuids.remove(u(30))
    new.entities.questions[u(31)].item_template_question_uuids.append(u(30))
    events = diff(old, new)
    assert [type(e.content) for e in events] == [ev.MoveQuestionEventContent]
    assert compile_events(events, old) == new


def test_diff_rejects_kind_change_and_other_model():
    old = compile_events(base_events())
    new = old.model_copy(deep=True)
    chapter = new.entities.chapters.pop(u(10))
    new.entities.questions.pop(u(31))
    new.entities.chapters[u(31)] = chapter.model_copy(update={'uuid': u(31)})
    new.chapter_uuids = [u(31)]
    with pytest.raises(DiffError, match='changes entity kind'):
        diff(old, new)
    with pytest.raises(DiffError, match='UUIDs differ'):
        diff(old, flat.KnowledgeModel(uuid=u(2)))
    shared = old.model_copy(deep=True)
    shared.entities.tags[u(10)] = flat.Tag(uuid=u(10), name='Clash', color='#000000')
    with pytest.raises(DiffError, match='used by both chapters and tags'):
        diff(old, shared)


@pytest.mark.parametrize('name', ['dsw_smp_1.2.4.km.gz', 'dmp.eosc.cz_czech-nrp-km_1.0.2.km.gz',
                                  'dsw_root_2.8.1.km.gz'])
def test_decompile_reference_bundles(name):
    km = compile_bundle(load(KnowledgeModelBundle, load_reference(name)))
    events = decompile(km, clock=clock())
    assert compile_events(events) == prune_unreachable(km)
    assert compile_events(squash(events)) == prune_unreachable(km)


def test_diff_between_reference_versions():
    bundle = load(KnowledgeModelBundle, load_reference('dmp.eosc.cz_czech-nrp-km_1.0.2.km.gz'))
    versions = [compile_bundle(bundle, package.id) for package in package_chain(bundle)]
    for old, new in zip(versions, versions[1:], strict=False):
        events = diff(old, new)  # verifies the result itself
        assert prune_unreachable(compile_events(events, old)) == prune_unreachable(new)


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(knowledge_model_pairs())
def test_diff_properties(pair):
    old, new = pair
    events = diff(old, new, uuid_factory=deterministic_uuids(10**7), clock=clock())
    assert prune_unreachable(compile_events(events, old)) == new
    assert prune_unreachable(compile_events(squash(events), old)) == new
    assert diff(new, new) == []
    assert compile_events(decompile(new, clock=clock())) == new


def test_deterministic_output():
    old = compile_events(base_events())
    kwargs = {'uuid_factory': deterministic_uuids(), 'clock': clock()}
    first = [e.to_json_data() for e in decompile(old, **kwargs)]
    kwargs = {'uuid_factory': deterministic_uuids(), 'clock': clock()}
    assert first == [e.to_json_data() for e in decompile(old, **kwargs)]
    assert first[0]['uuid'] == str(UUID(int=1 << 64))
