"""Knowledge model bundle (``.km`` file) and its packages."""
from __future__ import annotations

from datetime import UTC, datetime

import pydantic

from ..common import BaseModel, Timestamp
from .common import PackagePhase
from .events import Event


class KnowledgeModelBundlePackage(BaseModel):
    id: str
    name: str
    organization_id: str
    km_id: str
    version: str
    phase: PackagePhase = 'ReleasedKnowledgeModelPackagePhase'
    metamodel_version: int
    description: str
    readme: str = ''
    license: str = ''
    language: str = 'en'
    previous_package_id: str | None = None
    fork_of_package_id: str | None = None
    merge_checkpoint_package_id: str | None = None
    events: list[Event]
    non_editable: bool = False
    created_at: Timestamp = datetime(1970, 1, 1, tzinfo=UTC)


class KnowledgeModelBundle(BaseModel):
    id: str
    name: str
    organization_id: str
    km_id: str
    version: str
    metamodel_version: int
    packages: list[KnowledgeModelBundlePackage] = pydantic.Field(default_factory=list)
