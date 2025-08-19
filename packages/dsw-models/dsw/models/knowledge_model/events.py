# pylint: disable=too-many-arguments, too-many-locals, too-many-lines
import datetime
import json
import typing
import uuid

import pydantic

# https://github.com/ds-wizard/engine-backend/blob/develop/engine-shared/src/Shared/Model/Event/

T = typing.TypeVar('T')
NULL_UUID = uuid.UUID('00000000-0000-0000-0000-000000000000')


class MetricMeasure(pydantic.BaseModel):
    metric_uuid: uuid.UUID = pydantic.Field(alias='metricUuid')
    measure: float = pydantic.Field(ge=0.0, le=1.0)
    weight: float = pydantic.Field(ge=0.0, le=1.0)


class EventField(pydantic.BaseModel, typing.Generic[T]):
    changed: bool
    value: T | None = None

    @pydantic.model_serializer(mode='wrap')
    def _serialize(self, handler):
        if not self.changed:
            return {'changed': False}
        # default serialization includes both fields; we only keep what we want
        data = handler(self)
        return {'changed': True, 'value': data.get('value')}

    @staticmethod
    def unchanged(*args) -> 'EventField[T]':
        return EventField(changed=False)


class MapEntry(pydantic.BaseModel):
    key: str
    value: str


class KMEvent(pydantic.BaseModel):
    event_type: str = pydantic.Field(alias='eventType')
    event_uuid: uuid.UUID = pydantic.Field(alias='uuid')
    entity_uuid: uuid.UUID = pydantic.Field(alias='entityUuid')
    parent_uuid: uuid.UUID = pydantic.Field(alias='parentUuid')
    created_at: datetime.datetime = pydantic.Field(alias='createdAt')


class KMAddEvent(KMEvent):
    annotations: list[MapEntry] = pydantic.Field(alias='annotations')


class KMEditEvent(KMEvent):
    annotations: EventField[list[MapEntry]] = pydantic.Field(alias='annotations')


class KMDeleteEvent(KMEvent):
    pass


class KMMoveEvent(KMEvent):
    target_uuid: str = pydantic.Field(alias='targetUuid')


class AddKnowledgeModelEvent(KMAddEvent):
    event_type: typing.Literal['AddKnowledgeModelEvent'] = pydantic.Field(alias='eventType', default='AddKnowledgeModelEvent')

    @pydantic.field_validator('parent_uuid')
    def must_be_null_uuid(cls, v):
        if v != NULL_UUID:
            raise ValueError(f'parent_uuid must be {NULL_UUID}')
        return v


class EditKnowledgeModelEvent(KMEditEvent):
    event_type: typing.Literal['EditKnowledgeModelEvent'] = pydantic.Field(alias='eventType', default='EditKnowledgeModelEvent')
    chapter_uuids: EventField[list[uuid.UUID]] = pydantic.Field(alias='chapterUuids', default_factory=EventField.unchanged)
    tag_uuids: EventField[list[uuid.UUID]] = pydantic.Field(alias='tagUuids', default_factory=EventField.unchanged)
    integration_uuids: EventField[list[uuid.UUID]] = pydantic.Field(alias='integrationUuids', default_factory=EventField.unchanged)
    metric_uuids: EventField[list[uuid.UUID]] = pydantic.Field(alias='metricUuids', default_factory=EventField.unchanged)
    phase_uuids: EventField[list[uuid.UUID]] = pydantic.Field(alias='phaseUuids', default_factory=EventField.unchanged)
    resource_collection_uuids: EventField[list[uuid.UUID]] = pydantic.Field(alias='resourceCollectionUuids', default_factory=EventField.unchanged)


class AddChapterEvent(KMAddEvent):
    event_type: typing.Literal['AddChapterEvent'] = pydantic.Field(alias='eventType', default='AddChapterEvent')
    title: str
    text: str | None = None


class EditChapterEvent(KMEditEvent):
    event_type: typing.Literal['EditChapterEvent'] = pydantic.Field(alias='eventType', default='EditChapterEvent')
    title: EventField[str]
    text: EventField[str | None]
    question_uuids: EventField[list[uuid.UUID]] = pydantic.Field(alias='questionUuids')


