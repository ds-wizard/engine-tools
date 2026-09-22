"""Project replies: values stored under reply paths (``chapterUuid.questionUuid…``)."""
from __future__ import annotations

import typing
from uuid import UUID

import pydantic

from ..common import BaseModel, JsonValue, Timestamp, UserSuggestion


class PlainIntegrationReplyType(BaseModel):
    type: typing.Literal['PlainType'] = 'PlainType'
    value: str


class IntegrationReplyType(BaseModel):
    type: typing.Literal['IntegrationType'] = 'IntegrationType'
    value: str
    raw: JsonValue


IntegrationReplyValueContent = typing.Annotated[
    PlainIntegrationReplyType | IntegrationReplyType,
    pydantic.Field(discriminator='type'),
]


class StringReplyValue(BaseModel):
    type: typing.Literal['StringReply'] = 'StringReply'
    value: str


class AnswerReplyValue(BaseModel):
    type: typing.Literal['AnswerReply'] = 'AnswerReply'
    value: UUID


class MultiChoiceReplyValue(BaseModel):
    type: typing.Literal['MultiChoiceReply'] = 'MultiChoiceReply'
    value: list[UUID]


class ItemListReplyValue(BaseModel):
    type: typing.Literal['ItemListReply'] = 'ItemListReply'
    value: list[UUID]


class IntegrationReplyValue(BaseModel):
    type: typing.Literal['IntegrationReply'] = 'IntegrationReply'
    value: IntegrationReplyValueContent


class ItemSelectReplyValue(BaseModel):
    type: typing.Literal['ItemSelectReply'] = 'ItemSelectReply'
    value: UUID


class FileReplyValue(BaseModel):
    type: typing.Literal['FileReply'] = 'FileReply'
    value: UUID


ReplyValue = typing.Annotated[
    StringReplyValue
    | AnswerReplyValue
    | MultiChoiceReplyValue
    | ItemListReplyValue
    | IntegrationReplyValue
    | ItemSelectReplyValue
    | FileReplyValue,
    pydantic.Field(discriminator='type'),
]


class Reply(BaseModel):
    value: ReplyValue
    created_by: UserSuggestion | None = None
    created_at: Timestamp


Replies = dict[str, Reply]
