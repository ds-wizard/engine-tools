"""Migrate ``.km`` bundles to the current knowledge model metamodel version.

Port of ``KnowledgeModelBundleMigrator`` and the legacy fields ``KnowledgeModelBundlePackage``
reads. Works on parsed JSON; validate the result with
:class:`dsw.models.knowledge_model.package.KnowledgeModelBundle`.
"""
from __future__ import annotations

import copy
import typing
from datetime import datetime

import pydantic

from ...common import format_timestamp
from ...errors import MigrationError
from ...versions import KM_METAMODEL_VERSION
from .steps import STEPS, MigrationContext, MigrationStepError


_TIMESTAMP = pydantic.TypeAdapter(datetime)


def migrate_events(
    events: list[typing.Any],
    source_version: int,
    created_at: str | datetime,
    target_version: int = KM_METAMODEL_VERSION,
) -> list[typing.Any]:
    """Upgrade raw events of one package; ``created_at`` is the package's ``createdAt``."""
    if source_version > target_version:
        raise MigrationError(
            f'Downgrade from {source_version} to {target_version} is not supported')
    timestamp = created_at if isinstance(created_at, datetime) else _TIMESTAMP.validate_python(
        created_at)
    ctx = MigrationContext(created_at=format_timestamp(timestamp))
    result = [copy.deepcopy(event) for event in events]
    for version in range(source_version, target_version):
        step = STEPS.get(version)
        if step is None:
            raise MigrationError(f'Unsupported metamodel version {version}')
        try:
            result = [migrated for event in result for migrated in step(event, ctx)]
        except MigrationStepError as error:
            raise MigrationError(f'Migration from version {version} failed: {error}') from error
    return result


def migrate_package(package: dict[str, typing.Any]) -> dict[str, typing.Any]:
    version = package.get('metamodelVersion')
    if not isinstance(version, int) or isinstance(version, bool):
        raise MigrationError(f"Package {package.get('id')} has no valid metamodelVersion")
    if version > KM_METAMODEL_VERSION:
        raise MigrationError(
            f"Package {package.get('id')} has metamodel version {version}, "
            f'only up to {KM_METAMODEL_VERSION} is supported')
    if 'createdAt' not in package:
        raise MigrationError(f"Package {package.get('id')} has no createdAt")
    migrated = dict(package)
    migrated['events'] = migrate_events(package.get('events', []), version, package['createdAt'])
    migrated['metamodelVersion'] = KM_METAMODEL_VERSION
    # legacy "parentPackageId" is read as the default of the three package links
    parent = migrated.pop('parentPackageId', None)
    for link in ('previousPackageId', 'forkOfPackageId', 'mergeCheckpointPackageId'):
        if migrated.get(link) is None:
            migrated[link] = parent
    return migrated


def migrate_bundle(bundle: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """A migrated copy of a parsed ``.km`` bundle."""
    if not isinstance(bundle, dict) or not isinstance(bundle.get('packages'), list):
        raise MigrationError('A bundle must be an object with a "packages" list')
    return {
        **bundle,
        'packages': [migrate_package(package) for package in bundle['packages']],
        'metamodelVersion': KM_METAMODEL_VERSION,
    }
