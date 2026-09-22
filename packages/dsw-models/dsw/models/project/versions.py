from __future__ import annotations

from uuid import UUID

from ..common import BaseModel, Timestamp, UserSuggestion


class ProjectVersion(BaseModel):
    """Named pointer to a project event (backend ``ProjectVersionList``)."""

    uuid: UUID
    name: str
    description: str | None = None
    event_uuid: UUID
    created_by: UserSuggestion | None = None
    created_at: Timestamp
    updated_at: Timestamp
