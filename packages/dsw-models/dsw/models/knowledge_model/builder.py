"""Fluent construction of knowledge models.

Example::

    builder = KnowledgeModelBuilder()
    fair = builder.phase('Before submitting the proposal')
    findability = builder.metric('Findability', abbreviation='F')
    chapter = builder.chapter('Data description')
    question = chapter.options_question('Will you reuse existing data?', required_phase=fair)
    question.answer('Yes', metric_measures=[(findability, 1.0, 1.0)]) \\
        .value_question('Which data?')
    question.answer('No')
    km = builder.build()                     # flat.KnowledgeModel
    events = builder.to_events()             # events creating it

Every ``add`` method returns a handle of the new entity; handles (or UUIDs) are accepted wherever
another entity is referenced. UUIDs come from ``uuid_factory`` unless passed explicitly.
"""
from __future__ import annotations

import typing
import uuid as uuid_module
from collections.abc import Mapping

from ..common import KeyValue
from ..versions import KM_METAMODEL_VERSION
from . import flat
from .common import MetricMeasure
from .diff import decompile
from .package import KnowledgeModelBundle, KnowledgeModelBundlePackage


if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from datetime import datetime
    from uuid import UUID

    from .common import QuestionValidation, QuestionValueType
    from .events import Event


AnnotationsInput = typing.Union['Mapping[str, str]', 'Iterable[KeyValue]', None]


def _annotations(value: AnnotationsInput) -> list[KeyValue]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        mapping = typing.cast('Mapping[str, str]', value)
        return [KeyValue(key=key, value=item) for key, item in mapping.items()]
    return list(value)


class Handle:
    """A created entity; pass it wherever the builder expects a reference."""

    __slots__ = ('builder', 'uuid')

    def __init__(self, builder: KnowledgeModelBuilder, uuid: UUID):
        self.builder = builder
        self.uuid = uuid

    def __repr__(self) -> str:
        return f'<{type(self).__name__} {self.uuid}>'

    @property
    def entity(self) -> typing.Any:
        return self.builder.entity(self.uuid)


Reference = typing.Union[Handle, 'UUID']


def _uuid(reference: Reference) -> UUID:
    return reference.uuid if isinstance(reference, Handle) else reference


def _optional_uuid(reference: Reference | None) -> UUID | None:
    return None if reference is None else _uuid(reference)


class _QuestionContainer(Handle):
    """Something questions can be added to: a chapter, an answer or a list question."""

    __slots__ = ()

    def _question_list(self) -> list[UUID]:
        raise NotImplementedError

    def _add_question(self, question_type: type, title: str, *, uuid: UUID | None, text: str | None,
                      required_phase: Reference | None, tags: Iterable[Reference],
                      annotations: AnnotationsInput, **fields: typing.Any) -> typing.Any:
        question = question_type(
            uuid=self.builder._new_uuid(uuid),  # noqa: SLF001
            title=title,
            text=text,
            required_phase_uuid=_optional_uuid(required_phase),
            tag_uuids=[_uuid(tag) for tag in tags],
            annotations=_annotations(annotations),
            **fields,
        )
        self.builder.km.entities.questions[question.uuid] = question
        self._question_list().append(question.uuid)
        return _QUESTION_HANDLES[question_type](self.builder, question.uuid)

    def options_question(self, title: str, *, uuid: UUID | None = None, text: str | None = None,
                         required_phase: Reference | None = None, tags: Iterable[Reference] = (),
                         annotations: AnnotationsInput = None) -> OptionsQuestionHandle:
        return self._add_question(flat.OptionsQuestion, title, uuid=uuid, text=text,
                                  required_phase=required_phase, tags=tags, annotations=annotations)

    def multi_choice_question(self, title: str, *, uuid: UUID | None = None,
                              text: str | None = None, required_phase: Reference | None = None,
                              tags: Iterable[Reference] = (),
                              annotations: AnnotationsInput = None) -> MultiChoiceQuestionHandle:
        return self._add_question(flat.MultiChoiceQuestion, title, uuid=uuid, text=text,
                                  required_phase=required_phase, tags=tags, annotations=annotations)

    def list_question(self, title: str, *, uuid: UUID | None = None, text: str | None = None,
                      required_phase: Reference | None = None, tags: Iterable[Reference] = (),
                      annotations: AnnotationsInput = None) -> ListQuestionHandle:
        return self._add_question(flat.ListQuestion, title, uuid=uuid, text=text,
                                  required_phase=required_phase, tags=tags, annotations=annotations)

    def value_question(self, title: str, *, uuid: UUID | None = None, text: str | None = None,
                       value_type: QuestionValueType = 'StringQuestionValueType',
                       validations: Iterable[QuestionValidation] = (),
                       required_phase: Reference | None = None, tags: Iterable[Reference] = (),
                       annotations: AnnotationsInput = None) -> QuestionHandle:
        return self._add_question(flat.ValueQuestion, title, uuid=uuid, text=text,
                                  required_phase=required_phase, tags=tags, annotations=annotations,
                                  value_type=value_type, validations=list(validations))

    def integration_question(self, title: str, *, integration: Reference,
                             variables: Mapping[str, str] | None = None, uuid: UUID | None = None,
                             text: str | None = None, required_phase: Reference | None = None,
                             tags: Iterable[Reference] = (),
                             annotations: AnnotationsInput = None) -> QuestionHandle:
        return self._add_question(flat.IntegrationQuestion, title, uuid=uuid, text=text,
                                  required_phase=required_phase, tags=tags, annotations=annotations,
                                  integration_uuid=_uuid(integration),
                                  variables=dict(variables or {}))

    def item_select_question(self, title: str, *, list_question: Reference | None = None,
                             uuid: UUID | None = None, text: str | None = None,
                             required_phase: Reference | None = None,
                             tags: Iterable[Reference] = (),
                             annotations: AnnotationsInput = None) -> QuestionHandle:
        return self._add_question(flat.ItemSelectQuestion, title, uuid=uuid, text=text,
                                  required_phase=required_phase, tags=tags, annotations=annotations,
                                  list_question_uuid=_optional_uuid(list_question))

    def file_question(self, title: str, *, max_size: int | None = None,
                      file_types: str | None = None, uuid: UUID | None = None,
                      text: str | None = None, required_phase: Reference | None = None,
                      tags: Iterable[Reference] = (),
                      annotations: AnnotationsInput = None) -> QuestionHandle:
        return self._add_question(flat.FileQuestion, title, uuid=uuid, text=text,
                                  required_phase=required_phase, tags=tags, annotations=annotations,
                                  max_size=max_size, file_types=file_types)


