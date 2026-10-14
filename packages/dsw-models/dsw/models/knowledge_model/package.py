"""Knowledge model bundle (``.km`` file) and its packages.

The models read both bundle shapes, as the backend imports them: the 5.0 one with a single
``id`` and split package links, and the older one with ``organizationId`` + ``kmId`` and
``org:km:version`` references (see :mod:`dsw.models.coordinate`). They write only the 5.0 shape.
"""
from __future__ import annotations

import typing
from datetime import UTC, datetime

import pydantic

from ..common import BaseModel, Timestamp
from ..coordinate import build_reference, upgrade_legacy_coordinate, upgrade_legacy_id
from .common import PackagePhase
from .events import Event


_PACKAGE_LINKS = ('previousPackage', 'forkOfPackage', 'mergeCheckpointPackage')


def _upgrade_legacy_identity(data: typing.Any, *, links: bool) -> typing.Any:
    if not isinstance(data, dict):
        return data
    data = dict(data)
    upgrade_legacy_id(data, 'kmId')
    if links:
        for prefix in _PACKAGE_LINKS:
            upgrade_legacy_coordinate(data, prefix)
    return data


class KnowledgeModelBundlePackage(BaseModel):
    id: str
    name: str
    version: str
    phase: PackagePhase = 'ReleasedKnowledgeModelPackagePhase'
    metamodel_version: int
    description: str
    readme: str = ''
    license: str = ''
    language: str = 'en'
    events: list[Event]
    non_editable: bool = False
    created_at: Timestamp = datetime(1970, 1, 1, tzinfo=UTC)
    previous_package_id: str | None = None
    previous_package_version: str | None = None
    fork_of_package_id: str | None = None
    fork_of_package_version: str | None = None
    merge_checkpoint_package_id: str | None = None
    merge_checkpoint_package_version: str | None = None

    @pydantic.model_validator(mode='before')
    @classmethod
    def _upgrade_legacy(cls, data: typing.Any) -> typing.Any:
        return _upgrade_legacy_identity(data, links=True)

    @property
    def reference(self) -> str:
        return build_reference(self.id, self.version)

    @property
    def previous_package_reference(self) -> str | None:
        if self.previous_package_id is None or self.previous_package_version is None:
            return None
        return build_reference(self.previous_package_id, self.previous_package_version)


class KnowledgeModelBundle(BaseModel):
    id: str
    name: str
    version: str
    metamodel_version: int
    packages: list[KnowledgeModelBundlePackage] = pydantic.Field(default_factory=list)

    @pydantic.model_validator(mode='before')
    @classmethod
    def _upgrade_legacy(cls, data: typing.Any) -> typing.Any:
        return _upgrade_legacy_identity(data, links=False)

    @property
    def reference(self) -> str:
        return build_reference(self.id, self.version)
