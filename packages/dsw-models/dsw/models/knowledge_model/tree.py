"""Nested knowledge model for authoring by hand or by tools.

Containment is expressed by nesting (chapters hold questions, answers hold follow-up
questions …) instead of UUID lists, and UUIDs are optional: :func:`.convert.tree_to_flat`
assigns missing ones. Only entities referenced from elsewhere (tags, phases, integrations,
metrics, list questions of item-select questions, cross-reference targets, resource pages)
need an explicit UUID so the reference can name them.
"""
from __future__ import annotations

import typing
from uuid import UUID

import pydantic

from ..common import Annotations, BaseModel
from . import flat
from .common import MetricMeasure, QuestionValidation, QuestionValueType


class Entity(BaseModel):
    uuid: UUID | None = None
    annotations: Annotations = pydantic.Field(default_factory=list)


class Expert(flat.Expert):
    uuid: UUID | None = None


class ResourcePageReference(flat.ResourcePageReference):
    uuid: UUID | None = None


class URLReference(flat.URLReference):
    uuid: UUID | None = None


class CrossReference(flat.CrossReference):
    uuid: UUID | None = None


Reference = typing.Annotated[
    ResourcePageReference | URLReference | CrossReference,
    pydantic.Field(discriminator='reference_type'),
]


class QuestionBase(Entity):
    title: str
    text: str | None = None
    required_phase_uuid: UUID | None = None
    tag_uuids: list[UUID] = pydantic.Field(default_factory=list)
    experts: list[Expert] = pydantic.Field(default_factory=list)
    references: list[Reference] = pydantic.Field(default_factory=list)


class Answer(Entity):
    label: str
    advice: str | None = None
    follow_up_questions: list[Question] = pydantic.Field(default_factory=list)
    metric_measures: list[MetricMeasure] = pydantic.Field(default_factory=list)


class Choice(flat.Choice):
    uuid: UUID | None = None


class OptionsQuestion(QuestionBase):
    question_type: typing.Literal['OptionsQuestion'] = 'OptionsQuestion'
    answers: list[Answer] = pydantic.Field(default_factory=list)


class MultiChoiceQuestion(QuestionBase):
    question_type: typing.Literal['MultiChoiceQuestion'] = 'MultiChoiceQuestion'
    choices: list[Choice] = pydantic.Field(default_factory=list)


class ListQuestion(QuestionBase):
    question_type: typing.Literal['ListQuestion'] = 'ListQuestion'
    item_template_questions: list[Question] = pydantic.Field(default_factory=list)


class ValueQuestion(QuestionBase):
    question_type: typing.Literal['ValueQuestion'] = 'ValueQuestion'
    value_type: QuestionValueType = 'StringQuestionValueType'
    validations: list[QuestionValidation] = pydantic.Field(default_factory=list)


class IntegrationQuestion(QuestionBase):
    question_type: typing.Literal['IntegrationQuestion'] = 'IntegrationQuestion'
    integration_uuid: UUID
    variables: dict[str, str] = pydantic.Field(default_factory=dict)


class ItemSelectQuestion(QuestionBase):
    question_type: typing.Literal['ItemSelectQuestion'] = 'ItemSelectQuestion'
    list_question_uuid: UUID | None = None


class FileQuestion(QuestionBase):
    question_type: typing.Literal['FileQuestion'] = 'FileQuestion'
    max_size: int | None = None
    file_types: str | None = None


Question = typing.Annotated[
    OptionsQuestion
    | MultiChoiceQuestion
    | ListQuestion
    | ValueQuestion
    | IntegrationQuestion
    | ItemSelectQuestion
    | FileQuestion,
    pydantic.Field(discriminator='question_type'),
]


class Chapter(Entity):
    title: str
    text: str | None = None
    questions: list[Question] = pydantic.Field(default_factory=list)


class ApiIntegration(flat.ApiIntegration):
    uuid: UUID | None = None


class PluginIntegration(flat.PluginIntegration):
    uuid: UUID | None = None


Integration = typing.Annotated[
    ApiIntegration | PluginIntegration,
    pydantic.Field(discriminator='integration_type'),
]


class Tag(flat.Tag):
    uuid: UUID | None = None


class Metric(flat.Metric):
    uuid: UUID | None = None


class Phase(flat.Phase):
    uuid: UUID | None = None


class ResourcePage(flat.ResourcePage):
    uuid: UUID | None = None


class ResourceCollection(Entity):
    title: str
    resource_pages: list[ResourcePage] = pydantic.Field(default_factory=list)


class KnowledgeModel(Entity):
    chapters: list[Chapter] = pydantic.Field(default_factory=list)
    tags: list[Tag] = pydantic.Field(default_factory=list)
    integrations: list[Integration] = pydantic.Field(default_factory=list)
    metrics: list[Metric] = pydantic.Field(default_factory=list)
    phases: list[Phase] = pydantic.Field(default_factory=list)
    resource_collections: list[ResourceCollection] = pydantic.Field(default_factory=list)