class DeleteChapterEvent(KMDeleteEvent):
    event_type: typing.Literal['DeleteChapterEvent'] = pydantic.Field(alias='eventType', default='DeleteChapterEvent')


class BaseAddQuestionEvent(KMAddEvent):
    event_type: typing.Literal['AddQuestionEvent'] = pydantic.Field(alias='eventType', default='AddQuestionEvent')
    title: str
    text: str | None = None
    required_phase_uuid: uuid.UUID | None = pydantic.Field(alias='requiredPhaseUuid')
    tag_uuids: list[uuid.UUID] = pydantic.Field(alias='tagUuids')
    question_type: str = pydantic.Field(alias='questionType')


class AddOptionsQuestionEvent(BaseAddQuestionEvent):
    question_type: typing.Literal['OptionsQuestion'] = pydantic.Field(alias='questionType', default='OptionsQuestion')


class AddMultiChoiceQuestionEvent(BaseAddQuestionEvent):
    question_type: typing.Literal['MultiChoiceQuestion'] = pydantic.Field(alias='questionType', default='MultiChoiceQuestion')


class AddListQuestionEvent(BaseAddQuestionEvent):
    question_type: typing.Literal['ListQuestion'] = pydantic.Field(alias='questionType', default='ListQuestion')


class AddValueQuestionEvent(BaseAddQuestionEvent):
    question_type: typing.Literal['ValueQuestion'] = pydantic.Field(alias='questionType', default='ValueQuestion')
    value_type: str = pydantic.Field(alias='valueType')  # TODO: enum


class AddIntegrationQuestionEvent(BaseAddQuestionEvent):
    question_type: typing.Literal['IntegrationQuestion'] = pydantic.Field(alias='questionType', default='IntegrationQuestion')
    integration_uuid: uuid.UUID = pydantic.Field(alias='integrationUuid', default=NULL_UUID)
    variables: dict[str, str] = pydantic.Field(alias='variables', default_factory=dict)


class AddItemSelectQuestionEvent(BaseAddQuestionEvent):
    question_type: typing.Literal['ItemSelectQuestion'] = pydantic.Field(alias='questionType', default='ItemSelectQuestion')
    list_question_uuid: uuid.UUID = pydantic.Field(alias='listQuestionUuid', default=NULL_UUID)


class AddFileQuestionEvent(BaseAddQuestionEvent):
    question_type: typing.Literal['FileQuestion'] = pydantic.Field(alias='questionType', default='FileQuestion')
    max_size: int | None = pydantic.Field(alias='maxSize', default=None)
    file_types: str | None = pydantic.Field(alias='fileTypes', default=None)


AddQuestionEvent =  typing.Annotated[
    typing.Union[
        AddValueQuestionEvent,
        AddOptionsQuestionEvent,
        AddMultiChoiceQuestionEvent,
        AddListQuestionEvent,
        AddIntegrationQuestionEvent,
        AddItemSelectQuestionEvent,
        AddFileQuestionEvent,
    ],
    pydantic.Field(discriminator='question_type')
]


class BaseEditQuestionEvent(KMEditEvent):
    event_type: typing.Literal['EditQuestionEvent'] = pydantic.Field(alias='eventType', default='EditQuestionEvent')
    question_type: str = pydantic.Field(alias='questionType')
    title: EventField[str]
    text: EventField[str | None]
    required_phase_uuid: EventField[str | None] = pydantic.Field(alias='requiredPhaseUuid')
    tag_uuids: EventField[list[str]] = pydantic.Field(alias='tagUuids')
    expert_uuids: EventField[list[str]] = pydantic.Field(alias='expertUuids')
    reference_uuids: EventField[list[str]] = pydantic.Field(alias='referenceUuids')


class EditOptionsQuestionEvent(BaseEditQuestionEvent):
    question_type: typing.Literal['OptionsQuestion'] = pydantic.Field(alias='questionType', default='OptionsQuestion')
    answer_uuids: EventField[list[str]] = pydantic.Field(alias='answerUuids')


class EditMultiChoiceQuestionEvent(BaseEditQuestionEvent):
    question_type: typing.Literal['MultiChoiceQuestion'] = pydantic.Field(alias='questionType', default='MultiChoiceQuestion')
    choice_uuids: EventField[list[str]] = pydantic.Field(alias='choiceUuids')


