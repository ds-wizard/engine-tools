"""Project events as the backend sends them (event list, content DTO, websocket).

The client-to-server form without ``createdBy``/``createdAt`` is in :mod:`.changes`.
"""
from __future__ import annotations

import typing
from uuid import UUID

import pydantic

from ..common import BaseModel, Timestamp, UserSuggestion
from .common import PATH_SEPARATOR
from .replies import ReplyValue


class ProjectEventBase(BaseModel):
    type: str
    uuid: UUID
    created_by: UserSuggestion | None = None
    created_at: Timestamp


class PathEventBase(ProjectEventBase):
    path: str

    @property
    def path_parts(self) -> list[str]:
        return self.path.split(PATH_SEPARATOR) if self.path else []


class SetReplyEvent(PathEventBase):
    type: typing.Literal['SetReplyEvent'] = 'SetReplyEvent'
    value: ReplyValue


class ClearReplyEvent(PathEventBase):
    type: typing.Literal['ClearReplyEvent'] = 'ClearReplyEvent'


class SetPhaseEvent(ProjectEventBase):
    type: typing.Literal['SetPhaseEvent'] = 'SetPhaseEvent'
    phase_uuid: UUID | None = None


class SetLabelsEvent(PathEventBase):
    type: typing.Literal['SetLabelsEvent'] = 'SetLabelsEvent'
    value: list[UUID]


class ResolveCommentThreadEvent(PathEventBase):
    type: typing.Literal['ResolveCommentThreadEvent'] = 'ResolveCommentThreadEvent'
    thread_uuid: UUID
    comment_count: int


class ReopenCommentThreadEvent(PathEventBase):
    type: typing.Literal['ReopenCommentThreadEvent'] = 'ReopenCommentThreadEvent'
    thread_uuid: UUID
    comment_count: int


class AssignCommentThreadEvent(PathEventBase):
    type: typing.Literal['AssignCommentThreadEvent'] = 'AssignCommentThreadEvent'
    thread_uuid: UUID
    private: bool
    assigned_to: UserSuggestion | None = None


class DeleteCommentThreadEvent(PathEventBase):
    type: typing.Literal['DeleteCommentThreadEvent'] = 'DeleteCommentThreadEvent'
    thread_uuid: UUID


class AddCommentEvent(PathEventBase):
    type: typing.Literal['AddCommentEvent'] = 'AddCommentEvent'
    thread_uuid: UUID
    comment_uuid: UUID
    text: str
    private: bool
    new_thread: bool


class EditCommentEvent(PathEventBase):
    type: typing.Literal['EditCommentEvent'] = 'EditCommentEvent'
    thread_uuid: UUID
    comment_uuid: UUID
    text: str


class DeleteCommentEvent(PathEventBase):
    type: typing.Literal['DeleteCommentEvent'] = 'DeleteCommentEvent'
    thread_uuid: UUID
    comment_uuid: UUID


#: Events that change project content; the only ones the backend stores.
ProjectEvent = typing.Annotated[
    SetReplyEvent | ClearReplyEvent | SetPhaseEvent | SetLabelsEvent,
    pydantic.Field(discriminator='type'),
]

#: Content and comment events, as pushed to clients.
AnyProjectEvent = typing.Annotated[
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
