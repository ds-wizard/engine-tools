"""Knowledge model events as stored in packages and exchanged with the backend."""
from __future__ import annotations

import typing
from uuid import UUID

import pydantic

from ..common import Annotations, BaseModel, JsonValue, KeyValue, Timestamp
from .common import MetricMeasure, QuestionValidation, QuestionValueType, TypeHintExchange


class EditEventField[T](BaseModel):
    """Backend ``EventField``: ``{"changed": false}`` or ``{"changed": true, "value": ...}``."""

    changed: bool
    value: T | None = None

    @pydantic.model_validator(mode='after')
    def _check_value(self) -> typing.Self:
        if self.changed and 'value' not in self.model_fields_set:
            raise ValueError('Changed event field requires a value')
        return self

    @pydantic.model_serializer(mode='wrap')
    def _serialize(self, handler: pydantic.SerializerFunctionWrapHandler) -> dict[str, typing.Any]:
        if not self.changed:
            return {'changed': False}
        return {'changed': True, 'value': handler(self)['value']}

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: typing.Any, handler: pydantic.GetJsonSchemaHandler,
    ) -> dict[str, typing.Any]:
        """``{"changed": false}`` or ``{"changed": true, "value": ...}``, in either mode."""
        value = dict(handler(_model_field_schema(core_schema, 'value')['schema']))
        value.pop('default', None)
        return {
            'oneOf': [
                {'type': 'object', 'properties': {'changed': {'const': False}},
                 'required': ['changed'], 'additionalProperties': False},
                {'type': 'object', 'properties': {'changed': {'const': True}, 'value': value},
                 'required': ['changed', 'value'], 'additionalProperties': False},
            ],
        }

    @classmethod
    def no_change(cls) -> typing.Self:
        return cls(changed=False)

    @classmethod
    def change(cls, value: T) -> typing.Self:
        return cls(changed=True, value=value)


def _model_field_schema(core_schema: typing.Any, name: str) -> typing.Any:
    """Find the core schema of field ``name`` in a (possibly wrapped) model core schema."""
    stack = [core_schema]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get('type') == 'model-fields':
                return node['fields'][name]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    raise KeyError(name)


class EventContent(BaseModel):
    event_type: str


# Knowledge model
class AddKnowledgeModelEventContent(EventContent):
    event_type: typing.Literal['AddKnowledgeModelEvent'] = 'AddKnowledgeModelEvent'
    annotations: Annotations


class EditKnowledgeModelEventContent(EventContent):
    event_type: typing.Literal['EditKnowledgeModelEvent'] = 'EditKnowledgeModelEvent'
    annotations: EditEventField[Annotations]
    chapter_uuids: EditEventField[list[UUID]]
    tag_uuids: EditEventField[list[UUID]]
    integration_uuids: EditEventField[list[UUID]]
    metric_uuids: EditEventField[list[UUID]]
    phase_uuids: EditEventField[list[UUID]]
    resource_collection_uuids: EditEventField[list[UUID]]


# Chapter
class AddChapterEventContent(EventContent):
    event_type: typing.Literal['AddChapterEvent'] = 'AddChapterEvent'
    title: str
    text: str | None = None
    annotations: Annotations


class EditChapterEventContent(EventContent):
    event_type: typing.Literal['EditChapterEvent'] = 'EditChapterEvent'
    title: EditEventField[str]
    text: EditEventField[str | None]
    annotations: EditEventField[Annotations]
    question_uuids: EditEventField[list[UUID]]


class DeleteChapterEventContent(EventContent):
    event_type: typing.Literal['DeleteChapterEvent'] = 'DeleteChapterEvent'


# Question
class AddQuestionEventContentBase(EventContent):
    event_type: typing.Literal['AddQuestionEvent'] = 'AddQuestionEvent'
    title: str
    text: str | None = None
    required_phase_uuid: UUID | None = None
    annotations: Annotations
    tag_uuids: list[UUID]


class AddOptionsQuestionEventContent(AddQuestionEventContentBase):
    question_type: typing.Literal['OptionsQuestion'] = 'OptionsQuestion'


class AddMultiChoiceQuestionEventContent(AddQuestionEventContentBase):
    question_type: typing.Literal['MultiChoiceQuestion'] = 'MultiChoiceQuestion'