class EditListQuestionEvent(BaseEditQuestionEvent):
    question_type: typing.Literal['ListQuestion'] = pydantic.Field(alias='questionType', default='ListQuestion')
    item_template_question_uuids: EventField[list[str]] = pydantic.Field(alias='itemTemplateQuestionUuids')


class EditValueQuestionEvent(BaseEditQuestionEvent):
    question_type: typing.Literal['ValueQuestion'] = pydantic.Field(alias='questionType', default='ValueQuestion')
    value_type: EventField[str] = pydantic.Field(alias='valueType')  # TODO: enum


class EditIntegrationQuestionEvent(BaseEditQuestionEvent):
    question_type: typing.Literal['IntegrationQuestion'] = pydantic.Field(alias='questionType', default='IntegrationQuestion')
    integration_uuid: EventField[uuid.UUID] = pydantic.Field(alias='integrationUuid')
    variables: EventField[dict[str, str]] = pydantic.Field(alias='variables')


class EditItemSelectQuestionEvent(BaseEditQuestionEvent):
    question_type: typing.Literal['ItemSelectQuestion'] = pydantic.Field(alias='questionType', default='ItemSelectQuestion')
    list_question_uuid: EventField[uuid.UUID] = pydantic.Field(alias='listQuestionUuid')


class EditFileQuestionEvent(BaseEditQuestionEvent):
    question_type: typing.Literal['FileQuestion'] = pydantic.Field(alias='questionType', default='FileQuestion')
    max_size: EventField[int | None] = pydantic.Field(alias='maxSize')
    file_types: EventField[str | None] = pydantic.Field(alias='fileTypes')


EditQuestionEvent = typing.Annotated[
    typing.Union[
        EditValueQuestionEvent,
        EditOptionsQuestionEvent,
        EditMultiChoiceQuestionEvent,
        EditListQuestionEvent,
        EditIntegrationQuestionEvent,
        EditItemSelectQuestionEvent,
        EditFileQuestionEvent,
    ],
    pydantic.Field(discriminator='question_type')
]

class DeleteQuestionEvent(KMDeleteEvent):
    event_type: typing.Literal['DeleteQuestionEvent'] = pydantic.Field(alias='eventType', default='DeleteQuestionEvent')


class AddAnswerEvent(KMAddEvent):
    event_type: typing.Literal['AddAnswerEvent'] = pydantic.Field(alias='eventType', default='AddAnswerEvent')
    label: str
    advice: str | None = None
    metric_measures: list[MetricMeasure] = pydantic.Field(alias='metricMeasures', default_factory=list)


class EditAnswerEvent(KMEditEvent):
    event_type: typing.Literal['EditAnswerEvent'] = pydantic.Field(alias='eventType', default='EditAnswerEvent')
    label: EventField[str]
    advice: EventField[str | None]
    follow_up_uuids: EventField[list[str]] = pydantic.Field(alias='followUpUuids')
    metric_measures: EventField[list[MetricMeasure]] = pydantic.Field(alias='metricMeasures')


class DeleteAnswerEvent(KMDeleteEvent):
    event_type: typing.Literal['DeleteAnswerEvent'] = pydantic.Field(alias='eventType', default='DeleteAnswerEvent')


class AddChoiceEvent(KMAddEvent):
    event_type: typing.Literal['AddChoiceEvent'] = pydantic.Field(alias='eventType', default='AddChoiceEvent')
    label: str


class EditChoiceEvent(KMEditEvent):
    event_type: typing.Literal['EditChoiceEvent'] = pydantic.Field(alias='eventType', default='EditChoiceEvent')
    label: EventField[str]


class DeleteChoiceEvent(KMDeleteEvent):
    event_type: typing.Literal['DeleteChoiceEvent'] = pydantic.Field(alias='eventType', default='DeleteChoiceEvent')


class AddExpertEvent(KMAddEvent):
    event_type: typing.Literal['AddExpertEvent'] = pydantic.Field(alias='eventType', default='AddExpertEvent')
    name: str
    email: str


