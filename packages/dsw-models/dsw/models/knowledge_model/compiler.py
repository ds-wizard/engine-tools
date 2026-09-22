"""Compile knowledge model events into a flat knowledge model.

A faithful port of the backend compiler (``Wizard.Service.KnowledgeModel.Compiler``), including
its quirks, so the result equals what the backend would produce:

* an event whose entity or parent does not exist is ignored (an added question is still
  stored, just not linked),
* removing a UUID from a parent list removes its first occurrence only, except for moves,
* editing a question, reference or integration with a different type converts the entity and
  resets type-specific fields,
* deletes cascade to contained entities; a deleted integration turns its questions into value
  questions, a deleted tag, metric or phase is removed from where it is used,
* dangling cross-references, item-select list questions and resource page references are kept.

Pass ``on_ignored`` to learn about events that had no or only partial effect.
"""
from __future__ import annotations

import copy
import typing

from ..common import NULL_UUID
from . import events as ev
from . import flat


if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from uuid import UUID


OnIgnored = typing.Callable[[ev.Event, str], None]
_Handler = typing.Callable[[ev.Event, typing.Any], None]


def compile_events(
    events: Iterable[ev.Event],
    base: flat.KnowledgeModel | None = None,
    *,
    on_ignored: OnIgnored | None = None,
) -> flat.KnowledgeModel:
    """Apply ``events`` in order to a copy of ``base`` (or an empty knowledge model)."""
    km = base.model_copy(deep=True) if base is not None else flat.KnowledgeModel(uuid=NULL_UUID)
    compiler = Compiler(km, on_ignored=on_ignored)
    for event in events:
        compiler.apply(event)
    return compiler.km


_ENTITY_TYPES: dict[type, type] = {
    ev.AddChapterEventContent: flat.Chapter,
    ev.AddOptionsQuestionEventContent: flat.OptionsQuestion,
    ev.AddMultiChoiceQuestionEventContent: flat.MultiChoiceQuestion,
    ev.AddListQuestionEventContent: flat.ListQuestion,
    ev.AddValueQuestionEventContent: flat.ValueQuestion,
    ev.AddIntegrationQuestionEventContent: flat.IntegrationQuestion,
    ev.AddItemSelectQuestionEventContent: flat.ItemSelectQuestion,
    ev.AddFileQuestionEventContent: flat.FileQuestion,
    ev.AddAnswerEventContent: flat.Answer,
    ev.AddChoiceEventContent: flat.Choice,
    ev.AddExpertEventContent: flat.Expert,
    ev.AddResourcePageReferenceEventContent: flat.ResourcePageReference,
    ev.AddURLReferenceEventContent: flat.URLReference,
    ev.AddCrossReferenceEventContent: flat.CrossReference,
    ev.AddApiIntegrationEventContent: flat.ApiIntegration,
    ev.AddPluginIntegrationEventContent: flat.PluginIntegration,
    ev.AddTagEventContent: flat.Tag,
    ev.AddMetricEventContent: flat.Metric,
    ev.AddPhaseEventContent: flat.Phase,
    ev.AddResourceCollectionEventContent: flat.ResourceCollection,
    ev.AddResourcePageEventContent: flat.ResourcePage,
    ev.EditOptionsQuestionEventContent: flat.OptionsQuestion,
    ev.EditMultiChoiceQuestionEventContent: flat.MultiChoiceQuestion,
    ev.EditListQuestionEventContent: flat.ListQuestion,
    ev.EditValueQuestionEventContent: flat.ValueQuestion,
    ev.EditIntegrationQuestionEventContent: flat.IntegrationQuestion,
    ev.EditItemSelectQuestionEventContent: flat.ItemSelectQuestion,
    ev.EditFileQuestionEventContent: flat.FileQuestion,
    ev.EditResourcePageReferenceEventContent: flat.ResourcePageReference,
    ev.EditURLReferenceEventContent: flat.URLReference,
    ev.EditCrossReferenceEventContent: flat.CrossReference,
    ev.EditApiIntegrationEventContent: flat.ApiIntegration,
    ev.EditPluginIntegrationEventContent: flat.PluginIntegration,
}

_CONTENT_ONLY_FIELDS = frozenset({'event_type'})
_QUESTION_SHARED_FIELDS = ('title', 'text', 'required_phase_uuid', 'tag_uuids', 'reference_uuids',
                           'expert_uuids', 'annotations')