class AddListQuestionEventContent(AddQuestionEventContentBase):
    question_type: typing.Literal['ListQuestion'] = 'ListQuestion'


class AddValueQuestionEventContent(AddQuestionEventContentBase):
    question_type: typing.Literal['ValueQuestion'] = 'ValueQuestion'
    value_type: QuestionValueType
    validations: list[QuestionValidation]


class AddIntegrationQuestionEventContent(AddQuestionEventContentBase):
    question_type: typing.Literal['IntegrationQuestion'] = 'IntegrationQuestion'
    integration_uuid: UUID
    variables: dict[str, str]


class AddItemSelectQuestionEventContent(AddQuestionEventContentBase):
    question_type: typing.Literal['ItemSelectQuestion'] = 'ItemSelectQuestion'
    list_question_uuid: UUID | None = None


class AddFileQuestionEventContent(AddQuestionEventContentBase):
    question_type: typing.Literal['FileQuestion'] = 'FileQuestion'
    max_size: int | None = None
    file_types: str | None = None


AddQuestionEventContent = typing.Annotated[
    AddOptionsQuestionEventContent
    | AddMultiChoiceQuestionEventContent
    | AddListQuestionEventContent
    | AddValueQuestionEventContent
    | AddIntegrationQuestionEventContent
    | AddItemSelectQuestionEventContent
    | AddFileQuestionEventContent,
    pydantic.Field(discriminator='question_type'),
]


class EditQuestionEventContentBase(EventContent):
    event_type: typing.Literal['EditQuestionEvent'] = 'EditQuestionEvent'
    title: EditEventField[str]
    text: EditEventField[str | None]
    required_phase_uuid: EditEventField[UUID | None]
    annotations: EditEventField[Annotations]
    tag_uuids: EditEventField[list[UUID]]
    expert_uuids: EditEventField[list[UUID]]
    reference_uuids: EditEventField[list[UUID]]


class EditOptionsQuestionEventContent(EditQuestionEventContentBase):
    question_type: typing.Literal['OptionsQuestion'] = 'OptionsQuestion'
    answer_uuids: EditEventField[list[UUID]]


class EditMultiChoiceQuestionEventContent(EditQuestionEventContentBase):
    question_type: typing.Literal['MultiChoiceQuestion'] = 'MultiChoiceQuestion'
    choice_uuids: EditEventField[list[UUID]]


class EditListQuestionEventContent(EditQuestionEventContentBase):
    question_type: typing.Literal['ListQuestion'] = 'ListQuestion'
    item_template_question_uuids: EditEventField[list[UUID]]


class EditValueQuestionEventContent(EditQuestionEventContentBase):
    question_type: typing.Literal['ValueQuestion'] = 'ValueQuestion'
    value_type: EditEventField[QuestionValueType]
    validations: EditEventField[list[QuestionValidation]]


class EditIntegrationQuestionEventContent(EditQuestionEventContentBase):
    question_type: typing.Literal['IntegrationQuestion'] = 'IntegrationQuestion'
    integration_uuid: EditEventField[UUID]
    variables: EditEventField[dict[str, str]]


class EditItemSelectQuestionEventContent(EditQuestionEventContentBase):
    question_type: typing.Literal['ItemSelectQuestion'] = 'ItemSelectQuestion'
    list_question_uuid: EditEventField[UUID | None]


class EditFileQuestionEventContent(EditQuestionEventContentBase):
    question_type: typing.Literal['FileQuestion'] = 'FileQuestion'
    max_size: EditEventField[int | None]
    file_types: EditEventField[str | None]


EditQuestionEventContent = typing.Annotated[
    EditOptionsQuestionEventContent
    | EditMultiChoiceQuestionEventContent
    | EditListQuestionEventContent
    | EditValueQuestionEventContent
    | EditIntegrationQuestionEventContent
    | EditItemSelectQuestionEventContent
    | EditFileQuestionEventContent,
    pydantic.Field(discriminator='question_type'),
]


class DeleteQuestionEventContent(EventContent):
    event_type: typing.Literal['DeleteQuestionEvent'] = 'DeleteQuestionEvent'