class EditExpertEvent(KMEditEvent):
    event_type: typing.Literal['EditExpertEvent'] = pydantic.Field(alias='eventType', default='EditExpertEvent')
    name: EventField[str]
    email: EventField[str]


class DeleteExpertEvent(KMDeleteEvent):
    event_type: typing.Literal['DeleteExpertEvent'] = pydantic.Field(alias='eventType', default='DeleteExpertEvent')


class BaseAddReferenceEvent(KMAddEvent):
    event_type: typing.Literal['AddReferenceEvent'] = pydantic.Field(alias='eventType', default='AddReferenceEvent')
    reference_type: str = pydantic.Field(alias='referenceType')


class AddResourcePageReferenceEvent(BaseAddReferenceEvent):
    reference_type: typing.Literal['ResourcePageReference'] = pydantic.Field(alias='referenceType', default='ResourcePageReference')
    resource_page_uuid: uuid.UUID = pydantic.Field(alias='resourcePageUuid')


class AddURLReferenceEvent(BaseAddReferenceEvent):
    reference_type: typing.Literal['URLReference'] = pydantic.Field(alias='referenceType', default='URLReference')
    url: str
    label: str


class AddCrossReferenceEvent(BaseAddReferenceEvent):
    reference_type: typing.Literal['CrossReference'] = pydantic.Field(alias='referenceType', default='CrossReference')
    target_uuid: uuid.UUID = pydantic.Field(alias='targetUuid')
    description: str


AddReferenceEvent = typing.Annotated[
    typing.Union[
        AddResourcePageReferenceEvent,
        AddURLReferenceEvent,
        AddCrossReferenceEvent,
    ],
    pydantic.Field(discriminator='reference_type')
]


class BaseEditReferenceEvent(KMEditEvent):
    event_type: typing.Literal['EditReferenceEvent'] = pydantic.Field(alias='eventType', default='EditReferenceEvent')
    reference_type: str = pydantic.Field(alias='referenceType')


class EditResourcePageReferenceEvent(BaseEditReferenceEvent):
    reference_type: typing.Literal['ResourcePageReference'] = pydantic.Field(alias='referenceType', default='ResourcePageReference')
    resource_page_uuid: EventField[uuid.UUID] = pydantic.Field(alias='resourcePageUuid')


class EditURLReferenceEvent(BaseEditReferenceEvent):
    reference_type: typing.Literal['URLReference'] = pydantic.Field(alias='referenceType', default='URLReference')
    url: EventField[str]
    label: EventField[str]


class EditCrossReferenceEvent(BaseEditReferenceEvent):
    reference_type: typing.Literal['CrossReference'] = pydantic.Field(alias='referenceType', default='CrossReference')
    target_uuid: EventField[uuid.UUID] = pydantic.Field(alias='targetUuid')
    description: EventField[str]


EditReferenceEvent = typing.Annotated[
    typing.Union[
        EditResourcePageReferenceEvent,
        EditURLReferenceEvent,
        EditCrossReferenceEvent,
    ],
    pydantic.Field(discriminator='reference_type')
]


class DeleteReferenceEvent(KMDeleteEvent):
    event_type: typing.Literal['DeleteReferenceEvent'] = pydantic.Field(alias='eventType', default='DeleteReferenceEvent')


class AddTagEvent(KMAddEvent):
    event_type: typing.Literal['AddTagEvent'] = pydantic.Field(alias='eventType', default='AddTagEvent')
    name: str
    description: str | None = None
    color: str


class EditTagEvent(KMEditEvent):
    event_type: typing.Literal['EditTagEvent'] = pydantic.Field(alias='eventType', default='EditTagEvent')
    name: EventField[str]
    description: EventField[str | None]
    color: EventField[str]


class DeleteTagEvent(KMDeleteEvent):
    event_type: typing.Literal['DeleteTagEvent'] = pydantic.Field(alias='eventType', default='DeleteTagEvent')


class BaseAddIntegrationEvent(KMAddEvent):
    event_type: typing.Literal['AddIntegrationEvent'] = pydantic.Field(alias='eventType', default='AddIntegrationEvent')
    integration_type: str = pydantic.Field(alias='integrationType')
    name: str
    variables: list[str]


