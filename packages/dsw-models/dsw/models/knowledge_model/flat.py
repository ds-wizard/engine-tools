import typing
from uuid import UUID

import pydantic

from .common import (BaseModel, TAnnotations, TQuestionValueType, THeaders,
                     MetricMeasure, QuestionValidation, TypeHintExchange)


class BaseKMFlatEntity(BaseModel):
    uuid: UUID
    annotations: TAnnotations


class Answer(BaseKMFlatEntity):
    label: str
    advice: str | None
    metric_measures: list[MetricMeasure]
    follow_up_uuids: list[UUID]


class Chapter(BaseKMFlatEntity):
    title: str
    text: str | None
    question_uuids: list[UUID]


class Choice(BaseKMFlatEntity):
    label: str


class Expert(BaseKMFlatEntity):
    name: str
    email: str


class ApiIntegration(BaseKMFlatEntity):
    integration_type: typing.Literal['ApiIntegration'] = 'ApiIntegration'
    name: str
    variables: list[str]
    allow_custom_reply: bool
    request_method: str
    request_url: str
    request_headers: THeaders
    request_body: str | None
    request_allow_empty_search: bool
    response_list_field: str | None
    response_item_template: str
    response_item_template_for_selection: str | None
    test_q: str
    test_variables: dict[str, str]
    test_response: TypeHintExchange | None


class ApiLegacyIntegration(BaseKMFlatEntity):
    integration_type: typing.Literal['ApiLegacyIntegration'] = 'ApiLegacyIntegration'
    id: str
    name: str
    variables: list[str]
    logo: str | None
    request_method: str
    request_url: str
    request_headers: THeaders
    request_body: str | None
    request_empty_search: bool
    response_list_field: str | None
    response_item_id: str | None
    response_item_template: str | None
    item_url: str | None


class WidgetIntegration(BaseKMFlatEntity):
    integration_type: typing.Literal['WidgetIntegration'] = 'WidgetIntegration'
    id: str
    name: str
    variables: list[str]
    logo: str | None
    widget_url: str
    item_url: str | None


Integration = typing.Annotated[
    typing.Union[
        ApiIntegration,
        ApiLegacyIntegration,
        WidgetIntegration,
    ],
    pydantic.Field(discriminator='integration_type'),
]


class Metric(BaseKMFlatEntity):
    title: str
    abbreviation: str | None
    description: str | None


class Phase(BaseKMFlatEntity):
    title: str
    description: str | None


class QuestionBase(BaseKMFlatEntity):
    title: str
    text: str | None
    required_phase_uuid: UUID | None
    expert_uuids: list[UUID]
    reference_uuids: list[UUID]
    tag_uuids: list[UUID]


class OptionsQuestion(QuestionBase):
    question_type: typing.Literal['OptionsQuestion'] = 'OptionsQuestion'
    answer_uuids: list[UUID]


class MultiChoiceQuestion(QuestionBase):
    question_type: typing.Literal['MultiChoiceQuestion'] = 'MultiChoiceQuestion'
    choice_uuids: list[UUID]


class ListQuestion(QuestionBase):
    question_type: typing.Literal['ListQuestion'] = 'ListQuestion'
    item_template_question_uuids: list[UUID]


class ValueQuestion(QuestionBase):
    question_type: typing.Literal['ValueQuestion'] = 'ValueQuestion'
    value_type: TQuestionValueType
    validations: list[QuestionValidation]


class IntegrationQuestion(QuestionBase):
    question_type: typing.Literal['IntegrationQuestion'] = 'IntegrationQuestion'
    integration_uuid: UUID
    variables: dict[str, str]


class ItemSelectQuestion(QuestionBase):
    question_type: typing.Literal['ItemSelectQuestion'] = 'ItemSelectQuestion'
    list_question_uuid: UUID


class FileQuestion(QuestionBase):
    question_type: typing.Literal['FileQuestion'] = 'FileQuestion'
    max_size: int
    file_types: str | None


Question = typing.Annotated[
    typing.Union[
        OptionsQuestion,
        MultiChoiceQuestion,
        ListQuestion,
        ValueQuestion,
        IntegrationQuestion,
        ItemSelectQuestion,
        FileQuestion,
    ],
    pydantic.Field(discriminator='question_type'),
]


class ResourcePageReference(BaseKMFlatEntity):
    reference_type: typing.Literal['ResourcePageReference'] = 'ResourcePageReference'
    resource_page_uuid: UUID


class URLReference(BaseKMFlatEntity):
    reference_type: typing.Literal['URLReference'] = 'URLReference'
    url: str
    label: str


class CrossReference(BaseKMFlatEntity):
    reference_type: typing.Literal['CrossReference'] = 'CrossReference'
    target_uuid: UUID
    description: str


Reference = typing.Annotated[
    typing.Union[
        ResourcePageReference,
        URLReference,
        CrossReference,
    ],
    pydantic.Field(discriminator='reference_type'),
]


class ResourceCollection(BaseKMFlatEntity):
    title: str
    resource_page_uuids: list[UUID]


class ResourcePage(BaseKMFlatEntity):
    title: str
    content: str


class Tag(BaseKMFlatEntity):
    name: str
    description: str | None
    color: str


class KnowledgeModelEntities(BaseModel):
    answers: dict[UUID, Answer]
    chapters: dict[UUID, Chapter]
    choices: dict[UUID, Choice]
    experts: dict[UUID, Expert]
    integrations: dict[UUID, Integration]
    metrics: dict[UUID, Metric]
    phases: dict[UUID, Phase]
    questions: dict[UUID, Question]
    references: dict[UUID, Reference]
    resource_collections: dict[UUID, ResourceCollection]
    resource_pages: dict[UUID, ResourcePage]
    tags: dict[UUID, Tag]


class KnowledgeModel(BaseKMFlatEntity):
    entities: KnowledgeModelEntities
    chapter_uuids: list[UUID]
    integration_uuids: list[UUID]
    metric_uuids: list[UUID]
    phase_uuids: list[UUID]
    resource_collection_uuids: list[UUID]
    tag_uuids: list[UUID]
