"""Read-only, navigable knowledge model built from :mod:`.flat`.

Every flat entity becomes a node. Nodes resolve UUID references to other nodes, know their
parent and expose the flat entity as ``entity``; unknown attributes are read from the entity,
so ``question.title`` works as well as ``question.entity.title``.

Containment (chapter → questions → answers → follow-up questions …) defines ``parent``.
References that are not containment (tags, integration, required phase, cross-reference
target …) are resolved but do not set a parent. UUIDs that are missing or point to the wrong
kind of entity are skipped and recorded in :attr:`KnowledgeModel.dangling`. An entity listed by
more than one parent keeps the first one in knowledge model order and the others are recorded
in :attr:`KnowledgeModel.shared`. A UUID used by entities of two collections is a node only for
the first collection (chapters, questions, answers … in that order); the pair is recorded in
:attr:`KnowledgeModel.collisions` and the other entity is left out.
"""
from __future__ import annotations

import collections
import dataclasses
import typing
from uuid import UUID

from . import flat


if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from ..common import KeyValue


@dataclasses.dataclass(frozen=True, slots=True)
class DanglingReference:
    """``source`` refers in ``field`` to ``target_uuid``, which is missing or of a wrong kind."""

    source: Node
    field: str
    target_uuid: UUID
    reason: typing.Literal['missing', 'wrong_type'] = 'missing'


class Node:
    __slots__ = ('entity', 'km', 'parent')

    kind: typing.ClassVar[str] = 'node'

    def __init__(self, entity: typing.Any, km: KnowledgeModel):
        self.entity = entity
        self.km = km
        self.parent: Node | None = None

    def __getattr__(self, name: str) -> typing.Any:
        if name.startswith('_'):
            raise AttributeError(name)
        try:
            return getattr(object.__getattribute__(self, 'entity'), name)
        except AttributeError:
            raise AttributeError(f'{type(self).__name__!r} has no attribute {name!r}') from None

    def __repr__(self) -> str:
        return f'<{type(self).__name__} {self.uuid}>'

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Node) and other.uuid == self.uuid and other.km is self.km

    def __hash__(self) -> int:
        return hash(self.uuid)

    @property
    def uuid(self) -> UUID:
        return self.entity.uuid

    @property
    def annotations(self) -> list[KeyValue]:
        return self.entity.annotations

    def annotation(self, key: str, default: str | None = None) -> str | None:
        """First value of annotation ``key``."""
        return next((item.value for item in self.annotations if item.key == key), default)

    def annotation_values(self, key: str) -> list[str]:
        return [item.value for item in self.annotations if item.key == key]

    @property
    def children(self) -> list[Node]:
        """Contained nodes in knowledge model order."""
        return []

    @property
    def ancestors(self) -> list[Node]:
        """Parents from the closest one up to the chapter (or collection)."""
        result: list[Node] = []
        node = self.parent
        while node is not None and node is not self and node not in result:
            result.append(node)
            node = node.parent
        return result

    @property
    def entity_path(self) -> tuple[UUID, ...]:
        """UUIDs from the top-level container down to this node.

        For questions this is the reply path without list item UUIDs; see
        :mod:`dsw.models.project.paths` for complete reply paths.
        """
        return (*(node.uuid for node in reversed(self.ancestors)), self.uuid)

    def _resolve(self, field: str, uuids: Iterable[UUID], expected: type[Node]) -> list:
        return [
            node for node in (self.km._resolve_one(self, field, uuid, expected)  # noqa: SLF001
                              for uuid in uuids)
            if node is not None
        ]

    def _resolve_optional(
        self, field: str, uuid: UUID | None, expected: type[Node],
    ) -> typing.Any:
        if uuid is None:
            return None
        return self.km._resolve_one(self, field, uuid, expected)  # noqa: SLF001

    def _link(self) -> None:
        """Resolve references once all nodes exist."""


class Chapter(Node):
    __slots__ = ('questions',)
    kind = 'chapter'
    entity: flat.Chapter

    def _link(self) -> None:
        self.questions: list[Question] = self._resolve(
            'questionUuids', self.entity.question_uuids, Question)

    @property
    def children(self) -> list[Node]:
        return list(self.questions)


