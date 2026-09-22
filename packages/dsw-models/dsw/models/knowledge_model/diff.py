"""Events that turn one knowledge model into another.

Entities are matched by UUID. :func:`diff` produces, in replay order: additions (parents before
children), moves (an existing entity under a different parent), deletions (the backend cascades
to contained entities) and edits (only changed fields; a type change converts the entity).

Every produced event is applied to a working copy with :class:`.compiler.Compiler`, so later
events are computed against the real intermediate state, backend quirks included. The result
is verified: ``compile_events(diff(old, new), old)`` equals ``new`` apart from entities that are
not reachable from the top-level lists (the event model cannot express those, and nothing uses
them); :func:`.convert.prune_unreachable` removes them.
"""
from __future__ import annotations

import typing
import uuid as uuid_module
from datetime import UTC, datetime

from ..common import NULL_UUID
from ..errors import ModelsError
from . import events as ev
from . import flat, graph
from .compiler import Compiler, convert_entity
from .convert import prune_unreachable
from .visitor import iter_nodes


if typing.TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID


class DiffError(ModelsError):
    """The change cannot be expressed with knowledge model events."""


def _now() -> datetime:
    return datetime.now(tz=UTC)


def diff(
    old: flat.KnowledgeModel,
    new: flat.KnowledgeModel,
    *,
    uuid_factory: Callable[[], UUID] = uuid_module.uuid4,
    clock: Callable[[], datetime] = _now,
) -> list[ev.Event]:
    """Events changing ``old`` into ``new`` (both must have the same knowledge model UUID)."""
    if old.uuid != new.uuid:
        raise DiffError(f'Knowledge model UUIDs differ: {old.uuid} != {new.uuid}')
    for km in (old, new):
        _check_unique_uuids(km)
    return _Differ(old, new, uuid_factory, clock).run()


def _check_unique_uuids(km: flat.KnowledgeModel) -> None:
    seen: dict[UUID, str] = {}
    for collection in _DELETE:
        for uuid in getattr(km.entities, collection):
            if uuid in seen:
                raise DiffError(f'UUID {uuid} is used by both {seen[uuid]} and {collection}')
            seen[uuid] = collection


def decompile(
    km: flat.KnowledgeModel,
    *,
    uuid_factory: Callable[[], UUID] = uuid_module.uuid4,
    clock: Callable[[], datetime] = _now,
) -> list[ev.Event]:
    """Events creating ``km`` from nothing, e.g. for a new package."""
    add = ev.Event(
        uuid=uuid_factory(), parent_uuid=NULL_UUID, entity_uuid=km.uuid, created_at=clock(),
        content=ev.AddKnowledgeModelEventContent(annotations=list(km.annotations)),
    )
    empty = flat.KnowledgeModel(uuid=km.uuid, annotations=list(km.annotations))
    return [add, *diff(empty, km, uuid_factory=uuid_factory, clock=clock)]


# entity type -> (collection, add content type, edit content type)
_KINDS: dict[type, tuple[str, typing.Any, typing.Any]] = {
    flat.Chapter: ('chapters', ev.AddChapterEventContent, ev.EditChapterEventContent),
    flat.OptionsQuestion: (
        'questions', ev.AddOptionsQuestionEventContent, ev.EditOptionsQuestionEventContent),
    flat.MultiChoiceQuestion: (
        'questions', ev.AddMultiChoiceQuestionEventContent,
        ev.EditMultiChoiceQuestionEventContent),
    flat.ListQuestion: (
        'questions', ev.AddListQuestionEventContent, ev.EditListQuestionEventContent),
    flat.ValueQuestion: (
        'questions', ev.AddValueQuestionEventContent, ev.EditValueQuestionEventContent),
    flat.IntegrationQuestion: (
        'questions', ev.AddIntegrationQuestionEventContent,
        ev.EditIntegrationQuestionEventContent),
    flat.ItemSelectQuestion: (
        'questions', ev.AddItemSelectQuestionEventContent,
        ev.EditItemSelectQuestionEventContent),
    flat.FileQuestion: (
        'questions', ev.AddFileQuestionEventContent, ev.EditFileQuestionEventContent),
    flat.Answer: ('answers', ev.AddAnswerEventContent, ev.EditAnswerEventContent),
    flat.Choice: ('choices', ev.AddChoiceEventContent, ev.EditChoiceEventContent),
    flat.Expert: ('experts', ev.AddExpertEventContent, ev.EditExpertEventContent),
    flat.ResourcePageReference: (
        'references', ev.AddResourcePageReferenceEventContent,
        ev.EditResourcePageReferenceEventContent),
    flat.URLReference: (
        'references', ev.AddURLReferenceEventContent, ev.EditURLReferenceEventContent),
    flat.CrossReference: (
        'references', ev.AddCrossReferenceEventContent, ev.EditCrossReferenceEventContent),
    flat.ApiIntegration: (
        'integrations', ev.AddApiIntegrationEventContent, ev.EditApiIntegrationEventContent),
    flat.PluginIntegration: (
        'integrations', ev.AddPluginIntegrationEventContent,
        ev.EditPluginIntegrationEventContent),
    flat.Tag: ('tags', ev.AddTagEventContent, ev.EditTagEventContent),
    flat.Metric: ('metrics', ev.AddMetricEventContent, ev.EditMetricEventContent),
    flat.Phase: ('phases', ev.AddPhaseEventContent, ev.EditPhaseEventContent),
    flat.ResourceCollection: (
        'resource_collections', ev.AddResourceCollectionEventContent,
        ev.EditResourceCollectionEventContent),
    flat.ResourcePage: (
        'resource_pages', ev.AddResourcePageEventContent, ev.EditResourcePageEventContent),
}

