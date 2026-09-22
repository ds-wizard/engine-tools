"""Squash knowledge model events like the backend does on publish.

Port of ``Wizard.Service.KnowledgeModel.Squash``. Events are sorted by ``createdAt`` (stable) and
grouped by UTC day; within a day:

1. *simple squash* merges an edit of an entity into its previous edit (at the earlier position)
   when neither changes child order or references,
2. *reorder squash* merges consecutive edits of the same chapter, question, answer or resource
   collection, and consecutive knowledge model edits.

A merged event takes ``uuid`` and ``parentUuid`` of the later event and ``createdAt`` of the
earlier one. Only edit events are ever merged.

Squash the events of **one package** (or one editor), as the backend does: sorting by ``createdAt``
reorders a package chain whose timestamps are not monotonic, which changes its result.

Deliberate difference from the backend: a change of ``resourceCollectionUuids`` prevents a
simple squash of knowledge model edits. The backend omits this check, so it merges such an edit
and resets the list change to *unchanged*, losing a reorder of resource collections (reported
as a backend bug).
"""
from __future__ import annotations

import itertools
import typing

from ..common import utc_date
from . import events as ev


if typing.TYPE_CHECKING:
    from collections.abc import Iterable
    from uuid import UUID


class _Rules(typing.NamedTuple):
    #: a change of any of these fields prevents a simple squash
    blocking: frozenset[str]
    #: merged only when the previous event edits the same entity, otherwise reset
    same_entity: frozenset[str]
    #: consecutive edits may be merged by the reorder squash
    reorder: typing.Literal['never', 'same_entity', 'always']


_QUESTION_BLOCKING = ('required_phase_uuid', 'tag_uuids', 'expert_uuids', 'reference_uuids')
_QUESTION_SAME_ENTITY = ('tag_uuids', 'expert_uuids', 'reference_uuids')
_NONE: frozenset[str] = frozenset()


def _question(*extra_blocking: str, extra_same_entity: tuple[str, ...] = ()) -> _Rules:
    return _Rules(frozenset((*_QUESTION_BLOCKING, *extra_blocking)),
                  frozenset((*_QUESTION_SAME_ENTITY, *extra_same_entity)), 'same_entity')


_RULES: dict[type, _Rules] = {
    ev.EditKnowledgeModelEventContent: _Rules(
        frozenset(('chapter_uuids', 'tag_uuids', 'integration_uuids', 'metric_uuids',
                   'phase_uuids', 'resource_collection_uuids')),
        frozenset(('chapter_uuids', 'tag_uuids', 'integration_uuids', 'metric_uuids',
                   'phase_uuids', 'resource_collection_uuids')),
        'always'),
    ev.EditChapterEventContent: _Rules(
        frozenset(('question_uuids',)), frozenset(('question_uuids',)), 'same_entity'),
    ev.EditOptionsQuestionEventContent: _question(
        'answer_uuids', extra_same_entity=('answer_uuids',)),
    ev.EditMultiChoiceQuestionEventContent: _question(
        'choice_uuids', extra_same_entity=('choice_uuids',)),
    ev.EditListQuestionEventContent: _question(
        'item_template_question_uuids', extra_same_entity=('item_template_question_uuids',)),
    ev.EditValueQuestionEventContent: _question(),
    ev.EditIntegrationQuestionEventContent: _question('integration_uuid'),
    ev.EditItemSelectQuestionEventContent: _question('list_question_uuid'),
    ev.EditFileQuestionEventContent: _question(),
    ev.EditAnswerEventContent: _Rules(
        frozenset(('follow_up_uuids', 'metric_measures')), frozenset(('follow_up_uuids',)),
        'same_entity'),
    ev.EditChoiceEventContent: _Rules(_NONE, _NONE, 'never'),
    ev.EditExpertEventContent: _Rules(_NONE, _NONE, 'never'),
    ev.EditResourcePageReferenceEventContent: _Rules(_NONE, _NONE, 'never'),
    ev.EditURLReferenceEventContent: _Rules(_NONE, _NONE, 'never'),
    ev.EditCrossReferenceEventContent: _Rules(_NONE, _NONE, 'never'),
    ev.EditApiIntegrationEventContent: _Rules(_NONE, _NONE, 'never'),
    ev.EditPluginIntegrationEventContent: _Rules(_NONE, _NONE, 'never'),
    ev.EditTagEventContent: _Rules(_NONE, _NONE, 'never'),
    ev.EditMetricEventContent: _Rules(_NONE, _NONE, 'never'),
    ev.EditPhaseEventContent: _Rules(_NONE, _NONE, 'never'),
    ev.EditResourceCollectionEventContent: _Rules(
        frozenset(('resource_page_uuids',)), frozenset(('resource_page_uuids',)), 'same_entity'),
    ev.EditResourcePageEventContent: _Rules(_NONE, _NONE, 'never'),
}