class ChapterHandle(_QuestionContainer):
    __slots__ = ()

    def _question_list(self) -> list[UUID]:
        return self.builder.km.entities.chapters[self.uuid].question_uuids


class AnswerHandle(_QuestionContainer):
    """Questions added to an answer are its follow-up questions."""

    __slots__ = ()

    def _question_list(self) -> list[UUID]:
        return self.builder.km.entities.answers[self.uuid].follow_up_uuids


class QuestionHandle(Handle):
    __slots__ = ()

    def _question(self) -> typing.Any:
        return self.builder.km.entities.questions[self.uuid]

    def expert(self, name: str, email: str, *, uuid: UUID | None = None,
               annotations: AnnotationsInput = None) -> Handle:
        expert = flat.Expert(uuid=self.builder._new_uuid(uuid), name=name, email=email,  # noqa: SLF001
                             annotations=_annotations(annotations))
        self.builder.km.entities.experts[expert.uuid] = expert
        self._question().expert_uuids.append(expert.uuid)
        return Handle(self.builder, expert.uuid)

    def _reference(self, reference: typing.Any) -> Handle:
        self.builder.km.entities.references[reference.uuid] = reference
        self._question().reference_uuids.append(reference.uuid)
        return Handle(self.builder, reference.uuid)

    def url_reference(self, url: str, label: str, *, uuid: UUID | None = None,
                      annotations: AnnotationsInput = None) -> Handle:
        return self._reference(flat.URLReference(
            uuid=self.builder._new_uuid(uuid), url=url, label=label,  # noqa: SLF001
            annotations=_annotations(annotations)))

    def cross_reference(self, target: Reference, description: str, *, uuid: UUID | None = None,
                        annotations: AnnotationsInput = None) -> Handle:
        return self._reference(flat.CrossReference(
            uuid=self.builder._new_uuid(uuid), target_uuid=_uuid(target),  # noqa: SLF001
            description=description, annotations=_annotations(annotations)))

    def resource_page_reference(self, page: Reference, *, uuid: UUID | None = None,
                                annotations: AnnotationsInput = None) -> Handle:
        return self._reference(flat.ResourcePageReference(
            uuid=self.builder._new_uuid(uuid), resource_page_uuid=_optional_uuid(page),  # noqa: SLF001
            annotations=_annotations(annotations)))