_DELETE: dict[str, type] = {
    'chapters': ev.DeleteChapterEventContent,
    'questions': ev.DeleteQuestionEventContent,
    'answers': ev.DeleteAnswerEventContent,
    'choices': ev.DeleteChoiceEventContent,
    'experts': ev.DeleteExpertEventContent,
    'references': ev.DeleteReferenceEventContent,
    'integrations': ev.DeleteIntegrationEventContent,
    'tags': ev.DeleteTagEventContent,
    'metrics': ev.DeleteMetricEventContent,
    'phases': ev.DeletePhaseEventContent,
    'resource_collections': ev.DeleteResourceCollectionEventContent,
    'resource_pages': ev.DeleteResourcePageEventContent,
}

_MOVE: dict[str, type] = {
    'questions': ev.MoveQuestionEventContent,
    'answers': ev.MoveAnswerEventContent,
    'choices': ev.MoveChoiceEventContent,
    'experts': ev.MoveExpertEventContent,
    'references': ev.MoveReferenceEventContent,
}

_ROOT_COLLECTIONS = ('integrations', 'tags', 'metrics', 'phases', 'resource_collections',
                     'chapters')
_EDIT_ORDER = ('integrations', 'chapters', 'questions', 'answers', 'choices', 'experts',
               'references', 'tags', 'metrics', 'phases', 'resource_collections', 'resource_pages')

# (parent collection, child list field) -> child collection
_CHILD_LISTS: tuple[tuple[str, str, str], ...] = (
    ('chapters', 'question_uuids', 'questions'),
    ('questions', 'item_template_question_uuids', 'questions'),
    ('answers', 'follow_up_uuids', 'questions'),
    ('questions', 'answer_uuids', 'answers'),
    ('questions', 'choice_uuids', 'choices'),
    ('questions', 'expert_uuids', 'experts'),
    ('questions', 'reference_uuids', 'references'),
    ('resource_collections', 'resource_page_uuids', 'resource_pages'),
)