class AddApiIntegrationEvent(BaseAddIntegrationEvent):
    integration_type: typing.Literal['ApiIntegration'] = pydantic.Field(alias='integrationType', default='ApiIntegration')
    allow_custom_reply: bool = pydantic.Field(alias='allowCustomReply', default=True)
    request_method: typing.Literal['GET', 'POST'] = pydantic.Field(alias='requestMethod', default='GET')
    request_url: str = pydantic.Field(alias='requestUrl')
    request_headers: list[MapEntry] = pydantic.Field(alias='requestHeaders', default_factory=list)
    request_body: str | None = pydantic.Field(alias='requestBody', default=None)
    request_allow_empty_search: bool = pydantic.Field(alias='requestEmptySearch', default=True)
    response_list_field: str | None = pydantic.Field(alias='responseListField', default=None)
    response_item_template: str = pydantic.Field(alias='responseItemTemplate')
    response_item_template_for_selection: str | None = pydantic.Field(alias='responseItemTemplateForSelection', default=None)
    test_q: str = pydantic.Field(alias='testQ', default='')
    test_variables: dict[str, str] = pydantic.Field(alias='testVariables', default_factory=dict)
    test_response: str = pydantic.Field(alias='testResponse', default='')  # TODO: nested


class AddApiLegacyIntegrationEvent(BaseAddIntegrationEvent):
    integration_type: typing.Literal['ApiLegacyIntegration'] = pydantic.Field(alias='integrationType', default='ApiLegacyIntegration')
    id: str
    logo: str | None = None
    request_method: str = pydantic.Field(alias='requestMethod')
    request_url: str = pydantic.Field(alias='requestUrl')
    request_headers: list[MapEntry] = pydantic.Field(alias='requestHeaders')
    request_body: str = pydantic.Field(alias='requestBody')
    request_empty_search: bool = pydantic.Field(alias='requestEmptySearch')
    response_list_field: str | None = pydantic.Field(alias='responseListField')
    response_item_id: str | None = pydantic.Field(alias='responseItemId')
    response_item_template: str = pydantic.Field(alias='responseItemTemplate')
    item_url: str | None = pydantic.Field(alias='itemUrl')


class AddWidgetIntegrationEvent(BaseAddIntegrationEvent):
    integration_type: typing.Literal['WidgetIntegration'] = pydantic.Field(alias='integrationType', default='WidgetIntegration')
    id: str
    logo: str | None = None
    widget_url: str = pydantic.Field(alias='widgetUrl')
    item_url: str | None = pydantic.Field(alias='itemUrl')


AddIntegrationEvent = typing.Annotated[
    typing.Union[
        AddApiIntegrationEvent,
        AddApiLegacyIntegrationEvent,
        AddWidgetIntegrationEvent,
    ],
    pydantic.Field(discriminator='integration_type')
]


class BaseEditIntegrationEvent(KMEditEvent):
    event_type: typing.Literal['EditIntegrationEvent'] = pydantic.Field(alias='eventType', default='EditIntegrationEvent')
    integration_type: str = pydantic.Field(alias='integrationType')
    name: EventField[str]
    variables: EventField[list[str]]


class EditApiIntegrationEvent(BaseEditIntegrationEvent):
    integration_type: typing.Literal['ApiIntegration'] = pydantic.Field(alias='integrationType', default='ApiIntegration')
    allow_custom_reply: EventField[bool] = pydantic.Field(alias='allowCustomReply')
    request_method: EventField[typing.Literal['GET', 'POST']] = pydantic.Field(alias='requestMethod')
    request_url: EventField[str] = pydantic.Field(alias='requestUrl')
    request_headers: EventField[list[MapEntry]] = pydantic.Field(alias='requestHeaders')
    request_body: EventField[str | None] = pydantic.Field(alias='requestBody')
    request_allow_empty_search: EventField[bool] = pydantic.Field(alias='requestEmptySearch')
    response_list_field: EventField[str | None] = pydantic.Field(alias='responseListField')
    response_item_template: EventField[str] = pydantic.Field(alias='responseItemTemplate')
    response_item_template_for_selection: EventField[str | None] = pydantic.Field(alias='responseItemTemplateForSelection')
    test_q: EventField[str] = pydantic.Field(alias='testQ')
    test_variables: EventField[dict[str, str]] = pydantic.Field(alias='testVariables')
    test_response: EventField[str] = pydantic.Field(alias='testResponse')


