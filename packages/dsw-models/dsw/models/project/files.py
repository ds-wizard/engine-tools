from __future__ import annotations

from uuid import UUID

from ..common import BaseModel


class ProjectFile(BaseModel):
    """Backend ``ProjectFileSimple``, as used by the API and document context."""

    uuid: UUID
    file_name: str
    content_type: str
    file_size: int