class Question(Node):
    __slots__ = ('experts', 'references', 'required_phase', 'tags')
    kind = 'question'
    entity: flat.QuestionBase

    def _link(self) -> None:
        self.required_phase: Phase | None = self._resolve_optional(
            'requiredPhaseUuid', self.entity.required_phase_uuid, Phase)
        self.tags: list[Tag] = self._resolve('tagUuids', self.entity.tag_uuids, Tag)
        self.experts: list[Expert] = self._resolve(
            'expertUuids', self.entity.expert_uuids, Expert)
        self.references: list[Reference] = self._resolve(
            'referenceUuids', self.entity.reference_uuids, Reference)

    @property
    def question_type(self) -> str:
        return self.entity.question_type  # ty: ignore[unresolved-attribute]

    @property
    def children(self) -> list[Node]:
        return [*self.experts, *self.references]


class OptionsQuestion(Question):
    __slots__ = ('answers',)
    kind = 'options_question'
    entity: flat.OptionsQuestion

    def _link(self) -> None:
        super()._link()
        self.answers: list[Answer] = self._resolve(
            'answerUuids', self.entity.answer_uuids, Answer)

    @property
    def children(self) -> list[Node]:
        return [*self.answers, *super().children]


class MultiChoiceQuestion(Question):
    __slots__ = ('choices',)
    kind = 'multi_choice_question'
    entity: flat.MultiChoiceQuestion

    def _link(self) -> None:
        super()._link()
        self.choices: list[Choice] = self._resolve(
            'choiceUuids', self.entity.choice_uuids, Choice)

    @property
    def children(self) -> list[Node]:
        return [*self.choices, *super().children]


class ListQuestion(Question):
    __slots__ = ('item_template_questions',)
    kind = 'list_question'
    entity: flat.ListQuestion

    def _link(self) -> None:
        super()._link()
        self.item_template_questions: list[Question] = self._resolve(
            'itemTemplateQuestionUuids', self.entity.item_template_question_uuids, Question)

    @property
    def item_select_questions(self) -> list[ItemSelectQuestion]:
        """Questions selecting items of this list."""
        return self.km.item_select_questions_of(self)

    @property
    def children(self) -> list[Node]:
        return [*self.item_template_questions, *super().children]


class ValueQuestion(Question):
    __slots__ = ()
    kind = 'value_question'
    entity: flat.ValueQuestion


class IntegrationQuestion(Question):
    __slots__ = ('integration',)
    kind = 'integration_question'
    entity: flat.IntegrationQuestion

    def _link(self) -> None:
        super()._link()
        self.integration: Integration | None = self._resolve_optional(
            'integrationUuid', self.entity.integration_uuid, Integration)


class ItemSelectQuestion(Question):
    __slots__ = ('list_question',)
    kind = 'item_select_question'
    entity: flat.ItemSelectQuestion

    def _link(self) -> None:
        super()._link()
        self.list_question: ListQuestion | None = self._resolve_optional(
            'listQuestionUuid', self.entity.list_question_uuid, ListQuestion)


class FileQuestion(Question):
    __slots__ = ()
    kind = 'file_question'
    entity: flat.FileQuestion


class MetricMeasure:
    __slots__ = ('measure', 'metric', 'weight')

    def __init__(self, metric: Metric, measure: float, weight: float):
        self.metric = metric
        self.measure = measure
        self.weight = weight

    def __repr__(self) -> str:
        return f'<MetricMeasure {self.metric.uuid} {self.measure}×{self.weight}>'


class Answer(Node):
    __slots__ = ('follow_up_questions', 'metric_measures')
    kind = 'answer'
    entity: flat.Answer

    def _link(self) -> None:
        self.follow_up_questions: list[Question] = self._resolve(
            'followUpUuids', self.entity.follow_up_uuids, Question)
        self.metric_measures: list[MetricMeasure] = []
        for measure in self.entity.metric_measures:
            metric = self._resolve_optional('metricMeasures', measure.metric_uuid, Metric)
            if metric is not None:
                self.metric_measures.append(MetricMeasure(metric, measure.measure, measure.weight))

    @property
    def children(self) -> list[Node]:
        return list(self.follow_up_questions)