class EditApiLegacyIntegrationEvent(BaseEditIntegrationEvent):
    integration_type: typing.Literal['ApiLegacyIntegration'] = pydantic.Field(alias='integrationType', default='ApiLegacyIntegration')
    id: EventField[str] = pydantic.Field(alias='id')
    logo: EventField[str | None] = pydantic.Field(alias='logo')
    request_method: EventField[str] = pydantic.Field(alias='requestMethod')
    request_url: EventField[str] = pydantic.Field(alias='requestUrl')
    request_headers: EventField[list[MapEntry]] = pydantic.Field(alias='requestHeaders')
    request_body: EventField[str] = pydantic.Field(alias='requestBody')
    request_empty_search: EventField[bool] = pydantic.Field(alias='requestEmptySearch')
    response_list_field: EventField[str | None] = pydantic.Field(alias='responseListField')
    response_item_id: EventField[str | None] = pydantic.Field(alias='responseItemId')
    response_item_template: EventField[str] = pydantic.Field(alias='responseItemTemplate')
    item_url: EventField[str | None] = pydantic.Field(alias='itemUrl')


class EditWidgetIntegrationEvent(BaseEditIntegrationEvent):
    integration_type: typing.Literal['WidgetIntegration'] = pydantic.Field(alias='integrationType', default='WidgetIntegration')
    id: EventField[str] = pydantic.Field(alias='id')
    logo: EventField[str | None] = pydantic.Field(alias='logo')
    item_url: EventField[str | None] = pydantic.Field(alias='itemUrl')
    widget_url: EventField[str] = pydantic.Field(alias='widgetUrl')


EditIntegrationEvent = typing.Annotated[
    typing.Union[
        EditApiIntegrationEvent,
        EditApiLegacyIntegrationEvent,
        EditWidgetIntegrationEvent,
    ],
    pydantic.Field(discriminator='integration_type')
]


class DeleteIntegrationEvent(KMDeleteEvent):
    event_type: typing.Literal['DeleteIntegrationEvent'] = pydantic.Field(alias='eventType', default='DeleteIntegrationEvent')


class AddMetricEvent(KMAddEvent):
    event_type: typing.Literal['AddMetricEvent'] = pydantic.Field(alias='eventType', default='AddMetricEvent')
    title: str
    abbreviation: str | None
    description: str | None


class EditMetricEvent(KMEditEvent):
    event_type: typing.Literal['EditMetricEvent'] = pydantic.Field(alias='eventType', default='EditMetricEvent')
    title: EventField[str]
    abbreviation: EventField[str | None]
    description: EventField[str | None]


class DeleteMetricEvent(KMDeleteEvent):
    event_type: typing.Literal['DeleteMetricEvent'] = pydantic.Field(alias='eventType', default='DeleteMetricEvent')


class AddPhaseEvent(KMAddEvent):
    event_type: typing.Literal['AddPhaseEvent'] = pydantic.Field(alias='eventType', default='AddPhaseEvent')
    title: str
    description: str | None


class EditPhaseEvent(KMEditEvent):
    event_type: typing.Literal['EditPhaseEvent'] = pydantic.Field(alias='eventType', default='EditPhaseEvent')
    title: EventField[str]
    description: EventField[str | None]


class DeletePhaseEvent(KMDeleteEvent):
    event_type: typing.Literal['DeletePhaseEvent'] = pydantic.Field(alias='eventType', default='DeletePhaseEvent')


class AddResourceCollectionEvent(KMAddEvent):
    event_type: typing.Literal['AddResourceCollectionEvent'] = pydantic.Field(alias='eventType', default='AddResourceCollectionEvent')
    title: str


class EditResourceCollectionEvent(KMEditEvent):
    event_type: typing.Literal['EditResourceCollectionEvent'] = pydantic.Field(alias='eventType', default='EditResourceCollectionEvent')
    title: EventField[str]
    resource_page_uuids: EventField[list[str]] = pydantic.Field(alias='resourcePageUuids', default_factory=EventField.unchanged)


