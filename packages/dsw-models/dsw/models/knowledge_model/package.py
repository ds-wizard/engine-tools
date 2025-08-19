# pylint: disable=too-many-arguments, too-many-locals, too-many-lines
import datetime

import pydantic

from .events import Event


SEMVER_REGEX = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$'


class Package:
    id: str
    km_id: str = pydantic.Field(alias='kmId')
    organization_id: str = pydantic.Field(alias='organizationId')
    version: str = pydantic.Field(alias='version', regex=SEMVER_REGEX)
    name: str
    metamodel_version: int = pydantic.Field(alias='metamodelVersion')
    description: str
    license: str
    readme: str
    created_at: datetime.datetime = pydantic.Field(alias='createdAt')
    fork_of_package_id: str = pydantic.Field(alias='forkOfPackageId')
    merge_checkpoint_package_id: str = pydantic.Field(alias='mergeCheckpointPackageId')
    previous_package_id: str = pydantic.Field(alias='previousPackageId')
    events: list[Event] = pydantic.Field(default_factory=list)


class PackageBundle:
    id: str
    km_id: str = pydantic.Field(alias='kmId')
    organization_id: str = pydantic.Field(alias='organizationId')
    version: str = pydantic.Field(alias='version', regex=SEMVER_REGEX)
    metamodel_version: int = pydantic.Field(alias='metamodelVersion')
    name: str
    packages: list[Package] = pydantic.Field(default_factory=list)
