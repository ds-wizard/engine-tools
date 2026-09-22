"""Project event changes sent by a client (``PUT /projects/{uuid}/content``, websocket)."""
from __future__ import annotations

import typing
from uuid import UUID

import pydantic

from ..common import BaseModel, UserSuggestion
from .replies import ReplyValue


class ChangeBase(BaseModel):
    type: str
    uuid: UUID


class PathChangeBase(ChangeBase):
    path: str


class SetReplyEvent(PathChangeBase):
    type: typing.Literal['SetReplyEvent'] = 'SetReplyEvent'
    value: ReplyValue


class ClearReplyEvent(PathChangeBase):
    type: typing.Literal['ClearReplyEvent'] = 'ClearReplyEvent'


class SetPhaseEvent(ChangeBase):
    type: typing.Literal['SetPhaseEvent'] = 'SetPhaseEvent'
    phase_uuid: UUID | None = None


class SetLabelsEvent(PathChangeBase):
    type: typing.Literal['SetLabelsEvent'] = 'SetLabelsEvent'
    value: list[UUID]


class ResolveCommentThreadEvent(PathChangeBase):
    type: typing.Literal['ResolveCommentThreadEvent'] = 'ResolveCommentThreadEvent'
    thread_uuid: UUID
    private: bool
    comment_count: int


class ReopenCommentThreadEvent(PathChangeBase):
    type: typing.Literal['ReopenCommentThreadEvent'] = 'ReopenCommentThreadEvent'
    thread_uuid: UUID
    private: bool
    comment_count: int


class AssignCommentThreadEvent(PathChangeBase):
    type: typing.Literal['AssignCommentThreadEvent'] = 'AssignCommentThreadEvent'
    thread_uuid: UUID
    private: bool
    assigned_to: UserSuggestion | None = None


class DeleteCommentThreadEvent(PathChangeBase):
    type: typing.Literal['DeleteCommentThreadEvent'] = 'DeleteCommentThreadEvent'
    thread_uuid: UUID
    private: bool


class AddCommentEvent(PathChangeBase):
    type: typing.Literal['AddCommentEvent'] = 'AddCommentEvent'
    thread_uuid: UUID
    comment_uuid: UUID
    text: str
    private: bool
    new_thread: bool


class EditCommentEvent(PathChangeBase):
    type: typing.Literal['EditCommentEvent'] = 'EditCommentEvent'
    thread_uuid: UUID
    comment_uuid: UUID
    text: str
    private: bool


class DeleteCommentEvent(PathChangeBase):
    type: typing.Literal['DeleteCommentEvent'] = 'DeleteCommentEvent'
    thread_uuid: UUID
    comment_uuid: UUID
    private: bool


ProjectEventChange = typing.Annotated[
    SetReplyEvent
    | ClearReplyEvent
    | SetPhaseEvent
    | SetLabelsEvent
    | ResolveCommentThreadEvent
    | ReopenCommentThreadEvent
    | AssignCommentThreadEvent
    | DeleteCommentThreadEvent
    | AddCommentEvent
    | EditCommentEvent
    | DeleteCommentEvent,
    pydantic.Field(discriminator='type'),
]