class DeleteResourceCollectionEvent(KMDeleteEvent):
    event_type: typing.Literal['DeleteResourceCollectionEvent'] = pydantic.Field(alias='eventType', default='DeleteResourceCollectionEvent')


class AddResourcePageEvent(KMAddEvent):
    event_type: typing.Literal['AddResourcePageEvent'] = pydantic.Field(alias='eventType', default='AddResourcePageEvent')
    title: str
    content: str


class EditResourcePageEvent(KMEditEvent):
    event_type: typing.Literal['EditResourcePageEvent'] = pydantic.Field(alias='eventType', default='EditResourcePageEvent')
    title: EventField[str]
    content: EventField[str]


class DeleteResourcePageEvent(KMDeleteEvent):
    event_type: typing.Literal['DeleteResourcePageEvent'] = pydantic.Field(alias='eventType', default='DeleteResourcePageEvent')


class MoveQuestionEvent(KMMoveEvent):
    event_type: typing.Literal['MoveQuestionEvent'] = pydantic.Field(alias='eventType', default='MoveQuestionEvent')


class MoveAnswerEvent(KMMoveEvent):
    event_type: typing.Literal['MoveAnswerEvent'] = pydantic.Field(alias='eventType', default='MoveAnswerEvent')


class MoveChoiceEvent(KMMoveEvent):
    event_type: typing.Literal['MoveChoiceEvent'] = pydantic.Field(alias='eventType', default='MoveChoiceEvent')


class MoveExpertEvent(KMMoveEvent):
    event_type: typing.Literal['MoveExpertEvent'] = pydantic.Field(alias='eventType', default='MoveExpertEvent')


class MoveReferenceEvent(KMMoveEvent):
    event_type: typing.Literal['MoveReferenceEvent'] = pydantic.Field(alias='eventType', default='MoveReferenceEvent')


Event = typing.Annotated[
    typing.Union[
        AddKnowledgeModelEvent,
        EditKnowledgeModelEvent,
        AddChapterEvent,
        EditChapterEvent,
        DeleteChapterEvent,
        AddPhaseEvent,
        EditPhaseEvent,
        DeletePhaseEvent,
        AddMetricEvent,
        EditMetricEvent,
        DeleteMetricEvent,
        AddResourceCollectionEvent,
        EditResourceCollectionEvent,
        DeleteResourceCollectionEvent,
        AddResourcePageEvent,
        EditResourcePageEvent,
        DeleteResourcePageEvent,
        AddTagEvent,
        EditTagEvent,
        DeleteTagEvent,
        AddIntegrationEvent,
        EditIntegrationEvent,
        DeleteIntegrationEvent,
        AddQuestionEvent,
        EditQuestionEvent,
        DeleteQuestionEvent,
        AddAnswerEvent,
        EditAnswerEvent,
        DeleteAnswerEvent,
        AddChoiceEvent,
        EditChoiceEvent,
        DeleteChoiceEvent,
        AddReferenceEvent,
        EditReferenceEvent,
        DeleteReferenceEvent,
        AddExpertEvent,
        EditReferenceEvent,
        DeleteExpertEvent,
    ], pydantic.Field(discriminator='event_type')
]

class Model(pydantic.BaseModel):
    event: Event


if __name__ == '__main__':
    test = {
        "eventType": "EditQuestionEvent",
        "uuid": "123e4567-e89b-12d3-a456-426614174000",
        "entityUuid": "123e4567-e89b-12d3-a456-426614174001",
        "parentUuid": "123e4567-e89b-12d3-a456-426614174002",
        "createdAt": "2024-10-01T12:00:00Z",
        "questionType": "ValueQuestion",
        "title": {"changed": True, "value": "New Title"},
        "text": {"changed": False},
        "requiredPhaseUuid": {"changed": True, "value": None},
        "tagUuids": {"changed": True, "value": ["123e4567-e89b-12d3-a456-426614174003"]},
        "expertUuids": {"changed": False},
        "referenceUuids": {"changed": False},
        "valueType": {"changed": False},
        "annotations": {"changed": False}
    }
    result = Model.model_validate({'event': test})
    print(result)
    print(type(result.event))
    print("OK")
    event = result.event.model_dump(mode='json', by_alias=True)
    print(event)

    print(Model.model_json_schema(by_alias=True))
