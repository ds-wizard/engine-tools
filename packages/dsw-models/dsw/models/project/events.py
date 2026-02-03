import typing
from uuid import UUID, uuid4

import pydantic

from ..common import BaseModel
from .common import UserInfo
from .replies import ReplyValue


class BaseProjectEvent(BaseModel):
    uuid: UUID = pydantic.Field(default_factory=uuid4)
    type: str


class BaseProjectPathEvent(BaseProjectEvent):
    path: str

    @property
    def path_parts(self) -> list[str]:
        return self.path.split('.') if self.path else []


class SetPhaseEvent(BaseProjectEvent):
    type: typing.Literal['SetPhaseEvent'] = 'SetPhaseEvent'
    phase_uuid: UUID | None


class SetReplyEvent(BaseProjectPathEvent):
    type: typing.Literal['SetReplyEvent'] = 'SetReplyEvent'
    value: ReplyValue


class ClearReplyEvent(BaseProjectPathEvent):
    type: typing.Literal['ClearReplyEvent'] = 'ClearReplyEvent'


class SetLabelsEvent(BaseProjectPathEvent):
    type: typing.Literal['SetLabelsEvent'] = 'SetLabelsEvent'
    labels: list[UUID]


class AddCommentEvent(BaseProjectPathEvent):
    type: typing.Literal['AddCommentEvent'] = 'AddCommentEvent'
    thread_uuid: UUID
    comment_uuid: UUID
    text: str
    private: bool = False
    new_thread: bool


class EditCommentEvent(BaseProjectPathEvent):
    type: typing.Literal['EditCommentEvent'] = 'EditCommentEvent'
    thread_uuid: UUID
    comment_uuid: UUID
    text: str
    private: bool = False


class DeleteCommentEvent(BaseProjectPathEvent):
    type: typing.Literal['DeleteCommentEvent'] = 'DeleteCommentEvent'
    thread_uuid: UUID
    comment_uuid: UUID
    private: bool = False


class AssignCommentThreadEvent(BaseProjectPathEvent):
    type: typing.Literal['AssignCommentThreadEvent'] = 'AssignCommentThreadEvent'
    thread_uuid: UUID
    private: bool = False
    assigned_to: UserInfo | None


class ResolveCommentThreadEvent(BaseProjectPathEvent):
    type: typing.Literal['ResolveCommentThreadEvent'] = 'ResolveCommentThreadEvent'
    thread_uuid: UUID
    private: bool = False
    comment_count: int


class ReopenCommentThreadEvent(BaseProjectPathEvent):
    type: typing.Literal['ReopenCommentThreadEvent'] = 'ReopenCommentThreadEvent'
    thread_uuid: UUID
    private: bool = False
    comment_count: int


ProjectEvent = typing.Annotated[
    SetPhaseEvent |
    SetReplyEvent |
    ClearReplyEvent |
    SetLabelsEvent |
    AddCommentEvent |
    EditCommentEvent |
    DeleteCommentEvent |
    AssignCommentThreadEvent |
    ResolveCommentThreadEvent |
    ReopenCommentThreadEvent,
    pydantic.Field(discriminator='type'),
]