class Choice(Node):
    __slots__ = ()
    kind = 'choice'
    entity: flat.Choice


class Expert(Node):
    __slots__ = ()
    kind = 'expert'
    entity: flat.Expert


class Reference(Node):
    __slots__ = ()
    kind = 'reference'

    @property
    def reference_type(self) -> str:
        return self.entity.reference_type


class ResourcePageReference(Reference):
    __slots__ = ('resource_page',)
    kind = 'resource_page_reference'
    entity: flat.ResourcePageReference

    def _link(self) -> None:
        self.resource_page: ResourcePage | None = self._resolve_optional(
            'resourcePageUuid', self.entity.resource_page_uuid, ResourcePage)


class URLReference(Reference):
    __slots__ = ()
    kind = 'url_reference'
    entity: flat.URLReference


class CrossReference(Reference):
    __slots__ = ('target',)
    kind = 'cross_reference'
    entity: flat.CrossReference

    def _link(self) -> None:
        self.target: Node | None = self._resolve_optional(
            'targetUuid', self.entity.target_uuid, Node)


class Integration(Node):
    __slots__ = ()
    kind = 'integration'

    @property
    def integration_type(self) -> str:
        return self.entity.integration_type

    @property
    def questions(self) -> list[IntegrationQuestion]:
        """Questions using this integration."""
        return self.km.questions_using_integration(self)


class ApiIntegration(Integration):
    __slots__ = ()
    kind = 'api_integration'
    entity: flat.ApiIntegration


class PluginIntegration(Integration):
    __slots__ = ()
    kind = 'plugin_integration'
    entity: flat.PluginIntegration


class Tag(Node):
    __slots__ = ()
    kind = 'tag'
    entity: flat.Tag

    @property
    def questions(self) -> list[Question]:
        return self.km.questions_with_tag(self)


class Metric(Node):
    __slots__ = ()
    kind = 'metric'
    entity: flat.Metric


class Phase(Node):
    __slots__ = ()
    kind = 'phase'
    entity: flat.Phase

    @property
    def order(self) -> int | None:
        """0-based position in the knowledge model phase list, ``None`` if not listed."""
        return self.km.phase_order.get(self.uuid)

    @property
    def questions(self) -> list[Question]:
        """Questions whose required phase is this one."""
        return self.km.questions_requiring_phase(self)


class ResourceCollection(Node):
    __slots__ = ('resource_pages',)
    kind = 'resource_collection'
    entity: flat.ResourceCollection

    def _link(self) -> None:
        self.resource_pages: list[ResourcePage] = self._resolve(
            'resourcePageUuids', self.entity.resource_page_uuids, ResourcePage)

    @property
    def children(self) -> list[Node]:
        return list(self.resource_pages)


class ResourcePage(Node):
    __slots__ = ()
    kind = 'resource_page'
    entity: flat.ResourcePage

    @property
    def references(self) -> list[ResourcePageReference]:
        return self.km.references_to(self, ResourcePageReference)


_QUESTION_NODES: dict[type, type[Question]] = {
    flat.OptionsQuestion: OptionsQuestion,
    flat.MultiChoiceQuestion: MultiChoiceQuestion,
    flat.ListQuestion: ListQuestion,
    flat.ValueQuestion: ValueQuestion,
    flat.IntegrationQuestion: IntegrationQuestion,
    flat.ItemSelectQuestion: ItemSelectQuestion,
    flat.FileQuestion: FileQuestion,
}
_REFERENCE_NODES: dict[type, type[Reference]] = {
    flat.ResourcePageReference: ResourcePageReference,
    flat.URLReference: URLReference,
    flat.CrossReference: CrossReference,
}
_INTEGRATION_NODES: dict[type, type[Integration]] = {
    flat.ApiIntegration: ApiIntegration,
    flat.PluginIntegration: PluginIntegration,
}


