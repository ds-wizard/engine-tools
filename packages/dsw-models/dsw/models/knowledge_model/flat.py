import typing
import uuid

import pydantic


class KeyValue(pydantic.BaseModel):
    key: str
    value: str


class MetricMeasure(pydantic.BaseModel):
    metric_uuid: uuid.UUID = pydantic.Field(alias='metricUuid')
    measure: float  # TODO: 0.0-1.0
    weight: float  # TODO: 0.0-1.0


QuestionValueType = typing.Literal[
    'StringQuestionValueType',
    'NumberQuestionValueType',
    'DateQuestionValueType',
    'DateTimeQuestionValueType',
    'TimeQuestionValueType',
    'TextQuestionValueType',
    'EmailQuestionValueType',
    'UrlQuestionValueType',
    'ColorQuestionValueType',
]


class MinLengthQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['MinLengthQuestionValidation'] = pydantic.Field(alias='type')
    value: int


class MaxLengthQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['MaxLengthQuestionValidation'] = pydantic.Field(alias='type')
    value: int


class RegexQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['RegexQuestionValidation'] = pydantic.Field(alias='type')
    value: str


class OrcidQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['OrcidQuestionValidation'] = pydantic.Field(alias='type')


class DoiQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['DoiQuestionValidation'] = pydantic.Field(alias='type')


class MinNumberQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['MinNumberQuestionValidation'] = pydantic.Field(alias='type')
    value: float


class MaxNumberQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['MaxNumberQuestionValidation'] = pydantic.Field(alias='type')
    value: float

class FromDateQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['FromDateQuestionValidation'] = pydantic.Field(alias='type')
    value: str  # ISO 8601 date string, e.g., '2023-10-01'


class ToDateQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['ToDateQuestionValidation'] = pydantic.Field(alias='type')
    value: str  # ISO 8601 date string, e.g., '2023-10-31'


class FromDateTimeQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['FromDateTimeQuestionValidation'] = pydantic.Field(alias='type')
    value: str  # ISO 8601 datetime string, e.g., '2023-10-01T12:00:00Z'


class ToDateTimeQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['ToDateTimeQuestionValidation'] = pydantic.Field(alias='type')
    value: str  # ISO 8601 datetime string, e.g., '2023


class FromTimeQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['FromTimeQuestionValidation'] = pydantic.Field(alias='type')
    value: str  # ISO 8601 time string, e.g., '12:00:00'


class ToTimeQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['ToTimeQuestionValidation'] = pydantic.Field(alias='type')
    value: str  # ISO 8601 time string, e.g., '13:00:00'


class DomainQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['DomainQuestionValidation'] = pydantic.Field(alias='type')
    value: str  # Domain name, e.g., 'example.com'


QuestionValidation = typing.Union[
    MinLengthQuestionValidation,
    MaxLengthQuestionValidation,
    RegexQuestionValidation,
    OrcidQuestionValidation,
    DoiQuestionValidation,
    MinNumberQuestionValidation,
    MaxNumberQuestionValidation,
    FromDateQuestionValidation,
    ToDateQuestionValidation,
    FromDateTimeQuestionValidation,
    ToDateTimeQuestionValidation,
    FromTimeQuestionValidation,
    ToTimeQuestionValidation,
    DomainQuestionValidation,
]


class KMFlatEntity(pydantic.BaseModel):
    uuid: uuid.UUID
    annotations: list[KeyValue] = pydantic.Field(default_factory=list)


class Answer(KMFlatEntity):
    label: str
    advice: str | None = None
    metric_measures: list[MetricMeasure] = pydantic.Field(default_factory=list, alias='metricMeasures')
    follow_up_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='followUpUuids')


class Chapter(KMFlatEntity):
    title: str
    text: str | None = None
    question_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='questionUuids')


class Choice(KMFlatEntity):
    label: str


class Expert(KMFlatEntity):
    name: str
    email: str


class ApiIntegration(KMFlatEntity):
    name: str
    variables: list[str] = pydantic.Field(default_factory=list)
    allow_custom_reply: bool = pydantic.Field(alias='allowCustomReply')
    request_method: typing.Literal['GET', 'POST'] = pydantic.Field(alias='requestMethod')
    request_url: str = pydantic.Field(alias='requestUrl')
    request_body: str | None = pydantic.Field(default=None, alias='requestBody')
    request_allow_empty_search: bool = pydantic.Field(alias='requestAllowEmptySearch')
    response_list_field: str = pydantic.Field(alias='responseListField')
    response_item_template: str = pydantic.Field(alias='responseItemTemplate')
    response_item_template_for_selection: str | None = pydantic.Field(default=None, alias='responseItemTemplateForSelection')
    test_q: str = pydantic.Field(alias='testQ')
    test_variables: dict[str, str] = pydantic.Field(default_factory=dict, alias='testVariables')
    test_response: str | None = pydantic.Field(default=None, alias='testResponse')  # TODO: nested


class ApiLegacyIntegration(KMFlatEntity):
    id: str
    name: str
    variables: list[str] = pydantic.Field(default_factory=list)
    logo: str | None = None
    request_method: str = pydantic.Field(alias='requestMethod')
    request_url: str = pydantic.Field(alias='requestUrl')
    request_body: str | None = pydantic.Field(default=None, alias='requestBody')
    request_empty_search: bool = pydantic.Field(alias='requestEmptySearch')
    response_list_field: str | None = pydantic.Field(alias='responseListField')
    response_item_id: str | None = pydantic.Field(alias='responseItemId')
    response_item_template: str | None = pydantic.Field(alias='responseItemTemplate')
    item_url: str | None = pydantic.Field(alias='itemUrl')


