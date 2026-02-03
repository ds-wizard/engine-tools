# pylint: disable=too-many-arguments, too-many-locals, too-many-lines
import datetime
import typing
from uuid import UUID

import pydantic

from .common import (
    BaseModel,
    MetricMeasure,
    QuestionValidation,
    TAnnotations,
    THeaders,
    TQuestionValueType,
    TypeHintExchange,
)


T = typing.TypeVar('T')


class EditEventField[T](BaseModel):
    changed: bool
    value: T | None

    @pydantic.model_serializer(mode='wrap')
    def _serialize(self, handler):
        if not self.changed:
            return {'changed': False}
        # default serialization includes both fields; we only keep what we want
        data = handler(self)
        return {'changed': True, 'value': data.get('value')}

    @classmethod
    def no_change(cls) -> typing.Self:
        return cls(changed=False, value=None)

    @classmethod
    def change(cls, value: T) -> typing.Self:
        return cls(changed=True, value=value)


class BaseEventContent(BaseModel):
    event_type: str


class BaseAddEventContent(BaseEventContent):
    annotations: TAnnotations


class BaseEditEventContent(BaseEventContent):
    annotations: EditEventField[TAnnotations]


# Knowledge Model
class AddKnowledgeModelEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddKnowledgeModelEvent'] = 'AddKnowledgeModelEvent'


class EditKnowledgeModelEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditKnowledgeModelEvent'] = 'EditKnowledgeModelEvent'
    chapter_uuids: EditEventField[list[UUID]]
    integration_uuids: EditEventField[list[UUID]]
    metric_uuids: EditEventField[list[UUID]]
    phase_uuids: EditEventField[list[UUID]]
    resource_collection_uuids: EditEventField[list[UUID]]
    tag_uuids: EditEventField[list[UUID]]


# Chapter
class AddChapterEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddChapterEvent'] = 'AddChapterEvent'
    title: str
    text: str | None


class EditChapterEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditChapterEvent'] = 'EditChapterEvent'
    title: EditEventField[str]
    text: EditEventField[str | None]
    question_uuids: EditEventField[list[UUID]]


class DeleteChapterEventContent(BaseEventContent):
    event_type: typing.Literal['DeleteChapterEvent'] = 'DeleteChapterEvent'


# Question
class _AddQuestionEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddQuestionEvent'] = 'AddQuestionEvent'
    question_type: str
    title: str
    text: str | None
    required_phase_uuid: UUID | None
    tag_uuids: list[UUID]


class AddOptionsQuestionEventContent(_AddQuestionEventContent):
    question_type: typing.Literal['OptionsQuestion'] = 'OptionsQuestion'


class AddMultiChoiceQuestionEventContent(_AddQuestionEventContent):
    question_type: typing.Literal['MultiChoiceQuestion'] = 'MultiChoiceQuestion'


class AddListQuestionEventContent(_AddQuestionEventContent):
    question_type: typing.Literal['ListQuestion'] = 'ListQuestion'


class AddValueQuestionEventContent(_AddQuestionEventContent):
    question_type: typing.Literal['ValueQuestion'] = 'ValueQuestion'
    value_type: TQuestionValueType
    validations: list[QuestionValidation]


class AddIntegrationQuestionEventContent(_AddQuestionEventContent):
    question_type: typing.Literal['IntegrationQuestion'] = 'IntegrationQuestion'
    integration_uuid: UUID
    variables: dict[str, str]


class AddItemSelectQuestionEventContent(_AddQuestionEventContent):
    question_type: typing.Literal['ItemSelectQuestion'] = 'ItemSelectQuestion'
    list_question_uuid: UUID


class AddFileQuestionEventContent(_AddQuestionEventContent):
    question_type: typing.Literal['FileQuestion'] = 'FileQuestion'
    max_size: int | None
    file_types: str | None


AddQuestionEventContent = typing.Annotated[
    AddOptionsQuestionEventContent |
    AddMultiChoiceQuestionEventContent |
    AddListQuestionEventContent |
    AddValueQuestionEventContent |
    AddIntegrationQuestionEventContent |
    AddItemSelectQuestionEventContent |
    AddFileQuestionEventContent,
    pydantic.Field(discriminator='question_type'),
]


class _EditQuestionEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditQuestionEvent'] = 'EditQuestionEvent'
    question_type: str
    title: EditEventField[str]
    text: EditEventField[str | None]
    required_phase_uuid: EditEventField[UUID | None]
    tag_uuids: EditEventField[list[UUID]]
    expert_uuids: EditEventField[list[UUID]]
    reference_uuids: EditEventField[list[UUID]]


class EditOptionsQuestionEventContent(_EditQuestionEventContent):
    question_type: typing.Literal['OptionsQuestion'] = 'OptionsQuestion'
    answer_uuids: EditEventField[list[UUID]]


