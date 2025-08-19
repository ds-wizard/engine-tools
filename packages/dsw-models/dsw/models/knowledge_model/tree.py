from uuid import UUID

import pydantic

from .common import (BaseModel, TAnnotations, TQuestionValueType,
                     QuestionValidation, TypeHintExchange)


class BaseKMTreeEntity(BaseModel):
    uuid: UUID
    annotations: TAnnotations


class MetricMeasure(BaseModel):
    metric: 'Metric'
    measure: float = pydantic.Field(ge=0.0, le=1.0)
    weight: float = pydantic.Field(ge=0.0, le=1.0)


class Answer(BaseKMTreeEntity):
    label: str
    advice: str | None
    metric_measures: list[MetricMeasure]
    follow_ups: list['Question']


class Choice(BaseKMTreeEntity):
    label: str


class Expert(BaseKMTreeEntity):
    name: str
    email: str


class Tag(BaseKMTreeEntity):
    title: str
    description: str | None
    color: str


class Phase(BaseKMTreeEntity):
    name: str
    description: str | None


class Metric(BaseKMTreeEntity):
    title: str
    abbreviation: str | None
    description: str | None


class ResourcePage(BaseKMTreeEntity):
    title: str
    content: str


class ResourceCollection(BaseKMTreeEntity):
    title: str
    resource_pages: list[ResourcePage]


class Integration(BaseKMTreeEntity):
    name: str
    variables: list[str]


class ApiIntegration(Integration):
    allow_custom_reply: bool
    request_method: str
    request_url: str
    request_body: str | None
    request_allow_empty_search: bool
    response_list_field: str
    response_item_template: str
    response_item_template_for_selection: str | None
    test_q: str
    test_variables: dict[str, str]
    test_response: TypeHintExchange | None


class ApiLegacyIntegration(Integration):
    id: str
    logo: str | None
    request_method: str
    request_url: str
    request_body: str | None
    request_empty_search: bool
    response_list_field: str | None
    response_item_id: str | None
    response_item_template: str | None
    item_url: str | None


class WidgetIntegration(Integration):
    id: str
    logo: str | None
    widget_url: str
    item_url: str | None


class Reference(BaseKMTreeEntity):
    pass


class ResourcePageReference(Reference):
    resource_page: ResourcePage


class URLReference(Reference):
    url: str
    label: str


class CrossReference(Reference):
    target: BaseKMTreeEntity
    description: str


class Question(BaseKMTreeEntity):
    title: str
    text: str
    required_phase: Phase | None
    experts: list[Expert]
    references: list[Reference]
    tags: list[Tag]


class OptionsQuestion(Question):
    answers: list[Answer]


class ChoiceQuestion(Question):
    choices: list[Choice]


class ListQuestion(Question):
    item_template_questions: list[Question]


class ValueQuestion(Question):
    value_type: TQuestionValueType
    validations: list[QuestionValidation]


class IntegrationQuestion(Question):
    integration: Integration
    variables: dict[str, str]


class ItemSelectQuestion(Question):
    list_question: ListQuestion


class FileQuestion(Question):
    max_size: int
    file_types: str | None


class Chapter(BaseKMTreeEntity):
    title: str
    description: str
    questions: list[Question]


class KnowledgeModel(BaseKMTreeEntity):
    chapters: list[Chapter]
    tags: list[Tag]
    phases: list[Phase]
    metrics: list[Metric]
    integrations: list[Integration]
    resource_collections: list[ResourceCollection]
