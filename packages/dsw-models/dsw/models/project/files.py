from __future__ import annotations

import typing

from ..common import BaseModel


if typing.TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class ProjectFile(BaseModel):
    uuid: UUID
    file_name: str
    content_type: str
    file_size: int
    project_uuid: UUID
    tenant_uuid: UUID
    created_by: UUID | None
    created_at: datetime