class EditMultiChoiceQuestionEventContent(_EditQuestionEventContent):
    question_type: typing.Literal['MultiChoiceQuestion'] = 'MultiChoiceQuestion'
    choice_uuids: EditEventField[list[UUID]]


class EditListQuestionEventContent(_EditQuestionEventContent):
    question_type: typing.Literal['ListQuestion'] = 'ListQuestion'
    item_template_question_uuids: EditEventField[list[UUID]]


class EditValueQuestionEventContent(_EditQuestionEventContent):
    question_type: typing.Literal['ValueQuestion'] = 'ValueQuestion'
    value_type: EditEventField[TQuestionValueType]
    validations: EditEventField[list[QuestionValidation]]


class EditIntegrationQuestionEventContent(_EditQuestionEventContent):
    question_type: typing.Literal['IntegrationQuestion'] = 'IntegrationQuestion'
    integration_uuid: EditEventField[UUID]
    variables: EditEventField[dict[str, str]]


class EditItemSelectQuestionEventContent(_EditQuestionEventContent):
    question_type: typing.Literal['ItemSelectQuestion'] = 'ItemSelectQuestion'
    list_question_uuid: EditEventField[UUID]


class EditFileQuestionEventContent(_EditQuestionEventContent):
    question_type: typing.Literal['FileQuestion'] = 'FileQuestion'
    max_size: EditEventField[int | None]
    file_types: EditEventField[str | None]


EditQuestionEventContent = typing.Annotated[
    EditOptionsQuestionEventContent |
    EditMultiChoiceQuestionEventContent |
    EditListQuestionEventContent |
    EditValueQuestionEventContent |
    EditIntegrationQuestionEventContent |
    EditItemSelectQuestionEventContent |
    EditFileQuestionEventContent,
    pydantic.Field(discriminator='question_type'),
]


class DeleteQuestionEventContent(BaseEventContent):
    event_type: typing.Literal['DeleteQuestionEvent'] = 'DeleteQuestionEvent'


# Answer
class AddAnswerEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddAnswerEvent'] = 'AddAnswerEvent'
    label: str
    advice: str | None
    metric_measures: list[MetricMeasure]


class EditAnswerEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditAnswerEvent'] = 'EditAnswerEvent'
    label: EditEventField[str]
    advice: EditEventField[str | None]
    metric_measures: EditEventField[list[MetricMeasure]]
    follow_up_uuids: EditEventField[list[UUID]]


class DeleteAnswerEventContent(BaseEventContent):
    event_type: typing.Literal['DeleteAnswerEvent'] = 'DeleteAnswerEvent'


# Choice
class AddChoiceEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddChoiceEvent'] = 'AddChoiceEvent'
    label: str


class EditChoiceEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditChoiceEvent'] = 'EditChoiceEvent'
    label: EditEventField[str]


class DeleteChoiceEventContent(BaseEventContent):
    event_type: typing.Literal['DeleteChoiceEvent'] = 'DeleteChoiceEvent'


# Reference
class _AddReferenceEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddReferenceEvent'] = 'AddReferenceEvent'
    reference_type: str


class AddResourcePageReferenceEventContent(_AddReferenceEventContent):
    reference_type: typing.Literal['ResourcePageReference'] = 'ResourcePageReference'
    resource_page_uuid: UUID | None


class AddURLReferenceEventContent(_AddReferenceEventContent):
    reference_type: typing.Literal['URLReference'] = 'URLReference'
    url: str
    label: str


class AddCrossReferenceEventContent(_AddReferenceEventContent):
    reference_type: typing.Literal['CrossReference'] = 'CrossReference'
    target_uuid: UUID | None
    description: str


AddReferenceEventContent = typing.Annotated[
    AddResourcePageReferenceEventContent |
    AddURLReferenceEventContent |
    AddCrossReferenceEventContent,
    pydantic.Field(discriminator='reference_type'),
]


class _EditReferenceEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditReferenceEvent'] = 'EditReferenceEvent'
    reference_type: str


class EditResourcePageReferenceEventContent(_EditReferenceEventContent):
    reference_type: typing.Literal['ResourcePageReference'] = 'ResourcePageReference'
    resource_page_uuid: EditEventField[UUID]


class EditURLReferenceEventContent(_EditReferenceEventContent):
    reference_type: typing.Literal['URLReference'] = 'URLReference'
    url: EditEventField[str]
    label: EditEventField[str]


class EditCrossReferenceEventContent(_EditReferenceEventContent):
    reference_type: typing.Literal['CrossReference'] = 'CrossReference'
    target_uuid: EditEventField[UUID]
    description: EditEventField[str]


