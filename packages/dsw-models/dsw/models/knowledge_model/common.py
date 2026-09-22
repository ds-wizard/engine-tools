"""Types shared by the flat knowledge model and its events."""
from __future__ import annotations

import typing
from uuid import UUID

import pydantic

from ..common import BaseModel, KeyValue


class MetricMeasure(BaseModel):
    metric_uuid: UUID
    measure: float
    weight: float


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

PackagePhase = typing.Literal[
    'ReleasedKnowledgeModelPackagePhase',
    'DeprecatedKnowledgeModelPackagePhase',
]


class MinLengthQuestionValidation(BaseModel):
    type: typing.Literal['MinLengthQuestionValidation'] = 'MinLengthQuestionValidation'
    value: int


class MaxLengthQuestionValidation(BaseModel):
    type: typing.Literal['MaxLengthQuestionValidation'] = 'MaxLengthQuestionValidation'
    value: int


class RegexQuestionValidation(BaseModel):
    type: typing.Literal['RegexQuestionValidation'] = 'RegexQuestionValidation'
    value: str


class OrcidQuestionValidation(BaseModel):
    type: typing.Literal['OrcidQuestionValidation'] = 'OrcidQuestionValidation'


class DoiQuestionValidation(BaseModel):
    type: typing.Literal['DoiQuestionValidation'] = 'DoiQuestionValidation'


class MinNumberQuestionValidation(BaseModel):
    type: typing.Literal['MinNumberQuestionValidation'] = 'MinNumberQuestionValidation'
    value: float


class MaxNumberQuestionValidation(BaseModel):
    type: typing.Literal['MaxNumberQuestionValidation'] = 'MaxNumberQuestionValidation'
    value: float


class FromDateQuestionValidation(BaseModel):
    type: typing.Literal['FromDateQuestionValidation'] = 'FromDateQuestionValidation'
    value: str


class ToDateQuestionValidation(BaseModel):
    type: typing.Literal['ToDateQuestionValidation'] = 'ToDateQuestionValidation'
    value: str


class FromDateTimeQuestionValidation(BaseModel):
    type: typing.Literal['FromDateTimeQuestionValidation'] = 'FromDateTimeQuestionValidation'
    value: str


class ToDateTimeQuestionValidation(BaseModel):
    type: typing.Literal['ToDateTimeQuestionValidation'] = 'ToDateTimeQuestionValidation'
    value: str


class FromTimeQuestionValidation(BaseModel):
    type: typing.Literal['FromTimeQuestionValidation'] = 'FromTimeQuestionValidation'
    value: str


class ToTimeQuestionValidation(BaseModel):
    type: typing.Literal['ToTimeQuestionValidation'] = 'ToTimeQuestionValidation'
    value: str


class DomainQuestionValidation(BaseModel):
    type: typing.Literal['DomainQuestionValidation'] = 'DomainQuestionValidation'
    value: str


QuestionValidation = typing.Annotated[
    MinLengthQuestionValidation
    | MaxLengthQuestionValidation
    | RegexQuestionValidation
    | OrcidQuestionValidation
    | DoiQuestionValidation
    | MinNumberQuestionValidation
    | MaxNumberQuestionValidation
    | FromDateQuestionValidation
    | ToDateQuestionValidation
    | FromDateTimeQuestionValidation
    | ToDateTimeQuestionValidation
    | FromTimeQuestionValidation
    | ToTimeQuestionValidation
    | DomainQuestionValidation,
    pydantic.Field(discriminator='type'),
]


class TypeHintRequest(BaseModel):
    method: str
    url: str
    headers: list[KeyValue]
    body: str | None = None


class SuccessTypeHintResponse(BaseModel):
    response_type: typing.Literal['SuccessTypeHintResponse'] = 'SuccessTypeHintResponse'
    status: int
    content_type: str | None = None
    body: str


class RemoteErrorTypeHintResponse(BaseModel):
    response_type: typing.Literal['RemoteErrorTypeHintResponse'] = 'RemoteErrorTypeHintResponse'
    status: int
    content_type: str | None = None
    body: str


class RequestFailedTypeHintResponse(BaseModel):
    response_type: typing.Literal['RequestFailedTypeHintResponse'] = (
        'RequestFailedTypeHintResponse'
    )
    message: str


TypeHintResponse = typing.Annotated[
    SuccessTypeHintResponse | RemoteErrorTypeHintResponse | RequestFailedTypeHintResponse,
    pydantic.Field(discriminator='response_type'),
]


class TypeHintExchange(BaseModel):
    request: TypeHintRequest
    response: TypeHintResponse