class KnowledgeModel:
    """Navigable view of a :class:`flat.KnowledgeModel`. Do not mutate the flat model after."""

    def __init__(self, km: flat.KnowledgeModel):
        self.flat = km
        entities = km.entities
        self._nodes: dict[UUID, Node] = {}
        self.dangling: list[DanglingReference] = []
        self.shared: list[tuple[Node, Node]] = []
        #: (kept node, left-out node) of entities sharing a UUID across collections
        self.collisions: list[tuple[Node, Node]] = []

        self.chapters_by_uuid = self._add(entities.chapters, lambda _: Chapter)
        self.questions = self._add(entities.questions, lambda e: _QUESTION_NODES[type(e)])
        self.answers = self._add(entities.answers, lambda _: Answer)
        self.choices = self._add(entities.choices, lambda _: Choice)
        self.experts = self._add(entities.experts, lambda _: Expert)
        self.references = self._add(entities.references, lambda e: _REFERENCE_NODES[type(e)])
        self.integrations_by_uuid = self._add(
            entities.integrations, lambda e: _INTEGRATION_NODES[type(e)])
        self.tags_by_uuid = self._add(entities.tags, lambda _: Tag)
        self.metrics_by_uuid = self._add(entities.metrics, lambda _: Metric)
        self.phases_by_uuid = self._add(entities.phases, lambda _: Phase)
        self.resource_collections_by_uuid = self._add(
            entities.resource_collections, lambda _: ResourceCollection)
        self.resource_pages = self._add(entities.resource_pages, lambda _: ResourcePage)

        for node in self._nodes.values():
            node._link()  # noqa: SLF001

        root = _RootNode(self)
        self.chapters: list[Chapter] = root._resolve('chapterUuids', km.chapter_uuids, Chapter)  # noqa: SLF001
        self.tags: list[Tag] = root._resolve('tagUuids', km.tag_uuids, Tag)  # noqa: SLF001
        self.integrations: list[Integration] = root._resolve(  # noqa: SLF001
            'integrationUuids', km.integration_uuids, Integration)
        self.metrics: list[Metric] = root._resolve('metricUuids', km.metric_uuids, Metric)  # noqa: SLF001
        self.phases: list[Phase] = root._resolve('phaseUuids', km.phase_uuids, Phase)  # noqa: SLF001
        self.resource_collections: list[ResourceCollection] = root._resolve(  # noqa: SLF001
            'resourceCollectionUuids', km.resource_collection_uuids, ResourceCollection)
        self._assign_parents()
        self.phase_order = {phase.uuid: index for index, phase in enumerate(self.phases)}
        self._reverse: dict[tuple[str, UUID], list[Node]] | None = None

    # construction
    def _add[N: Node](self, entities: dict[UUID, typing.Any], node_type) -> dict[UUID, N]:
        result: dict[UUID, N] = {}
        for uuid, entity in entities.items():
            node = node_type(entity)(entity, self)
            existing = self._nodes.get(uuid)
            if existing is not None:
                self.collisions.append((existing, node))
                continue
            result[uuid] = node
            self._nodes[uuid] = node
        return result

    def _resolve_one(
        self, source: Node, field: str, uuid: UUID, expected: type[Node],
    ) -> Node | None:
        node = self._nodes.get(uuid)
        if node is None:
            self.dangling.append(DanglingReference(source, field, uuid))
            return None
        if not isinstance(node, expected):
            self.dangling.append(DanglingReference(source, field, uuid, 'wrong_type'))
            return None
        return node

    def _assign_parents(self) -> None:
        """Set parents by first occurrence in depth-first order from the roots, then elsewhere."""
        roots = {id(node) for node in self.roots}
        visited: set[int] = set()

        def walk(start: Node) -> None:
            stack: list[tuple[Node, Node | None]] = [(start, None)]
            while stack:
                node, parent = stack.pop()
                if id(node) in visited or (parent is not None and id(node) in roots):
                    if parent is not None and node.parent is not parent:
                        self.shared.append((node, parent))
                    continue
                visited.add(id(node))
                if parent is not None:
                    node.parent = parent
                stack.extend((child, node) for child in reversed(node.children))

        for root in self.roots:
            walk(root)
        for node in self._nodes.values():
            if id(node) not in visited:
                walk(node)

    # lookup
    def __getitem__(self, uuid: UUID) -> Node:
        return self._nodes[uuid]

    def __contains__(self, uuid: object) -> bool:
        return uuid in self._nodes

    def __len__(self) -> int:
        return len(self._nodes)

    def get(self, uuid: UUID | str | None) -> Node | None:
        if uuid is None:
            return None
        return self._nodes.get(uuid if isinstance(uuid, UUID) else UUID(uuid))

    @property
    def uuid(self) -> UUID:
        return self.flat.uuid

    @property
    def annotations(self) -> list[KeyValue]:
        return self.flat.annotations

    @property
    def nodes(self) -> Iterator[Node]:
        """All nodes, reachable or not, in entity map order."""
        return iter(self._nodes.values())

    @property
    def roots(self) -> list[Node]:
        """Top-level nodes in knowledge model order."""
        return [*self.chapters, *self.tags, *self.integrations, *self.metrics, *self.phases,
                *self.resource_collections]

    @property
    def reachable(self) -> set[UUID]:
        seen: set[UUID] = set()
        stack: list[Node] = list(reversed(self.roots))
        while stack:
            node = stack.pop()
            if node.uuid in seen:
                continue
            seen.add(node.uuid)
            stack.extend(reversed(node.children))
        return seen

    @property
    def unreachable(self) -> list[Node]:
        """Entities not reachable from the top-level lists (the backend keeps but ignores them)."""
        reachable = self.reachable
        return [node for node in self._nodes.values() if node.uuid not in reachable]

    # reverse indexes
    def _reverse_index(self) -> dict[tuple[str, UUID], list[Node]]:
        if self._reverse is None:
            index: dict[tuple[str, UUID], list[Node]] = collections.defaultdict(list)
            for question in self.questions.values():
                for tag in question.tags:
                    index['tag', tag.uuid].append(question)
                if question.required_phase is not None:
                    index['phase', question.required_phase.uuid].append(question)
                if isinstance(question, IntegrationQuestion) and question.integration:
                    index['integration', question.integration.uuid].append(question)
                if isinstance(question, ItemSelectQuestion) and question.list_question:
                    index['list', question.list_question.uuid].append(question)
            for reference in self.references.values():
                if isinstance(reference, CrossReference) and reference.target is not None:
                    index['reference', reference.target.uuid].append(reference)
                if isinstance(reference, ResourcePageReference) and reference.resource_page:
                    index['reference', reference.resource_page.uuid].append(reference)
            self._reverse = dict(index)
        return self._reverse

    def _reverse_of(self, key: str, node: Node) -> list[typing.Any]:
        return list(self._reverse_index().get((key, node.uuid), []))

    def questions_with_tag(self, tag: Tag) -> list[Question]:
        return self._reverse_of('tag', tag)

    def questions_requiring_phase(self, phase: Phase) -> list[Question]:
        return self._reverse_of('phase', phase)

    def questions_using_integration(self, integration: Integration) -> list[IntegrationQuestion]:
        return self._reverse_of('integration', integration)

    def item_select_questions_of(self, question: ListQuestion) -> list[ItemSelectQuestion]:
        return self._reverse_of('list', question)

    def references_to(
        self, node: Node, kind: type[Reference] = Reference,
    ) -> list[typing.Any]:
        """Cross-references and resource page references pointing to ``node``."""
        return [reference for reference in self._reverse_of('reference', node)
                if isinstance(reference, kind)]


class _RootNode(Node):
    """Stand-in source for dangling references in the knowledge model's own UUID lists."""

    __slots__ = ()
    kind = 'knowledge_model'

    def __init__(self, km: KnowledgeModel):
        super().__init__(km.flat, km)
