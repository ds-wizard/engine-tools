# pylint: disable=too-many-arguments, too-many-locals, too-many-lines
import datetime

from .common import BaseModel
from .events import Event


class KnowledgeModelPackage(BaseModel):
    id: str
    km_id: str
    organization_id: str
    version: str
    name: str
    metamodel_version: int
    description: str
    license: str
    readme: str
    created_at: datetime.datetime
    fork_of_package_id: str | None
    merge_checkpoint_package_id: str | None
    previous_package_id: str | None
    events: list[Event]
    non_editable: bool = False
    phase: str


class KnowledgeModelPackageBundle(BaseModel):
    id: str
    km_id: str
    organization_id: str
    version: str
    metamodel_version: int
    name: str
    packages: list[KnowledgeModelPackage]