# Answer
class AddAnswerEventContent(EventContent):
    event_type: typing.Literal['AddAnswerEvent'] = 'AddAnswerEvent'
    label: str
    advice: str | None = None
    annotations: Annotations
    metric_measures: list[MetricMeasure]


class EditAnswerEventContent(EventContent):
    event_type: typing.Literal['EditAnswerEvent'] = 'EditAnswerEvent'
    label: EditEventField[str]
    advice: EditEventField[str | None]
    annotations: EditEventField[Annotations]
    follow_up_uuids: EditEventField[list[UUID]]
    metric_measures: EditEventField[list[MetricMeasure]]


class DeleteAnswerEventContent(EventContent):
    event_type: typing.Literal['DeleteAnswerEvent'] = 'DeleteAnswerEvent'


# Choice
class AddChoiceEventContent(EventContent):
    event_type: typing.Literal['AddChoiceEvent'] = 'AddChoiceEvent'
    label: str
    annotations: Annotations


class EditChoiceEventContent(EventContent):
    event_type: typing.Literal['EditChoiceEvent'] = 'EditChoiceEvent'
    label: EditEventField[str]
    annotations: EditEventField[Annotations]


class DeleteChoiceEventContent(EventContent):
    event_type: typing.Literal['DeleteChoiceEvent'] = 'DeleteChoiceEvent'


# Expert
class AddExpertEventContent(EventContent):
    event_type: typing.Literal['AddExpertEvent'] = 'AddExpertEvent'
    name: str
    email: str
    annotations: Annotations


class EditExpertEventContent(EventContent):
    event_type: typing.Literal['EditExpertEvent'] = 'EditExpertEvent'
    name: EditEventField[str]
    email: EditEventField[str]
    annotations: EditEventField[Annotations]


class DeleteExpertEventContent(EventContent):
    event_type: typing.Literal['DeleteExpertEvent'] = 'DeleteExpertEvent'


# Reference
class AddReferenceEventContentBase(EventContent):
    event_type: typing.Literal['AddReferenceEvent'] = 'AddReferenceEvent'
    annotations: Annotations


class AddResourcePageReferenceEventContent(AddReferenceEventContentBase):
    reference_type: typing.Literal['ResourcePageReference'] = 'ResourcePageReference'
    resource_page_uuid: UUID | None = None


class AddURLReferenceEventContent(AddReferenceEventContentBase):
    reference_type: typing.Literal['URLReference'] = 'URLReference'
    url: str
    label: str


class AddCrossReferenceEventContent(AddReferenceEventContentBase):
    reference_type: typing.Literal['CrossReference'] = 'CrossReference'
    target_uuid: UUID
    description: str


AddReferenceEventContent = typing.Annotated[
    AddResourcePageReferenceEventContent
    | AddURLReferenceEventContent
    | AddCrossReferenceEventContent,
    pydantic.Field(discriminator='reference_type'),
]


class EditReferenceEventContentBase(EventContent):
    event_type: typing.Literal['EditReferenceEvent'] = 'EditReferenceEvent'
    annotations: EditEventField[Annotations]


class EditResourcePageReferenceEventContent(EditReferenceEventContentBase):
    reference_type: typing.Literal['ResourcePageReference'] = 'ResourcePageReference'
    resource_page_uuid: EditEventField[UUID | None]


class EditURLReferenceEventContent(EditReferenceEventContentBase):
    reference_type: typing.Literal['URLReference'] = 'URLReference'
    url: EditEventField[str]
    label: EditEventField[str]


class EditCrossReferenceEventContent(EditReferenceEventContentBase):
    reference_type: typing.Literal['CrossReference'] = 'CrossReference'
    target_uuid: EditEventField[UUID]
    description: EditEventField[str]


EditReferenceEventContent = typing.Annotated[
    EditResourcePageReferenceEventContent
    | EditURLReferenceEventContent
    | EditCrossReferenceEventContent,
    pydantic.Field(discriminator='reference_type'),
]


class DeleteReferenceEventContent(EventContent):
    event_type: typing.Literal['DeleteReferenceEvent'] = 'DeleteReferenceEvent'