class OptionsQuestionHandle(QuestionHandle):
    __slots__ = ()

    def answer(self, label: str, *, advice: str | None = None,
               metric_measures: Iterable[tuple[Reference, float, float]] = (),
               uuid: UUID | None = None, annotations: AnnotationsInput = None) -> AnswerHandle:
        """Add an answer; ``metric_measures`` are ``(metric, measure, weight)`` triples."""
        answer = flat.Answer(
            uuid=self.builder._new_uuid(uuid),  # noqa: SLF001
            label=label,
            advice=advice,
            annotations=_annotations(annotations),
            metric_measures=[
                MetricMeasure(metric_uuid=_uuid(metric), measure=measure, weight=weight)
                for metric, measure, weight in metric_measures],
        )
        self.builder.km.entities.answers[answer.uuid] = answer
        self._question().answer_uuids.append(answer.uuid)
        return AnswerHandle(self.builder, answer.uuid)


class MultiChoiceQuestionHandle(QuestionHandle):
    __slots__ = ()

    def choice(self, label: str, *, uuid: UUID | None = None,
               annotations: AnnotationsInput = None) -> Handle:
        choice = flat.Choice(uuid=self.builder._new_uuid(uuid), label=label,  # noqa: SLF001
                             annotations=_annotations(annotations))
        self.builder.km.entities.choices[choice.uuid] = choice
        self._question().choice_uuids.append(choice.uuid)
        return Handle(self.builder, choice.uuid)


class ListQuestionHandle(QuestionHandle, _QuestionContainer):
    """Questions added to a list question are its item questions."""

    __slots__ = ()

    def _question_list(self) -> list[UUID]:
        return self._question().item_template_question_uuids


class ResourceCollectionHandle(Handle):
    __slots__ = ()

    def page(self, title: str, content: str, *, uuid: UUID | None = None,
             annotations: AnnotationsInput = None) -> Handle:
        page = flat.ResourcePage(uuid=self.builder._new_uuid(uuid), title=title,  # noqa: SLF001
                                 content=content, annotations=_annotations(annotations))
        self.builder.km.entities.resource_pages[page.uuid] = page
        self.builder.km.entities.resource_collections[self.uuid].resource_page_uuids.append(page.uuid)
        return Handle(self.builder, page.uuid)


_QUESTION_HANDLES: dict[type, type] = {
    flat.OptionsQuestion: OptionsQuestionHandle,
    flat.MultiChoiceQuestion: MultiChoiceQuestionHandle,
    flat.ListQuestion: ListQuestionHandle,
    flat.ValueQuestion: QuestionHandle,
    flat.IntegrationQuestion: QuestionHandle,
    flat.ItemSelectQuestion: QuestionHandle,
    flat.FileQuestion: QuestionHandle,
}


