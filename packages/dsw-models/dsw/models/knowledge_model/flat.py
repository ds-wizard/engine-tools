"""Compiled knowledge model as the backend serializes it: entity maps plus ordered UUID lists."""
from __future__ import annotations

import typing
from uuid import UUID

import pydantic

from ..common import Annotations, BaseModel, JsonValue, KeyValue
from .common import MetricMeasure, QuestionValidation, QuestionValueType, TypeHintExchange


class Entity(BaseModel):
    uuid: UUID
    annotations: Annotations = pydantic.Field(default_factory=list)


class Chapter(Entity):
    title: str
    text: str | None = None
    question_uuids: list[UUID] = pydantic.Field(default_factory=list)


class QuestionBase(Entity):
    title: str
    text: str | None = None
    required_phase_uuid: UUID | None = None
    tag_uuids: list[UUID] = pydantic.Field(default_factory=list)
    expert_uuids: list[UUID] = pydantic.Field(default_factory=list)
    reference_uuids: list[UUID] = pydantic.Field(default_factory=list)


class OptionsQuestion(QuestionBase):
    question_type: typing.Literal['OptionsQuestion'] = 'OptionsQuestion'
    answer_uuids: list[UUID] = pydantic.Field(default_factory=list)


class MultiChoiceQuestion(QuestionBase):
    question_type: typing.Literal['MultiChoiceQuestion'] = 'MultiChoiceQuestion'
    choice_uuids: list[UUID] = pydantic.Field(default_factory=list)


class ListQuestion(QuestionBase):
    question_type: typing.Literal['ListQuestion'] = 'ListQuestion'
    item_template_question_uuids: list[UUID] = pydantic.Field(default_factory=list)


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


class Answer(Entity):
    label: str
    advice: str | None = None
    follow_up_uuids: list[UUID] = pydantic.Field(default_factory=list)
    metric_measures: list[MetricMeasure] = pydantic.Field(default_factory=list)


class Choice(Entity):
    label: str


class Expert(Entity):
    name: str
    email: str


class ResourcePageReference(Entity):
    reference_type: typing.Literal['ResourcePageReference'] = 'ResourcePageReference'
    resource_page_uuid: UUID | None = None


class URLReference(Entity):
    reference_type: typing.Literal['URLReference'] = 'URLReference'
    url: str
    label: str


class CrossReference(Entity):
    reference_type: typing.Literal['CrossReference'] = 'CrossReference'
    target_uuid: UUID
    description: str


Reference = typing.Annotated[
    ResourcePageReference | URLReference | CrossReference,
    pydantic.Field(discriminator='reference_type'),
]


class ApiIntegration(Entity):
    integration_type: typing.Literal['ApiIntegration'] = 'ApiIntegration'
    name: str
    variables: list[str] = pydantic.Field(default_factory=list)
    allow_custom_reply: bool
    request_method: str
    request_url: str
    request_headers: list[KeyValue] = pydantic.Field(default_factory=list)
    request_body: str | None = None
    request_allow_empty_search: bool
    response_list_field: str | None = None
    response_item_template: str
    response_item_template_for_selection: str | None = None
    test_q: str
    test_variables: dict[str, str] = pydantic.Field(default_factory=dict)
    test_response: TypeHintExchange | None = None


class PluginIntegration(Entity):
    integration_type: typing.Literal['PluginIntegration'] = 'PluginIntegration'
    name: str
    plugin_uuid: UUID
    plugin_integration_id: str
    plugin_integration_settings: JsonValue


Integration = typing.Annotated[
    ApiIntegration | PluginIntegration,
    pydantic.Field(discriminator='integration_type'),
]


class Tag(Entity):
    name: str
    description: str | None = None
    color: str


class Metric(Entity):
    title: str
    abbreviation: str | None = None
    description: str | None = None


class Phase(Entity):
    title: str
    description: str | None = None


class ResourceCollection(Entity):
    title: str
    resource_page_uuids: list[UUID] = pydantic.Field(default_factory=list)


class ResourcePage(Entity):
    title: str
    content: str


class KnowledgeModelEntities(BaseModel):
    chapters: dict[UUID, Chapter] = pydantic.Field(default_factory=dict)
    questions: dict[UUID, Question] = pydantic.Field(default_factory=dict)
    answers: dict[UUID, Answer] = pydantic.Field(default_factory=dict)
    choices: dict[UUID, Choice] = pydantic.Field(default_factory=dict)
    experts: dict[UUID, Expert] = pydantic.Field(default_factory=dict)
    references: dict[UUID, Reference] = pydantic.Field(default_factory=dict)
    integrations: dict[UUID, Integration] = pydantic.Field(default_factory=dict)
    tags: dict[UUID, Tag] = pydantic.Field(default_factory=dict)
    metrics: dict[UUID, Metric] = pydantic.Field(default_factory=dict)
    phases: dict[UUID, Phase] = pydantic.Field(default_factory=dict)
    resource_collections: dict[UUID, ResourceCollection] = pydantic.Field(default_factory=dict)
    resource_pages: dict[UUID, ResourcePage] = pydantic.Field(default_factory=dict)


class KnowledgeModel(Entity):
    chapter_uuids: list[UUID] = pydantic.Field(default_factory=list)
    tag_uuids: list[UUID] = pydantic.Field(default_factory=list)
    integration_uuids: list[UUID] = pydantic.Field(default_factory=list)
    metric_uuids: list[UUID] = pydantic.Field(default_factory=list)
    phase_uuids: list[UUID] = pydantic.Field(default_factory=list)
    resource_collection_uuids: list[UUID] = pydantic.Field(default_factory=list)
    entities: KnowledgeModelEntities = pydantic.Field(default_factory=KnowledgeModelEntities)