# Integration
class AddApiIntegrationEventContent(EventContent):
    event_type: typing.Literal['AddIntegrationEvent'] = 'AddIntegrationEvent'
    integration_type: typing.Literal['ApiIntegration'] = 'ApiIntegration'
    name: str
    variables: list[str]
    allow_custom_reply: bool
    request_method: str
    request_url: str
    request_headers: list[KeyValue]
    request_body: str | None = None
    request_allow_empty_search: bool
    response_list_field: str | None = None
    response_item_template: str
    response_item_template_for_selection: str | None = None
    test_q: str
    test_variables: dict[str, str]
    test_response: TypeHintExchange | None = None
    annotations: Annotations


class AddPluginIntegrationEventContent(EventContent):
    event_type: typing.Literal['AddIntegrationEvent'] = 'AddIntegrationEvent'
    integration_type: typing.Literal['PluginIntegration'] = 'PluginIntegration'
    name: str
    plugin_uuid: UUID
    plugin_integration_id: str
    plugin_integration_settings: JsonValue
    annotations: Annotations


AddIntegrationEventContent = typing.Annotated[
    AddApiIntegrationEventContent | AddPluginIntegrationEventContent,
    pydantic.Field(discriminator='integration_type'),
]


class EditApiIntegrationEventContent(EventContent):
    event_type: typing.Literal['EditIntegrationEvent'] = 'EditIntegrationEvent'
    integration_type: typing.Literal['ApiIntegration'] = 'ApiIntegration'
    name: EditEventField[str]
    variables: EditEventField[list[str]]
    allow_custom_reply: EditEventField[bool]
    request_method: EditEventField[str]
    request_url: EditEventField[str]
    request_headers: EditEventField[list[KeyValue]]
    request_body: EditEventField[str | None]
    request_allow_empty_search: EditEventField[bool]
    response_list_field: EditEventField[str | None]
    response_item_template: EditEventField[str]
    response_item_template_for_selection: EditEventField[str | None]
    test_q: EditEventField[str]
    test_variables: EditEventField[dict[str, str]]
    test_response: EditEventField[TypeHintExchange | None]
    annotations: EditEventField[Annotations]


class EditPluginIntegrationEventContent(EventContent):
    event_type: typing.Literal['EditIntegrationEvent'] = 'EditIntegrationEvent'
    integration_type: typing.Literal['PluginIntegration'] = 'PluginIntegration'
    name: EditEventField[str]
    plugin_uuid: EditEventField[UUID]
    plugin_integration_id: EditEventField[str]
    plugin_integration_settings: EditEventField[JsonValue]
    annotations: EditEventField[Annotations]


EditIntegrationEventContent = typing.Annotated[
    EditApiIntegrationEventContent | EditPluginIntegrationEventContent,
    pydantic.Field(discriminator='integration_type'),
]


class DeleteIntegrationEventContent(EventContent):
    event_type: typing.Literal['DeleteIntegrationEvent'] = 'DeleteIntegrationEvent'


# Tag
class AddTagEventContent(EventContent):
    event_type: typing.Literal['AddTagEvent'] = 'AddTagEvent'
    name: str
    description: str | None = None
    color: str
    annotations: Annotations


class EditTagEventContent(EventContent):
    event_type: typing.Literal['EditTagEvent'] = 'EditTagEvent'
    name: EditEventField[str]
    description: EditEventField[str | None]
    color: EditEventField[str]
    annotations: EditEventField[Annotations]


class DeleteTagEventContent(EventContent):
    event_type: typing.Literal['DeleteTagEvent'] = 'DeleteTagEvent'


# Metric
class AddMetricEventContent(EventContent):
    event_type: typing.Literal['AddMetricEvent'] = 'AddMetricEvent'
    title: str
    abbreviation: str | None = None
    description: str | None = None
    annotations: Annotations


class EditMetricEventContent(EventContent):
    event_type: typing.Literal['EditMetricEvent'] = 'EditMetricEvent'
    title: EditEventField[str]
    abbreviation: EditEventField[str | None]
    description: EditEventField[str | None]
    annotations: EditEventField[Annotations]


class DeleteMetricEventContent(EventContent):
    event_type: typing.Literal['DeleteMetricEvent'] = 'DeleteMetricEvent'


# Phase
class AddPhaseEventContent(EventContent):
    event_type: typing.Literal['AddPhaseEvent'] = 'AddPhaseEvent'
    title: str
    description: str | None = None
    annotations: Annotations