#: Question list field holding each kind of child entity
_QUESTION_CHILD_FIELD = {
    'answers': ('answer_uuids', flat.OptionsQuestion),
    'choices': ('choice_uuids', flat.MultiChoiceQuestion),
    'experts': ('expert_uuids', flat.QuestionBase),
    'references': ('reference_uuids', flat.QuestionBase),
    'questions': ('item_template_question_uuids', flat.ListQuestion),
}


def _remove_first(items: list[UUID], uuid: UUID) -> None:
    if uuid in items:
        items.remove(uuid)


def _question_children(question: typing.Any, kind: str) -> list[UUID] | None:
    """The question's child list of ``kind``, ``None`` if its type has none (backend lens)."""
    field, question_type = _QUESTION_CHILD_FIELD[kind]
    return getattr(question, field) if isinstance(question, question_type) else None


class Compiler:
    """Incremental compiler: :meth:`apply` events one by one to :attr:`km` (mutated in place)."""

    def __init__(self, km: flat.KnowledgeModel, *, on_ignored: OnIgnored | None = None):
        self.km = km
        self.on_ignored = on_ignored
        self.handlers: dict[type, _Handler] = {
            ev.AddKnowledgeModelEventContent: self._add_knowledge_model,
            ev.EditKnowledgeModelEventContent: self._edit_knowledge_model,
            ev.AddChapterEventContent: self._add_root('chapters', 'chapter_uuids'),
            ev.DeleteChapterEventContent: self._delete_chapter,
            ev.DeleteQuestionEventContent: self._delete_question,
            ev.AddAnswerEventContent: self._add_to_question('answers', 'answers'),
            ev.DeleteAnswerEventContent: self._delete_from_question('answers', 'answers'),
            ev.AddChoiceEventContent: self._add_to_question('choices', 'choices'),
            ev.DeleteChoiceEventContent: self._delete_from_question('choices', 'choices'),
            ev.AddExpertEventContent: self._add_to_question('experts', 'experts'),
            ev.DeleteExpertEventContent: self._delete_from_question('experts', 'experts'),
            ev.DeleteReferenceEventContent: self._delete_from_question('references', 'references'),
            ev.DeleteIntegrationEventContent: self._delete_integration,
            ev.AddTagEventContent: self._add_root('tags', 'tag_uuids'),
            ev.DeleteTagEventContent: self._delete_tag,
            ev.AddMetricEventContent: self._add_root('metrics', 'metric_uuids'),
            ev.DeleteMetricEventContent: self._delete_metric,
            ev.AddPhaseEventContent: self._add_root('phases', 'phase_uuids'),
            ev.DeletePhaseEventContent: self._delete_phase,
            ev.AddResourceCollectionEventContent: self._add_root(
                'resource_collections', 'resource_collection_uuids'),
            ev.DeleteResourceCollectionEventContent: self._delete_resource_collection,
            ev.AddResourcePageEventContent: self._add_resource_page,
            ev.DeleteResourcePageEventContent: self._delete_resource_page,
            ev.MoveQuestionEventContent: self._move_question,
            ev.MoveAnswerEventContent: self._move_in_questions('answers'),
            ev.MoveChoiceEventContent: self._move_in_questions('choices'),
            ev.MoveExpertEventContent: self._move_in_questions('experts'),
            ev.MoveReferenceEventContent: self._move_in_questions('references'),
        }
        for content_type in (
            ev.AddOptionsQuestionEventContent, ev.AddMultiChoiceQuestionEventContent,
            ev.AddListQuestionEventContent, ev.AddValueQuestionEventContent,
            ev.AddIntegrationQuestionEventContent, ev.AddItemSelectQuestionEventContent,
            ev.AddFileQuestionEventContent,
        ):
            self.handlers[content_type] = self._add_question
        for content_type in (
            ev.AddResourcePageReferenceEventContent, ev.AddURLReferenceEventContent,
            ev.AddCrossReferenceEventContent,
        ):
            self.handlers[content_type] = self._add_to_question('references', 'references')
        for content_type in (ev.AddApiIntegrationEventContent, ev.AddPluginIntegrationEventContent):
            self.handlers[content_type] = self._add_root('integrations', 'integration_uuids')
        edits = {
            'chapters': (ev.EditChapterEventContent,),
            'questions': (
                ev.EditOptionsQuestionEventContent, ev.EditMultiChoiceQuestionEventContent,
                ev.EditListQuestionEventContent, ev.EditValueQuestionEventContent,
                ev.EditIntegrationQuestionEventContent, ev.EditItemSelectQuestionEventContent,
                ev.EditFileQuestionEventContent,
            ),
            'answers': (ev.EditAnswerEventContent,),
            'choices': (ev.EditChoiceEventContent,),
            'experts': (ev.EditExpertEventContent,),
            'references': (
                ev.EditResourcePageReferenceEventContent, ev.EditURLReferenceEventContent,
                ev.EditCrossReferenceEventContent,
            ),
            'integrations': (
                ev.EditApiIntegrationEventContent, ev.EditPluginIntegrationEventContent,
            ),
            'tags': (ev.EditTagEventContent,),
            'metrics': (ev.EditMetricEventContent,),
            'phases': (ev.EditPhaseEventContent,),
            'resource_collections': (ev.EditResourceCollectionEventContent,),
            'resource_pages': (ev.EditResourcePageEventContent,),
        }
        for collection, content_types in edits.items():
            for content_type in content_types:
                self.handlers[content_type] = self._edit(collection)

    # helpers
    @property
    def entities(self) -> flat.KnowledgeModelEntities:
        return self.km.entities

    def apply(self, event: ev.Event) -> None:
        self.handlers[type(event.content)](event, event.content)

    def _ignored(self, event: ev.Event, reason: str) -> None:
        if self.on_ignored is not None:
            self.on_ignored(event, reason)

    @staticmethod
    def _create(event: ev.Event, content: typing.Any) -> typing.Any:
        data = {name: copy.deepcopy(getattr(content, name))
                for name in type(content).model_fields if name not in _CONTENT_ONLY_FIELDS}
        return _ENTITY_TYPES[type(content)](uuid=event.entity_uuid, **data)

    @staticmethod
    def _apply_changes(entity: typing.Any, content: typing.Any) -> None:
        for name in type(content).model_fields:
            field = getattr(content, name)
            if isinstance(field, ev.EditEventField) and field.changed:
                setattr(entity, name, copy.deepcopy(field.value))

    # knowledge model
    def _add_knowledge_model(self, event: ev.Event, content: typing.Any) -> None:
        self.km = flat.KnowledgeModel(uuid=event.entity_uuid,
                                      annotations=copy.deepcopy(content.annotations))

    def _edit_knowledge_model(self, event: ev.Event, content: typing.Any) -> None:
        self._apply_changes(self.km, content)

    # generic add / edit
    def _add_root(self, collection: str, uuid_list: str) -> _Handler:
        def handler(event: ev.Event, content: typing.Any) -> None:
            getattr(self.km, uuid_list).append(event.entity_uuid)
            getattr(self.entities, collection)[event.entity_uuid] = self._create(event, content)
        return handler

    def _edit(self, collection: str) -> _Handler:
        def handler(event: ev.Event, content: typing.Any) -> None:
            entities = getattr(self.entities, collection)
            entity = entities.get(event.entity_uuid)
            if entity is None:
                self._ignored(event, 'entity not found')
            else:
                target_type = _ENTITY_TYPES.get(type(content))
                if target_type is not None and type(entity) is not target_type:
                    entity = convert_entity(entity, target_type)
                    entities[event.entity_uuid] = entity
                self._apply_changes(entity, content)
            # the backend updates questions even when the integration itself is missing
            if isinstance(content, ev.EditApiIntegrationEventContent) and content.variables.changed:
                self._update_integration_variables(event.entity_uuid, content.variables.value or [])
        return handler

    def _update_integration_variables(self, integration_uuid: UUID, variables: list[str]) -> None:
        for question in self.entities.questions.values():
            if (isinstance(question, flat.IntegrationQuestion)
                    and question.integration_uuid == integration_uuid):
                question.variables = {name: question.variables.get(name, '') for name in variables}

    # chapters and questions
    def _delete_chapter(self, event: ev.Event, content: typing.Any) -> None:
        _remove_first(self.km.chapter_uuids, event.entity_uuid)
        if not self._cascade_chapter(event.entity_uuid):
            self._ignored(event, 'entity not found')

    def _add_question(self, event: ev.Event, content: typing.Any) -> None:
        linked = self._edit_question_parent(
            event.parent_uuid, lambda items: items.append(event.entity_uuid))
        if not linked:
            self._ignored(event, 'parent not found, question stored unlinked')
        self.entities.questions[event.entity_uuid] = self._create(event, content)

    def _delete_question(self, event: ev.Event, content: typing.Any) -> None:
        self._edit_question_parent(
            event.parent_uuid, lambda items: _remove_first(items, event.entity_uuid))
        if not self._cascade_question(event.entity_uuid):
            self._ignored(event, 'entity not found')

    def _edit_question_parent(
        self, parent_uuid: UUID, change: Callable[[list[UUID]], None],
    ) -> bool:
        """Apply ``change`` to the question list of a chapter, list question or answer."""
        e = self.entities
        if parent_uuid in e.chapters:
            change(e.chapters[parent_uuid].question_uuids)
        elif parent_uuid in e.questions:
            children = _question_children(e.questions[parent_uuid], 'questions')
            if children is not None:
                change(children)
        elif parent_uuid in e.answers:
            change(e.answers[parent_uuid].follow_up_uuids)
        else:
            return False
        return True

    # children of questions
    def _add_to_question(self, kind: str, collection: str) -> _Handler:
        def handler(event: ev.Event, content: typing.Any) -> None:
            parent = self.entities.questions.get(event.parent_uuid)
            if parent is None:
                self._ignored(event, 'parent not found')
                return
            children = _question_children(parent, kind)
            if children is not None:
                children.append(event.entity_uuid)
            getattr(self.entities, collection)[event.entity_uuid] = self._create(event, content)
        return handler

    def _delete_from_question(self, kind: str, collection: str) -> _Handler:
        def handler(event: ev.Event, content: typing.Any) -> None:
            if kind == 'answers':
                found = self._cascade_answer(event.entity_uuid)
            else:
                found = getattr(self.entities, collection).pop(event.entity_uuid, None) is not None
            parent = self.entities.questions.get(event.parent_uuid)
            if parent is not None:
                children = _question_children(parent, kind)
                if children is not None:
                    _remove_first(children, event.entity_uuid)
            if not found:
                self._ignored(event, 'entity not found')
        return handler

    # cascades (backend Modifier.Delete)
    def _cascade_chapter(self, uuid: UUID) -> bool:
        chapter = self.entities.chapters.get(uuid)
        if chapter is None:
            return False
        for question_uuid in list(chapter.question_uuids):
            self._cascade_question(question_uuid)
        self.entities.chapters.pop(uuid, None)
        return True

    def _cascade_question(self, uuid: UUID) -> bool:
        question = self.entities.questions.get(uuid)
        if question is None:
            return False
        for expert_uuid in question.expert_uuids:
            self.entities.experts.pop(expert_uuid, None)
        for reference_uuid in question.reference_uuids:
            self.entities.references.pop(reference_uuid, None)
        for answer_uuid in list(_question_children(question, 'answers') or []):
            self._cascade_answer(answer_uuid)
        for item_uuid in list(_question_children(question, 'questions') or []):
            self._cascade_question(item_uuid)
        self.entities.questions.pop(uuid, None)
        return True

    def _cascade_answer(self, uuid: UUID) -> bool:
        answer = self.entities.answers.get(uuid)
        if answer is None:
            return False
        for question_uuid in list(answer.follow_up_uuids):
            self._cascade_question(question_uuid)
        self.entities.answers.pop(uuid, None)
        return True

    # root entities with usages
    def _delete_root(self, event: ev.Event, collection: str, uuid_list: str) -> None:
        _remove_first(getattr(self.km, uuid_list), event.entity_uuid)
        if getattr(self.entities, collection).pop(event.entity_uuid, None) is None:
            self._ignored(event, 'entity not found')

    def _delete_integration(self, event: ev.Event, content: typing.Any) -> None:
        questions = self.entities.questions
        for uuid, question in list(questions.items()):
            if (isinstance(question, flat.IntegrationQuestion)
                    and question.integration_uuid == event.entity_uuid):
                questions[uuid] = convert_entity(question, flat.ValueQuestion)
        self._delete_root(event, 'integrations', 'integration_uuids')

    def _delete_tag(self, event: ev.Event, content: typing.Any) -> None:
        for question in self.entities.questions.values():
            _remove_first(question.tag_uuids, event.entity_uuid)
        self._delete_root(event, 'tags', 'tag_uuids')

    def _delete_metric(self, event: ev.Event, content: typing.Any) -> None:
        for answer in self.entities.answers.values():
            answer.metric_measures = [m for m in answer.metric_measures
                                      if m.metric_uuid != event.entity_uuid]
        self._delete_root(event, 'metrics', 'metric_uuids')

    def _delete_phase(self, event: ev.Event, content: typing.Any) -> None:
        for question in self.entities.questions.values():
            if question.required_phase_uuid == event.entity_uuid:
                question.required_phase_uuid = None
        self._delete_root(event, 'phases', 'phase_uuids')

    # resources
    def _delete_resource_collection(self, event: ev.Event, content: typing.Any) -> None:
        collection = self.entities.resource_collections.get(event.entity_uuid)
        if collection is not None:
            for page_uuid in collection.resource_page_uuids:
                self.entities.resource_pages.pop(page_uuid, None)
        self._delete_root(event, 'resource_collections', 'resource_collection_uuids')

    def _add_resource_page(self, event: ev.Event, content: typing.Any) -> None:
        parent = self.entities.resource_collections.get(event.parent_uuid)
        if parent is None:
            self._ignored(event, 'parent not found')
            return
        parent.resource_page_uuids.append(event.entity_uuid)
        self.entities.resource_pages[event.entity_uuid] = self._create(event, content)

    def _delete_resource_page(self, event: ev.Event, content: typing.Any) -> None:
        found = self.entities.resource_pages.pop(event.entity_uuid, None) is not None
        parent = self.entities.resource_collections.get(event.parent_uuid)
        if parent is not None:
            _remove_first(parent.resource_page_uuids, event.entity_uuid)
        if not found:
            self._ignored(event, 'entity not found')

    # moves: remove every occurrence from the old parent, then append to the new one
    def _move_question(self, event: ev.Event, content: ev.MoveEventContent) -> None:
        lists: list[tuple[UUID, list[UUID]]] = []
        lists.extend((c.uuid, c.question_uuids) for c in self.entities.chapters.values())
        for question in self.entities.questions.values():
            children = _question_children(question, 'questions')
            if children is not None:
                lists.append((question.uuid, children))
        lists.extend((a.uuid, a.follow_up_uuids) for a in self.entities.answers.values())
        self._move(event, content, lists)

    def _move_in_questions(self, kind: str) -> _Handler:
        def handler(event: ev.Event, content: ev.MoveEventContent) -> None:
            lists = []
            for question in self.entities.questions.values():
                children = _question_children(question, kind)
                if children is not None:
                    lists.append((question.uuid, children))
            self._move(event, content, lists)
        return handler

    def _move(self, event: ev.Event, content: ev.MoveEventContent,
              lists: list[tuple[UUID, list[UUID]]]) -> None:
        moved = False
        for owner_uuid, items in lists:
            if owner_uuid == event.parent_uuid:
                items[:] = [uuid for uuid in items if uuid != event.entity_uuid]
            if owner_uuid == content.target_uuid:
                items.append(event.entity_uuid)
                moved = True
        if not moved:
            self._ignored(event, 'target not found')