EditReferenceEventContent = typing.Annotated[
    EditResourcePageReferenceEventContent |
    EditURLReferenceEventContent |
    EditCrossReferenceEventContent,
    pydantic.Field(discriminator='reference_type'),
]


class DeleteReferenceEventContent(BaseEventContent):
    event_type: typing.Literal['DeleteReferenceEvent'] = 'DeleteReferenceEvent'


# Expert
class AddExpertEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddExpertEvent'] = 'AddExpertEvent'
    name: str
    email: str


class EditExpertEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditExpertEvent'] = 'EditExpertEvent'
    name: EditEventField[str]
    email: EditEventField[str]


class DeleteExpertEventContent(BaseEventContent):
    event_type: typing.Literal['DeleteExpertEvent'] = 'DeleteExpertEvent'


# Integration
class _AddIntegrationEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddIntegrationEvent'] = 'AddIntegrationEvent'
    integration_type: str
    name: str
    variables: list[str]


class AddApiIntegrationEventContent(_AddIntegrationEventContent):
    integration_type: typing.Literal['ApiIntegration'] = 'ApiIntegration'
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


class AddApiLegacyIntegrationEventContent(_AddIntegrationEventContent):
    integration_type: typing.Literal['ApiLegacyIntegration'] = 'ApiLegacyIntegration'
    id: str
    logo: str | None
    item_url: str | None
    request_body: str | None
    request_empty_search: bool
    request_headers: THeaders
    request_method: str
    request_url: str
    response_item_id: str | None
    response_item_template: str
    response_list_field: str | None


class AddWidgetIntegrationEventContent(_AddIntegrationEventContent):
    integration_type: typing.Literal['WidgetIntegration'] = 'WidgetIntegration'
    id: str
    logo: str | None
    widget_url: str
    item_url: str | None


AddIntegrationEventContent = typing.Annotated[
    AddApiIntegrationEventContent |
    AddApiLegacyIntegrationEventContent |
    AddWidgetIntegrationEventContent,
    pydantic.Field(discriminator='integration_type'),
]


class _EditIntegrationEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditIntegrationEvent'] = 'EditIntegrationEvent'
    integration_type: str
    name: EditEventField[str]
    variables: EditEventField[list[str]]


class EditApiIntegrationEventContent(_EditIntegrationEventContent):
    integration_type: typing.Literal['ApiIntegration'] = 'ApiIntegration'
    allow_custom_reply: EditEventField[bool]
    request_method: EditEventField[str]
    request_url: EditEventField[str]
    request_headers: EditEventField[THeaders]
    request_body: EditEventField[str | None]
    request_allow_empty_search: EditEventField[bool]
    response_list_field: EditEventField[str | None]
    response_item_template: EditEventField[str]
    response_item_template_for_selection: EditEventField[str | None]
    test_q: EditEventField[str]
    test_variables: EditEventField[dict[str, str]]
    test_response: EditEventField[TypeHintExchange | None]


class EditApiLegacyIntegrationEventContent(_EditIntegrationEventContent):
    integration_type: typing.Literal['ApiLegacyIntegration'] = 'ApiLegacyIntegration'
    id: EditEventField[str]
    logo: EditEventField[str | None]
    item_url: EditEventField[str | None]
    request_body: EditEventField[str | None]
    request_empty_search: EditEventField[bool]
    request_headers: EditEventField[THeaders]
    request_method: EditEventField[str]
    request_url: EditEventField[str]
    response_item_id: EditEventField[str]
    response_item_template: EditEventField[str]
    response_list_field: EditEventField[str | None]


class EditWidgetIntegrationEventContent(_EditIntegrationEventContent):
    integration_type: typing.Literal['WidgetIntegration'] = 'WidgetIntegration'
    id: EditEventField[str]
    logo: EditEventField[str | None]
    widget_url: EditEventField[str]
    item_url: EditEventField[str | None]


EditIntegrationEventContent = typing.Annotated[
    EditApiIntegrationEventContent |
    EditApiLegacyIntegrationEventContent |
    EditWidgetIntegrationEventContent,
    pydantic.Field(discriminator='integration_type'),
]


class DeleteIntegrationEventContent(BaseEventContent):
    event_type: typing.Literal['DeleteIntegrationEvent'] = 'DeleteIntegrationEvent'


# Tag
class AddTagEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddTagEvent'] = 'AddTagEvent'
    name: str
    description: str | None
    color: str


class EditTagEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditTagEvent'] = 'EditTagEvent'
    name: EditEventField[str]
    description: EditEventField[str | None]
    color: EditEventField[str]


class DeleteTagEventContent(BaseEventContent):
    event_type: typing.Literal['DeleteTagEvent'] = 'DeleteTagEvent'


