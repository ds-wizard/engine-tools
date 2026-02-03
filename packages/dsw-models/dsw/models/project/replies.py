import datetime
import typing
from uuid import UUID

import pydantic

from ..common import BaseModel
from .common import UserInfo


class BaseIntegrationReplyType(BaseModel):
    type: str


class PlainIntegrationReplyType(BaseIntegrationReplyType):
    type: typing.Literal['PlainType'] = 'PlainType'
    content: str


class IntegrationLegacyReplyType(BaseIntegrationReplyType):
    type: typing.Literal['LegacyType'] = 'LegacyType'
    id: str | None
    value: str


class IntegrationReplyType(BaseModel):
    type: typing.Literal['IntegrationType'] = 'IntegrationType'
    value: str
    raw: pydantic.Json[dict[str, typing.Any]]


IntegrationReply = typing.Annotated[
    PlainIntegrationReplyType |
    IntegrationLegacyReplyType |
    IntegrationReplyType,
    pydantic.Field(discriminator='type'),
]


class BaseReplyValue(BaseModel):
    type: str


class StringReplyValue(BaseReplyValue):
    type: typing.Literal['StringReply'] = 'StringReply'
    value: str


class AnswerReplyValue(BaseReplyValue):
    type: typing.Literal['AnswerReply'] = 'AnswerReply'
    value: UUID


class MultiChoiceReplyValue(BaseReplyValue):
    type: typing.Literal['MultiChoiceReply'] = 'MultiChoiceReply'
    value: list[UUID]


class ItemListReplyValue(BaseReplyValue):
    type: typing.Literal['ItemListReply'] = 'ItemListReply'
    value: list[str]


class IntegrationReplyValue(BaseReplyValue):
    type: typing.Literal['IntegrationReply'] = 'IntegrationReply'
    value: IntegrationReply


class ItemSelectionReplyValue(BaseReplyValue):
    type: typing.Literal['ItemSelectReply'] = 'ItemSelectReply'
    value: UUID


class FileReplyValue(BaseReplyValue):
    type: typing.Literal['FileReply'] = 'FileReply'
    value: UUID


ReplyValue = typing.Annotated[
    StringReplyValue |
    AnswerReplyValue |
    MultiChoiceReplyValue |
    ItemListReplyValue |
    IntegrationReplyValue |
    ItemSelectionReplyValue |
    FileReplyValue,
    pydantic.Field(discriminator='type'),
]


class Reply(BaseModel):
    value: ReplyValue
    created_by: UserInfo | None
    created_at: datetime.datetime
