"""Project content (replies, labels, phase) compiled from project events.

Port of ``Wizard.Service.Project.Compiler.ProjectCompilerService``.
"""
from __future__ import annotations

import typing
from uuid import UUID

import pydantic

from ..common import BaseModel
from .events import ClearReplyEvent, SetLabelsEvent, SetPhaseEvent, SetReplyEvent
from .replies import Reply


if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from .events import ProjectEvent


class ProjectContent(BaseModel):
    phase_uuid: UUID | None = None
    replies: dict[str, Reply] = pydantic.Field(default_factory=dict)
    labels: dict[str, list[UUID]] = pydantic.Field(default_factory=dict)


def compile_project_events(
    events: Iterable[ProjectEvent],
    *,
    until: UUID | None = None,
) -> ProjectContent:
    """Apply events in order; stop after the event ``until`` (inclusive), e.g. a version's event."""
    content = ProjectContent()
    for event in events:
        if isinstance(event, SetReplyEvent):
            content.replies[event.path] = Reply(
                value=event.value, created_by=event.created_by, created_at=event.created_at)
        elif isinstance(event, ClearReplyEvent):
            content.replies.pop(event.path, None)
        elif isinstance(event, SetPhaseEvent):
            content.phase_uuid = event.phase_uuid
        elif isinstance(event, SetLabelsEvent):
            if event.value:
                content.labels[event.path] = list(event.value)
            else:
                content.labels.pop(event.path, None)
        if until is not None and event.uuid == until:
            break
    return content