class KnowledgeModelBuilder:

    def __init__(self, *, uuid: UUID | None = None, annotations: AnnotationsInput = None,
                 uuid_factory: Callable[[], UUID] = uuid_module.uuid4):
        self.uuid_factory = uuid_factory
        self.km = flat.KnowledgeModel(uuid=uuid or uuid_factory(),
                                      annotations=_annotations(annotations))

    def _new_uuid(self, uuid: UUID | None) -> UUID:
        return uuid if uuid is not None else self.uuid_factory()

    def entity(self, uuid: UUID) -> typing.Any:
        for name in type(self.km.entities).model_fields:
            entities = getattr(self.km.entities, name)
            if uuid in entities:
                return entities[uuid]
        raise KeyError(uuid)

    # top-level entities
    def chapter(self, title: str, *, text: str | None = None, uuid: UUID | None = None,
                annotations: AnnotationsInput = None) -> ChapterHandle:
        chapter = flat.Chapter(uuid=self._new_uuid(uuid), title=title, text=text,
                               annotations=_annotations(annotations))
        self.km.entities.chapters[chapter.uuid] = chapter
        self.km.chapter_uuids.append(chapter.uuid)
        return ChapterHandle(self, chapter.uuid)

    def tag(self, name: str, *, color: str = '#0033aa', description: str | None = None,
            uuid: UUID | None = None, annotations: AnnotationsInput = None) -> Handle:
        tag = flat.Tag(uuid=self._new_uuid(uuid), name=name, color=color, description=description,
                       annotations=_annotations(annotations))
        self.km.entities.tags[tag.uuid] = tag
        self.km.tag_uuids.append(tag.uuid)
        return Handle(self, tag.uuid)

    def metric(self, title: str, *, abbreviation: str | None = None,
               description: str | None = None, uuid: UUID | None = None,
               annotations: AnnotationsInput = None) -> Handle:
        metric = flat.Metric(uuid=self._new_uuid(uuid), title=title, abbreviation=abbreviation,
                             description=description, annotations=_annotations(annotations))
        self.km.entities.metrics[metric.uuid] = metric
        self.km.metric_uuids.append(metric.uuid)
        return Handle(self, metric.uuid)

    def phase(self, title: str, *, description: str | None = None, uuid: UUID | None = None,
              annotations: AnnotationsInput = None) -> Handle:
        phase = flat.Phase(uuid=self._new_uuid(uuid), title=title, description=description,
                           annotations=_annotations(annotations))
        self.km.entities.phases[phase.uuid] = phase
        self.km.phase_uuids.append(phase.uuid)
        return Handle(self, phase.uuid)

    def _integration(self, integration: typing.Any) -> Handle:
        self.km.entities.integrations[integration.uuid] = integration
        self.km.integration_uuids.append(integration.uuid)
        return Handle(self, integration.uuid)

    def api_integration(self, name: str, *, request_url: str, response_item_template: str,
                        request_method: str = 'GET', variables: Iterable[str] = (),
                        request_headers: AnnotationsInput = None, request_body: str | None = None,
                        response_list_field: str | None = None,
                        response_item_template_for_selection: str | None = None,
                        allow_custom_reply: bool = True, request_allow_empty_search: bool = True,
                        uuid: UUID | None = None, annotations: AnnotationsInput = None) -> Handle:
        return self._integration(flat.ApiIntegration(
            uuid=self._new_uuid(uuid), name=name, variables=list(variables),
            allow_custom_reply=allow_custom_reply, request_method=request_method,
            request_url=request_url, request_headers=_annotations(request_headers),
            request_body=request_body, request_allow_empty_search=request_allow_empty_search,
            response_list_field=response_list_field, response_item_template=response_item_template,
            response_item_template_for_selection=response_item_template_for_selection,
            test_q='', annotations=_annotations(annotations)))

    def plugin_integration(self, name: str, *, plugin_uuid: UUID, plugin_integration_id: str,
                           settings: typing.Any = None, uuid: UUID | None = None,
                           annotations: AnnotationsInput = None) -> Handle:
        return self._integration(flat.PluginIntegration(
            uuid=self._new_uuid(uuid), name=name, plugin_uuid=plugin_uuid,
            plugin_integration_id=plugin_integration_id,
            plugin_integration_settings=settings if settings is not None else {},
            annotations=_annotations(annotations)))

    def resource_collection(self, title: str, *, uuid: UUID | None = None,
                            annotations: AnnotationsInput = None) -> ResourceCollectionHandle:
        collection = flat.ResourceCollection(uuid=self._new_uuid(uuid), title=title,
                                             annotations=_annotations(annotations))
        self.km.entities.resource_collections[collection.uuid] = collection
        self.km.resource_collection_uuids.append(collection.uuid)
        return ResourceCollectionHandle(self, collection.uuid)

    # results
    def build(self) -> flat.KnowledgeModel:
        """A validated copy of the knowledge model built so far."""
        return flat.KnowledgeModel.model_validate(self.km.model_dump())

    def to_events(self, *, clock: Callable[[], datetime] | None = None) -> list[Event]:
        kwargs: dict[str, typing.Any] = {'uuid_factory': self.uuid_factory}
        if clock is not None:
            kwargs['clock'] = clock
        return decompile(self.build(), **kwargs)

    def to_bundle(self, *, organization_id: str, km_id: str, version: str, name: str,
                  description: str = '', readme: str = '', license: str = '',
                  language: str = 'en', previous_package_id: str | None = None,
                  clock: Callable[[], datetime] | None = None) -> KnowledgeModelBundle:
        """A ``.km`` bundle with a single package holding :meth:`to_events`."""
        events = self.to_events(clock=clock)
        package_id = f'{organization_id}:{km_id}:{version}'
        package = KnowledgeModelBundlePackage(
            id=package_id, name=name, organization_id=organization_id, km_id=km_id,
            version=version, metamodel_version=KM_METAMODEL_VERSION, description=description,
            readme=readme, license=license, language=language,
            previous_package_id=previous_package_id, events=events,
            created_at=events[0].created_at,
        )
        return KnowledgeModelBundle(id=package_id, name=name, organization_id=organization_id,
                                    km_id=km_id, version=version,
                                    metamodel_version=KM_METAMODEL_VERSION, packages=[package])
