import typing
from uuid import UUID

import pydantic

from ..common import BaseModel


class MetricMeasure(BaseModel):
    metric_uuid: UUID
    measure: float = pydantic.Field(ge=0.0, le=1.0)
    weight: float = pydantic.Field(ge=0.0, le=1.0)


class KeyValue(BaseModel):
    key: str
    value: str


TAnnotations = list[KeyValue]
THeaders = list[KeyValue]
TQuestionValueType = typing.Literal[
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
    type: typing.Literal['MinLengthQuestionValidation'] = 'MinLengthQuestionValidation'
    value: int


class MaxLengthQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['MaxLengthQuestionValidation'] = 'MaxLengthQuestionValidation'
    value: int


class RegexQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['RegexQuestionValidation'] = 'RegexQuestionValidation'
    value: str


class OrcidQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['OrcidQuestionValidation'] = 'OrcidQuestionValidation'


class DoiQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['DoiQuestionValidation'] = 'DoiQuestionValidation'


class MinNumberQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['MinNumberQuestionValidation'] = 'MinNumberQuestionValidation'
    value: float


class MaxNumberQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['MaxNumberQuestionValidation'] = 'MaxNumberQuestionValidation'
    value: float


class FromDateQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['FromDateQuestionValidation'] = 'FromDateQuestionValidation'
    value: str  # ISO 8601 date string, e.g., '2023-10-01'


class ToDateQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['ToDateQuestionValidation'] = 'ToDateQuestionValidation'
    value: str  # ISO 8601 date string, e.g., '2023-10-31'


class FromDateTimeQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['FromDateTimeQuestionValidation'] = 'FromDateTimeQuestionValidation'
    value: str  # ISO 8601 datetime string, e.g., '2023-10-01T12:00:00Z'


class ToDateTimeQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['ToDateTimeQuestionValidation'] = 'ToDateTimeQuestionValidation'
    value: str  # ISO 8601 datetime string, e.g., '2023


class FromTimeQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['FromTimeQuestionValidation'] = 'FromTimeQuestionValidation'
    value: str  # ISO 8601 time string, e.g., '12:00:00'


class ToTimeQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['ToTimeQuestionValidation'] = 'ToTimeQuestionValidation'
    value: str  # ISO 8601 time string, e.g., '13:00:00'


class DomainQuestionValidation(pydantic.BaseModel):
    type: typing.Literal['DomainQuestionValidation'] = 'DomainQuestionValidation'
    value: str  # Domain name, e.g., 'example.com'


QuestionValidation = typing.Annotated[
    typing.Union[
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
    ],
    pydantic.Field(discriminator='type'),
]


class TypeHintRequest(BaseModel):
    method: str
    url: str
    headers: THeaders
    body: str | None


class BaseTypeHintResponse(BaseModel):
    response_type: str


class SuccessTypeHintResponse(BaseTypeHintResponse):
    response_type: typing.Literal['SuccessTypeHintResponse'] = 'SuccessTypeHintResponse'
    status: int
    content_type: str | None
    body: str


class RemoteErrorTypeHintResponse(BaseTypeHintResponse):
    response_type: typing.Literal['RemoteErrorTypeHintResponse'] = 'RemoteErrorTypeHintResponse'
    status: int
    content_type: str | None
    body: str


class RequestFailedTypeHintResponse(BaseTypeHintResponse):
    response_type: typing.Literal['RequestFailedTypeHintResponse'] = 'RequestFailedTypeHintResponse'
    message: str


TypeHintResponse = typing.Annotated[
    typing.Union[
        SuccessTypeHintResponse,
        RemoteErrorTypeHintResponse,
        RequestFailedTypeHintResponse,
    ],
    pydantic.Field(discriminator='response_type'),
]


class TypeHintExchange(BaseModel):
    request: TypeHintRequest
    response: TypeHintResponse
