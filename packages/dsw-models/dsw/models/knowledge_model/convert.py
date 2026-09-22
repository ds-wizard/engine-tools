"""Conversions between knowledge model representations."""
from __future__ import annotations

import typing
import uuid as uuid_module

from ..errors import ModelsError
from . import flat, graph, tree


if typing.TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID


class ConversionError(ModelsError):
    """The source cannot be expressed in the target representation."""


def flat_to_graph(km: flat.KnowledgeModel) -> graph.KnowledgeModel:
    return graph.KnowledgeModel(km)


_COLLECTIONS = ('chapters', 'questions', 'answers', 'choices', 'experts', 'references',
                'integrations', 'tags', 'metrics', 'phases', 'resource_collections',
                'resource_pages')


def prune_unreachable(km: flat.KnowledgeModel) -> flat.KnowledgeModel:
    """Copy of ``km`` without entities unreachable from its top-level lists.

    The backend keeps such entities (e.g. choices of a deleted question) but nothing shows or
    uses them. UUID lists are left untouched, dangling references included.
    """
    reachable = graph.KnowledgeModel(km).reachable
    pruned = km.model_copy(deep=True)
    for name in _COLLECTIONS:
        entities = getattr(pruned.entities, name)
        for uuid in [uuid for uuid in entities if uuid not in reachable]:
            del entities[uuid]
    return pruned


# flat → tree
_TREE_QUESTIONS: dict[type, typing.Any] = {
    flat.OptionsQuestion: tree.OptionsQuestion,
    flat.MultiChoiceQuestion: tree.MultiChoiceQuestion,
    flat.ListQuestion: tree.ListQuestion,
    flat.ValueQuestion: tree.ValueQuestion,
    flat.IntegrationQuestion: tree.IntegrationQuestion,
    flat.ItemSelectQuestion: tree.ItemSelectQuestion,
    flat.FileQuestion: tree.FileQuestion,
}
_TREE_LEAVES: dict[type, typing.Any] = {
    flat.Expert: tree.Expert,
    flat.Choice: tree.Choice,
    flat.ResourcePageReference: tree.ResourcePageReference,
    flat.URLReference: tree.URLReference,
    flat.CrossReference: tree.CrossReference,
    flat.ApiIntegration: tree.ApiIntegration,
    flat.PluginIntegration: tree.PluginIntegration,
    flat.Tag: tree.Tag,
    flat.Metric: tree.Metric,
    flat.Phase: tree.Phase,
    flat.ResourcePage: tree.ResourcePage,
}
_QUESTION_CHILD_LISTS = ('answer_uuids', 'choice_uuids', 'item_template_question_uuids',
                         'expert_uuids', 'reference_uuids')


def flat_to_tree(km: flat.KnowledgeModel) -> tree.KnowledgeModel:
    """Nest the flat model following containment from the top-level lists.

    Entities not reachable from the top-level lists are dropped, an entity contained by more
    than one parent is placed under the first one only, and missing UUIDs are skipped.
    """
    return _FlatToTree(km).convert()


class _FlatToTree:

    def __init__(self, km: flat.KnowledgeModel):
        self.km = km
        self.entities = km.entities
        self.placed: set[UUID] = set()

    def convert(self) -> tree.KnowledgeModel:
        e = self.entities
        return tree.KnowledgeModel(
            uuid=self.km.uuid,
            annotations=self.km.annotations,
            chapters=[self._chapter(c) for c in self._take(e.chapters, self.km.chapter_uuids)],
            tags=self._leaves(e.tags, self.km.tag_uuids),
            integrations=self._leaves(e.integrations, self.km.integration_uuids),
            metrics=self._leaves(e.metrics, self.km.metric_uuids),
            phases=self._leaves(e.phases, self.km.phase_uuids),
            resource_collections=[
                tree.ResourceCollection(
                    uuid=rc.uuid,
                    annotations=rc.annotations,
                    title=rc.title,
                    resource_pages=self._leaves(e.resource_pages, rc.resource_page_uuids),
                )
                for rc in self._take(e.resource_collections, self.km.resource_collection_uuids)
            ],
        )

    def _take(self, entities: dict, uuids: list[UUID]) -> list:
        result = []
        for uuid in uuids:
            if uuid in self.placed or uuid not in entities:
                continue
            self.placed.add(uuid)
            result.append(entities[uuid])
        return result

    def _leaves(self, entities: dict, uuids: list[UUID]) -> list:
        return [_TREE_LEAVES[type(entity)].model_validate(entity, from_attributes=True)
                for entity in self._take(entities, uuids)]

    def _chapter(self, chapter: flat.Chapter) -> tree.Chapter:
        return tree.Chapter(
            uuid=chapter.uuid,
            annotations=chapter.annotations,
            title=chapter.title,
            text=chapter.text,
            questions=self._questions(chapter.question_uuids),
        )

    def _questions(self, uuids: list[UUID]) -> list:
        return [self._question(q) for q in self._take(self.entities.questions, uuids)]

    def _question(self, question: typing.Any) -> typing.Any:
        e = self.entities
        data = question.model_dump(by_alias=False, exclude=set(_QUESTION_CHILD_LISTS))
        data['experts'] = self._leaves(e.experts, question.expert_uuids)
        data['references'] = self._leaves(e.references, question.reference_uuids)
        if isinstance(question, flat.OptionsQuestion):
            answers = self._take(e.answers, question.answer_uuids)
            data['answers'] = [self._answer(answer) for answer in answers]
        elif isinstance(question, flat.MultiChoiceQuestion):
            data['choices'] = self._leaves(e.choices, question.choice_uuids)
        elif isinstance(question, flat.ListQuestion):
            data['item_template_questions'] = self._questions(question.item_template_question_uuids)
        return _TREE_QUESTIONS[type(question)].model_validate(data)

    def _answer(self, answer: flat.Answer) -> tree.Answer:
        return tree.Answer(
            uuid=answer.uuid,
            annotations=answer.annotations,
            label=answer.label,
            advice=answer.advice,
            metric_measures=answer.metric_measures,
            follow_up_questions=self._questions(answer.follow_up_uuids),
        )