class WidgetIntegration(KMFlatEntity):
    id: str
    name: str
    variables: list[str] = pydantic.Field(default_factory=list)
    logo: str | None = None
    widget_url: str = pydantic.Field(alias='widgetUrl')
    item_url: str | None = pydantic.Field(alias='itemUrl')


Integration = typing.Union[ApiIntegration, ApiLegacyIntegration, WidgetIntegration]


class Metric(KMFlatEntity):
    title: str
    abbreviation: str | None = None
    description: str | None = None


class Phase(KMFlatEntity):
    name: str
    description: str | None = None
    color: str  # TODO: hex color code


class QuestionBase(KMFlatEntity):
    title: str
    text: str | None = None
    required_phase_uuid: uuid.UUID | None = pydantic.Field(default=None, alias='requiredPhaseUuid')
    expert_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='expertUuids')
    reference_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='referenceUuids')
    tag_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='tagUuids')


class OptionsQuestion(QuestionBase):
    question_type: typing.Literal['OptionsQuestion'] = pydantic.Field(alias='questionType')
    answer_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='answerUuids')


class MultiChoiceQuestion(QuestionBase):
    question_type: typing.Literal['MultiChoiceQuestion'] = pydantic.Field(alias='questionType')
    choices: list[Choice] = pydantic.Field(default_factory=list)


class ListQuestion(QuestionBase):
    question_type: typing.Literal['ListQuestion'] = pydantic.Field(alias='questionType')
    item_template_question_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='itemTemplateQuestionUuids')


class ValueQuestion(QuestionBase):
    question_type: typing.Literal['ValueQuestion'] = pydantic.Field(alias='questionType')
    value_type: QuestionValueType = pydantic.Field(alias='valueType')
    validations: list[QuestionValidation] = pydantic.Field(default_factory=list, alias='validations')


class IntegrationQuestion(QuestionBase):
    question_type: typing.Literal['IntegrationQuestion'] = pydantic.Field(alias='questionType')
    integration_uuid: uuid.UUID = pydantic.Field(alias='integrationUuid')
    variables: dict[str, str] = pydantic.Field(default_factory=dict)


class ItemSelectQuestion(QuestionBase):
    question_type: typing.Literal['ItemSelectQuestion'] = pydantic.Field(alias='questionType')
    list_question_uuid: uuid.UUID = pydantic.Field(alias='listQuestionUuid')


class FileQuestion(QuestionBase):
    max_size: int = pydantic.Field(alias='maxSize')  # in bytes
    file_types: str | None = pydantic.Field(default=None, alias='fileTypes')  # e.g., 'image/png,image/jpeg'


Question = typing.Union[OptionsQuestion, MultiChoiceQuestion, ListQuestion, ValueQuestion,
                        IntegrationQuestion, ItemSelectQuestion, FileQuestion]


class ResourcePageReference(KMFlatEntity):
    reference_type: typing.Literal['ResourcePageReference'] = pydantic.Field(alias='referenceType')
    resource_page_uuid: uuid.UUID = pydantic.Field(alias='resourcePageUuid')


class URLReference(KMFlatEntity):
    reference_type: typing.Literal['URLReference'] = pydantic.Field(alias='referenceType')
    label: str
    url: str


class CrossReference(KMFlatEntity):
    reference_type: typing.Literal['CrossReference'] = pydantic.Field(alias='referenceType')
    target_uuid: uuid.UUID = pydantic.Field(alias='targetUuid')
    description: str

Reference = typing.Union[ResourcePageReference, URLReference, CrossReference]


class ResourceCollection(KMFlatEntity):
    title: str
    resource_page_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='resourcePageUuids')


class ResourcePage(KMFlatEntity):
    title: str
    content: str


class Tag(KMFlatEntity):
    title: str
    description: str | None = None


class KnowledgeModelEntities(pydantic.BaseModel):
    answers: list[Answer] = pydantic.Field(default_factory=list)
    chapters: list[Chapter] = pydantic.Field(default_factory=list)
    choices: list[Choice] = pydantic.Field(default_factory=list)
    experts: list[Expert] = pydantic.Field(default_factory=list)
    integrations: list[Integration] = pydantic.Field(default_factory=list)
    metrics: list[Metric] = pydantic.Field(default_factory=list)
    phases: list[Phase] = pydantic.Field(default_factory=list)
    questions: list[Question] = pydantic.Field(default_factory=list)
    references: list[Reference] = pydantic.Field(default_factory=list)
    resource_collections: list[ResourceCollection] = pydantic.Field(default_factory=list, alias='resourceCollections')
    resource_pages: list[ResourcePage] = pydantic.Field(default_factory=list, alias='resourcePages')
    tags: list[Tag] = pydantic.Field(default_factory=list)


class KnowledgeModel(KMFlatEntity):
    entities: KnowledgeModelEntities = pydantic.Field(default_factory=KnowledgeModelEntities)
    chapter_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='chapterUuids')
    tag_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='tagUuids')
    metric_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='metricUuids')
    phase_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='phaseUuids')
    resource_collection_uuids: list[uuid.UUID] = pydantic.Field(default_factory=list, alias='resourceCollectionUuids')
