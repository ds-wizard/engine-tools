import datetime
from uuid import UUID

from ..common import BaseModel


class ProjectFile(BaseModel):
    uuid: UUID
    file_name: str
    content_type: str
    file_size: int
    project_uuid: UUID
    tenant_uuid: UUID
    created_by: UUID | None
    created_at: datetime.datetime