def convert_entity(entity: typing.Any, target_type: type) -> typing.Any:
    """Change the type of a question, reference or integration like the backend does."""
    if issubclass(target_type, flat.QuestionBase):
        data = {name: getattr(entity, name) for name in _QUESTION_SHARED_FIELDS}
        if target_type is flat.IntegrationQuestion:
            data['integration_uuid'] = NULL_UUID
        return target_type(uuid=entity.uuid, **data)
    if target_type is flat.URLReference:
        return target_type(uuid=entity.uuid, annotations=entity.annotations, url='', label='')
    if target_type is flat.CrossReference:
        return target_type(uuid=entity.uuid, annotations=entity.annotations,
                           target_uuid=NULL_UUID, description='')
    if target_type is flat.ResourcePageReference:
        return target_type(uuid=entity.uuid, annotations=entity.annotations)
    if target_type is flat.ApiIntegration:
        return target_type(uuid=entity.uuid, annotations=entity.annotations, name='',
                           allow_custom_reply=False, request_method='GET', request_url='',
                           request_allow_empty_search=False, response_item_template='', test_q='')
    if target_type is flat.PluginIntegration:
        return target_type(uuid=entity.uuid, annotations=entity.annotations, name=entity.name,
                           plugin_uuid=NULL_UUID, plugin_integration_id='',
                           plugin_integration_settings={})
    raise TypeError(f'Cannot convert {type(entity).__name__} to {target_type.__name__}')