class EditPhaseEventContent(EventContent):
    event_type: typing.Literal['EditPhaseEvent'] = 'EditPhaseEvent'
    title: EditEventField[str]
    description: EditEventField[str | None]
    annotations: EditEventField[Annotations]


class DeletePhaseEventContent(EventContent):
    event_type: typing.Literal['DeletePhaseEvent'] = 'DeletePhaseEvent'


# Resource collection
class AddResourceCollectionEventContent(EventContent):
    event_type: typing.Literal['AddResourceCollectionEvent'] = 'AddResourceCollectionEvent'
    title: str
    annotations: Annotations


class EditResourceCollectionEventContent(EventContent):
    event_type: typing.Literal['EditResourceCollectionEvent'] = 'EditResourceCollectionEvent'
    title: EditEventField[str]
    resource_page_uuids: EditEventField[list[UUID]]
    annotations: EditEventField[Annotations]


class DeleteResourceCollectionEventContent(EventContent):
    event_type: typing.Literal['DeleteResourceCollectionEvent'] = 'DeleteResourceCollectionEvent'


# Resource page
class AddResourcePageEventContent(EventContent):
    event_type: typing.Literal['AddResourcePageEvent'] = 'AddResourcePageEvent'
    title: str
    content: str
    annotations: Annotations


class EditResourcePageEventContent(EventContent):
    event_type: typing.Literal['EditResourcePageEvent'] = 'EditResourcePageEvent'
    title: EditEventField[str]
    content: EditEventField[str]
    annotations: EditEventField[Annotations]


class DeleteResourcePageEventContent(EventContent):
    event_type: typing.Literal['DeleteResourcePageEvent'] = 'DeleteResourcePageEvent'


# Move
class MoveEventContent(EventContent):
    target_uuid: UUID


class MoveQuestionEventContent(MoveEventContent):
    event_type: typing.Literal['MoveQuestionEvent'] = 'MoveQuestionEvent'


class MoveAnswerEventContent(MoveEventContent):
    event_type: typing.Literal['MoveAnswerEvent'] = 'MoveAnswerEvent'


class MoveChoiceEventContent(MoveEventContent):
    event_type: typing.Literal['MoveChoiceEvent'] = 'MoveChoiceEvent'


class MoveExpertEventContent(MoveEventContent):
    event_type: typing.Literal['MoveExpertEvent'] = 'MoveExpertEvent'


class MoveReferenceEventContent(MoveEventContent):
    event_type: typing.Literal['MoveReferenceEvent'] = 'MoveReferenceEvent'


AnyEventContent = typing.Annotated[
    AddKnowledgeModelEventContent
    | EditKnowledgeModelEventContent
    | AddChapterEventContent
    | EditChapterEventContent
    | DeleteChapterEventContent
    | AddQuestionEventContent
    | EditQuestionEventContent
    | DeleteQuestionEventContent
    | AddAnswerEventContent
    | EditAnswerEventContent
    | DeleteAnswerEventContent
    | AddChoiceEventContent
    | EditChoiceEventContent
    | DeleteChoiceEventContent
    | AddExpertEventContent
    | EditExpertEventContent
    | DeleteExpertEventContent
    | AddReferenceEventContent
    | EditReferenceEventContent
    | DeleteReferenceEventContent
    | AddIntegrationEventContent
    | EditIntegrationEventContent
    | DeleteIntegrationEventContent
    | AddTagEventContent
    | EditTagEventContent
    | DeleteTagEventContent
    | AddMetricEventContent
    | EditMetricEventContent
    | DeleteMetricEventContent
    | AddPhaseEventContent
    | EditPhaseEventContent
    | DeletePhaseEventContent
    | AddResourceCollectionEventContent
    | EditResourceCollectionEventContent
    | DeleteResourceCollectionEventContent
    | AddResourcePageEventContent
    | EditResourcePageEventContent
    | DeleteResourcePageEventContent
    | MoveQuestionEventContent
    | MoveAnswerEventContent
    | MoveChoiceEventContent
    | MoveExpertEventContent
    | MoveReferenceEventContent,
    pydantic.Field(discriminator='event_type'),
]


class Event(BaseModel):
    uuid: UUID
    parent_uuid: UUID
    entity_uuid: UUID
    content: AnyEventContent
    created_at: Timestamp