# tree → flat
_FLAT_QUESTIONS: dict[type, typing.Any] = {
    tree_type: flat_type for flat_type, tree_type in _TREE_QUESTIONS.items()}
_FLAT_LEAVES: dict[type, typing.Any] = {
    tree_type: flat_type for flat_type, tree_type in _TREE_LEAVES.items()}


def tree_to_flat(
    km: tree.KnowledgeModel,
    *,
    uuid_factory: Callable[[], UUID] = uuid_module.uuid4,
) -> flat.KnowledgeModel:
    """Flatten a tree, assigning UUIDs from ``uuid_factory`` where they are missing.

    Raises :class:`ConversionError` if a UUID is used by more than one entity.
    """
    return _TreeToFlat(uuid_factory).convert(km)


class _TreeToFlat:

    def __init__(self, uuid_factory: Callable[[], UUID]):
        self.uuid_factory = uuid_factory
        self.entities = flat.KnowledgeModelEntities()
        self.used: set[UUID] = set()

    def _uuid(self, entity: typing.Any) -> UUID:
        uuid = entity.uuid if entity.uuid is not None else self.uuid_factory()
        if uuid in self.used:
            raise ConversionError(f'UUID {uuid} is used by more than one entity')
        self.used.add(uuid)
        return uuid

    def convert(self, km: tree.KnowledgeModel) -> flat.KnowledgeModel:
        e = self.entities
        return flat.KnowledgeModel(
            uuid=self._uuid(km),
            annotations=km.annotations,
            chapter_uuids=[self._chapter(chapter) for chapter in km.chapters],
            tag_uuids=[self._leaf(e.tags, tag) for tag in km.tags],
            integration_uuids=[self._leaf(e.integrations, i) for i in km.integrations],
            metric_uuids=[self._leaf(e.metrics, metric) for metric in km.metrics],
            phase_uuids=[self._leaf(e.phases, phase) for phase in km.phases],
            resource_collection_uuids=[self._collection(rc) for rc in km.resource_collections],
            entities=e,
        )

    def _leaf(self, target: dict, entity: typing.Any) -> UUID:
        uuid = self._uuid(entity)
        target[uuid] = _FLAT_LEAVES[type(entity)].model_validate(
            {**entity.model_dump(), 'uuid': uuid})
        return uuid

    def _chapter(self, chapter: tree.Chapter) -> UUID:
        uuid = self._uuid(chapter)
        self.entities.chapters[uuid] = flat.Chapter(
            uuid=uuid,
            annotations=chapter.annotations,
            title=chapter.title,
            text=chapter.text,
            question_uuids=[self._question(q) for q in chapter.questions],
        )
        return uuid

    def _question(self, question: typing.Any) -> UUID:
        uuid = self._uuid(question)
        e = self.entities
        data = question.model_dump(by_alias=False, exclude={
            'experts', 'references', 'answers', 'choices', 'item_template_questions'})
        data['uuid'] = uuid
        data['expert_uuids'] = [self._leaf(e.experts, expert) for expert in question.experts]
        data['reference_uuids'] = [self._leaf(e.references, ref) for ref in question.references]
        if isinstance(question, tree.OptionsQuestion):
            data['answer_uuids'] = [self._answer(answer) for answer in question.answers]
        elif isinstance(question, tree.MultiChoiceQuestion):
            data['choice_uuids'] = [self._leaf(e.choices, choice) for choice in question.choices]
        elif isinstance(question, tree.ListQuestion):
            data['item_template_question_uuids'] = [
                self._question(item) for item in question.item_template_questions]
        self.entities.questions[uuid] = _FLAT_QUESTIONS[type(question)].model_validate(data)
        return uuid

    def _answer(self, answer: tree.Answer) -> UUID:
        uuid = self._uuid(answer)
        self.entities.answers[uuid] = flat.Answer(
            uuid=uuid,
            annotations=answer.annotations,
            label=answer.label,
            advice=answer.advice,
            metric_measures=answer.metric_measures,
            follow_up_uuids=[self._question(q) for q in answer.follow_up_questions],
        )
        return uuid

    def _collection(self, collection: tree.ResourceCollection) -> UUID:
        uuid = self._uuid(collection)
        self.entities.resource_collections[uuid] = flat.ResourceCollection(
            uuid=uuid,
            annotations=collection.annotations,
            title=collection.title,
            resource_page_uuids=[self._leaf(self.entities.resource_pages, page)
                                 for page in collection.resource_pages],
        )
        return uuid