# Metric
class AddMetricEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddMetricEvent'] = 'AddMetricEvent'
    title: str
    abbreviation: str | None
    description: str | None


class EditMetricEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditMetricEvent'] = 'EditMetricEvent'
    title: EditEventField[str]
    abbreviation: EditEventField[str | None]
    description: EditEventField[str | None]


class DeleteMetricEventContent(BaseEventContent):
    event_type: typing.Literal['DeleteMetricEvent'] = 'DeleteMetricEvent'


# Phase
class AddPhaseEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddPhaseEvent'] = 'AddPhaseEvent'
    title: str
    description: str | None


class EditPhaseEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditPhaseEvent'] = 'EditPhaseEvent'
    title: EditEventField[str]
    description: EditEventField[str | None]


class DeletePhaseEventContent(BaseEventContent):
    event_type: typing.Literal['DeletePhaseEvent'] = 'DeletePhaseEvent'


# Resource Collection
class AddResourceCollectionEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddResourceCollectionEvent'] = 'AddResourceCollectionEvent'
    title: str


class EditResourceCollectionEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditResourceCollectionEvent'] = 'EditResourceCollectionEvent'
    title: EditEventField[str]
    resource_page_uuids: EditEventField[list[UUID]]


class DeleteResourceCollectionEventContent(BaseEventContent):
    event_type: typing.Literal['DeleteResourceCollectionEvent'] = 'DeleteResourceCollectionEvent'


# Resource Page
class AddResourcePageEventContent(BaseAddEventContent):
    event_type: typing.Literal['AddResourcePageEvent'] = 'AddResourcePageEvent'
    title: str
    content: str


class EditResourcePageEventContent(BaseEditEventContent):
    event_type: typing.Literal['EditResourcePageEvent'] = 'EditResourcePageEvent'
    title: EditEventField[str]
    content: EditEventField[str]


class DeleteResourcePageEventContent(BaseEventContent):
    event_type: typing.Literal['DeleteResourcePageEvent'] = 'DeleteResourcePageEvent'


# Move events
class _MoveQuestionEventContent(BaseEventContent):
    target_uuid: UUID


class MoveQuestionEventContent(_MoveQuestionEventContent):
    event_type: typing.Literal['MoveQuestionEvent'] = 'MoveQuestionEvent'


class MoveAnswerEventContent(_MoveQuestionEventContent):
    event_type: typing.Literal['MoveAnswerEvent'] = 'MoveAnswerEvent'


class MoveChoiceEventContent(_MoveQuestionEventContent):
    event_type: typing.Literal['MoveChoiceEvent'] = 'MoveChoiceEvent'


class MoveReferenceEventContent(_MoveQuestionEventContent):
    event_type: typing.Literal['MoveReferenceEvent'] = 'MoveReferenceEvent'


class MoveExpertEventContent(_MoveQuestionEventContent):
    event_type: typing.Literal['MoveExpertEvent'] = 'MoveExpertEvent'


# Event
EventContent = typing.Annotated[
    AddKnowledgeModelEventContent |
    EditKnowledgeModelEventContent |
    AddChapterEventContent |
    EditChapterEventContent |
    DeleteChapterEventContent |
    AddQuestionEventContent |
    EditQuestionEventContent |
    DeleteQuestionEventContent |
    AddAnswerEventContent |
    EditAnswerEventContent |
    DeleteAnswerEventContent |
    AddChoiceEventContent |
    EditChoiceEventContent |
    DeleteChoiceEventContent |
    AddReferenceEventContent |
    EditReferenceEventContent |
    DeleteReferenceEventContent |
    AddExpertEventContent |
    EditExpertEventContent |
    DeleteExpertEventContent |
    AddIntegrationEventContent |
    EditIntegrationEventContent |
    DeleteIntegrationEventContent |
    AddTagEventContent |
    EditTagEventContent |
    DeleteTagEventContent |
    AddMetricEventContent |
    EditMetricEventContent |
    DeleteMetricEventContent |
    AddPhaseEventContent |
    EditPhaseEventContent |
    DeletePhaseEventContent |
    AddResourceCollectionEventContent |
    EditResourceCollectionEventContent |
    DeleteResourceCollectionEventContent |
    AddResourcePageEventContent |
    EditResourcePageEventContent |
    DeleteResourcePageEventContent |
    MoveQuestionEventContent |
    MoveAnswerEventContent |
    MoveChoiceEventContent |
    MoveReferenceEventContent |
    MoveExpertEventContent,
    pydantic.Field(discriminator='event_type'),
]


class Event(BaseModel):
    uuid: UUID
    entity_uuid: UUID
    parent_uuid: UUID
    created_at: datetime.datetime
    content: EventContent