class _Differ:

    def __init__(self, old: flat.KnowledgeModel, new: flat.KnowledgeModel,
                 uuid_factory: Callable[[], UUID], clock: Callable[[], datetime]):
        self.compiler = Compiler(old.model_copy(deep=True))
        self.target = prune_unreachable(new)
        self.target_graph = graph.KnowledgeModel(self.target)
        self.uuid_factory = uuid_factory
        self.clock = clock
        self.events: list[ev.Event] = []

    @property
    def current(self) -> flat.KnowledgeModel:
        return self.compiler.km

    def run(self) -> list[ev.Event]:
        self._add_and_move()
        self._delete()
        self._add_and_move()  # re-add what deletes cascaded away from elsewhere
        self._edit()
        if prune_unreachable(self.current) != self.target:
            raise DiffError('Events do not reproduce the target knowledge model')
        return self.events

    def _emit(self, parent_uuid: UUID, entity_uuid: UUID, content: typing.Any) -> None:
        event = ev.Event(uuid=self.uuid_factory(), parent_uuid=parent_uuid,
                         entity_uuid=entity_uuid, content=content, created_at=self.clock())
        self.compiler.apply(event)
        self.events.append(event)

    def _collection_of(self, entity: typing.Any) -> str:
        return _KINDS[type(entity)][0]

    def _current_entity(self, collection: str, uuid: UUID) -> typing.Any:
        return getattr(self.current.entities, collection).get(uuid)

    def _current_parents(self) -> dict[UUID, UUID]:
        """First parent listing each entity in the current knowledge model."""
        parents: dict[UUID, UUID] = {}
        for parent_collection, field, _ in _CHILD_LISTS:
            for parent in getattr(self.current.entities, parent_collection).values():
                for child_uuid in getattr(parent, field, ()):
                    parents.setdefault(child_uuid, parent.uuid)
        return parents

    # additions and moves
    def _add_and_move(self) -> None:
        km_uuid = self.current.uuid
        parents = self._current_parents()
        for node in iter_nodes(self.target_graph):
            collection = self._collection_of(node.entity)
            parent_uuid = node.parent.uuid if node.parent is not None else km_uuid
            existing = self._current_entity(collection, node.uuid)
            if existing is None:
                self._check_unused(node.uuid, collection)
                self._add(node.entity, parent_uuid)
                parents[node.uuid] = parent_uuid
            elif node.parent is not None and not self._listed_under(node, node.parent):
                current_parent = parents.get(node.uuid, NULL_UUID)
                if collection in _MOVE:
                    self._emit(current_parent, node.uuid,
                               _MOVE[collection](target_uuid=parent_uuid))
                else:
                    self._emit(current_parent, node.uuid, _DELETE[collection]())
                    self._add(node.entity, parent_uuid)
                parents[node.uuid] = parent_uuid

    def _check_unused(self, uuid: UUID, collection: str) -> None:
        for other in _DELETE:
            if other != collection and uuid in getattr(self.current.entities, other):
                raise DiffError(f'UUID {uuid} changes entity kind from {other} to {collection}')

    def _listed_under(self, node: graph.Node, parent: graph.Node) -> bool:
        parent_collection = self._collection_of(parent.entity)
        current_parent = self._current_entity(parent_collection, parent.uuid)
        if current_parent is None:
            return False
        collection = self._collection_of(node.entity)
        return any(
            node.uuid in getattr(current_parent, field, ())
            for owner, field, child in _CHILD_LISTS
            if owner == parent_collection and child == collection
        )

    def _add(self, entity: typing.Any, parent_uuid: UUID) -> None:
        content_type = _KINDS[type(entity)][1]
        data = {name: getattr(entity, name)
                for name in content_type.model_fields if name != 'event_type'}
        self._emit(parent_uuid, entity.uuid, content_type.model_validate(data))

    # deletions
    def _delete(self) -> None:
        parents = self._current_parents()
        for collection in (*_ROOT_COLLECTIONS, 'questions', 'answers', 'choices', 'experts',
                           'references', 'resource_pages'):
            wanted = getattr(self.target.entities, collection)
            for uuid in list(getattr(self.current.entities, collection)):
                if uuid not in wanted and uuid in getattr(self.current.entities, collection):
                    self._emit(parents.get(uuid, self.current.uuid), uuid, _DELETE[collection]())

    # edits
    def _edit(self) -> None:
        km_content = self._edit_content(
            ev.EditKnowledgeModelEventContent, self.current, self.target)
        if km_content is not None:
            self._emit(NULL_UUID, self.target.uuid, km_content)
        for collection in _EDIT_ORDER:
            for uuid, entity in getattr(self.target.entities, collection).items():
                current = self._current_entity(collection, uuid)
                if type(current) is not type(entity):
                    current = convert_entity(current, type(entity))
                    changed_type = True
                else:
                    changed_type = False
                content = self._edit_content(_KINDS[type(entity)][2], current, entity,
                                             force=changed_type)
                if content is not None:
                    node = self.target_graph.get(uuid)
                    parent = node.parent if node is not None else None
                    self._emit(parent.uuid if parent else self.target.uuid, uuid, content)

    @staticmethod
    def _edit_content(content_type: typing.Any, current: typing.Any, target: typing.Any, *,
                      force: bool = False) -> typing.Any:
        data: dict[str, typing.Any] = {}
        changed = force
        for name, field in content_type.model_fields.items():
            annotation = field.annotation
            if not (isinstance(annotation, type) and issubclass(annotation, ev.EditEventField)):
                continue
            value = getattr(target, name)
            if getattr(current, name) == value:
                data[name] = annotation.no_change()
            else:
                data[name] = annotation.change(value)
                changed = True
        return content_type.model_validate(data) if changed else None