#: edit events whose variants must match to be merged
_VARIANT_GROUPS: tuple[frozenset[type], ...] = (
    frozenset((ev.EditOptionsQuestionEventContent, ev.EditMultiChoiceQuestionEventContent,
               ev.EditListQuestionEventContent, ev.EditValueQuestionEventContent,
               ev.EditIntegrationQuestionEventContent, ev.EditItemSelectQuestionEventContent,
               ev.EditFileQuestionEventContent)),
    frozenset((ev.EditResourcePageReferenceEventContent, ev.EditURLReferenceEventContent,
               ev.EditCrossReferenceEventContent)),
    frozenset((ev.EditApiIntegrationEventContent, ev.EditPluginIntegrationEventContent)),
)


def squash(events: Iterable[ev.Event]) -> list[ev.Event]:
    ordered = sorted(events, key=lambda event: event.created_at)
    result: list[ev.Event] = []
    for _, day in itertools.groupby(ordered, key=lambda event: utc_date(event.created_at)):
        result.extend(_squash_reorder(_squash_simple(list(day))))
    return result


def _same_kind(old: ev.Event, new: ev.Event) -> bool:
    return type(old.content) in _RULES and type(new.content) in _RULES and (
        type(old.content) is type(new.content)
        or any(type(old.content) in group and type(new.content) in group
               for group in _VARIANT_GROUPS)
    )


def _type_changed(old: ev.Event, new: ev.Event) -> bool:
    return any(type(old.content) in group and type(new.content) in group
               and type(old.content) is not type(new.content)
               for group in _VARIANT_GROUPS)


def _simple_applicable(event: ev.Event) -> bool:
    rules = _RULES.get(type(event.content))
    if rules is None:
        return False
    return not any(getattr(event.content, name).changed for name in rules.blocking)


def _reorder_applicable(previous: ev.Event, new: ev.Event) -> bool:
    if not _same_kind(previous, new):
        return False
    reorder = _RULES[type(new.content)].reorder
    return reorder == 'always' or (
        reorder == 'same_entity' and previous.entity_uuid == new.entity_uuid)


def _merge(previous: ev.Event | None, old: ev.Event, new: ev.Event) -> ev.Event:
    if type(old.content) is not type(new.content):
        return new
    rules = _RULES[type(new.content)]
    same_entity = previous is not None and previous.entity_uuid == new.entity_uuid
    data: dict[str, typing.Any] = {}
    for name in type(new.content).model_fields:
        new_value = getattr(new.content, name)
        if not isinstance(new_value, ev.EditEventField):
            data[name] = new_value
        elif name in rules.same_entity and not same_entity:
            data[name] = type(new_value).no_change()
        else:
            data[name] = new_value if new_value.changed else getattr(old.content, name)
    return ev.Event(
        uuid=new.uuid,
        parent_uuid=new.parent_uuid,
        entity_uuid=new.entity_uuid,
        content=type(new.content).model_construct(**data),
        created_at=old.created_at,
    )


def _squash_simple(events: list[ev.Event]) -> list[ev.Event]:
    latest: dict[UUID, ev.Event] = {}
    positions: dict[int, int] = {}  # id of an event in `latest` -> its index in `result`
    result: list[ev.Event] = []
    for new in events:
        old = latest.get(new.entity_uuid)
        if old is not None:
            if _type_changed(old, new) or not _simple_applicable(new):
                del latest[new.entity_uuid]
                result.append(new)
            else:
                merged = _merge(None, old, new)
                latest[new.entity_uuid] = merged
                index = positions.pop(id(old))
                result[index] = merged
                positions[id(merged)] = index
        else:
            if _simple_applicable(new):
                latest[new.entity_uuid] = new
                positions[id(new)] = len(result)
            result.append(new)
    return result


def _squash_reorder(events: list[ev.Event]) -> list[ev.Event]:
    to_delete: list[UUID] = []
    result: list[ev.Event] = []
    previous: ev.Event | None = None
    for new in events:
        if (previous is not None and not _type_changed(previous, new)
                and _reorder_applicable(previous, new)):
            merged = _merge(previous, previous, new)
            to_delete.append(previous.uuid)
            result.append(merged)
            previous = merged
        else:
            result.append(new)
            previous = new
    for uuid in to_delete:
        index = next((i for i, event in enumerate(result) if event.uuid == uuid), None)
        if index is not None:
            del result[index]
    return result
