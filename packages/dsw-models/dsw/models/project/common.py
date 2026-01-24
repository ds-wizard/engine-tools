from uuid import UUID

from ..common import BaseModel


TODO_LABEL_UUID = UUID('615b9028-5e3f-414f-b245-12d2ae2eeb20')


class UserInfo(BaseModel):
    uuid: UUID
    first_name: str
    last_name: str
    gravatar_hash: str
    image_url: str | None
