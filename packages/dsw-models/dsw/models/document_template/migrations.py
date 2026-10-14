"""Best-effort upgrade of older ``template.json`` descriptors to the current metamodel version.

The backend has no template migrations: it only accepts the same major version with a lower or
equal minor version. The steps below are derived from the published ``template.json`` schemas
(``ds-wizard/dsw-schemas``, versions 1–18.0) and the backend descriptors for 18.3 and 19.0:

========  =============================================================================
Version   Change
========  =============================================================================
11        ``formats[].color``, ``formats[].shortName`` and ``recommendedPackageId`` removed
17.0      ``metamodelVersion`` became a ``"major.minor"`` string
18.3      ``language`` added (default ``"en"``)
19.0      no descriptor change (single ``id``, see below); the document context was restructured
========  =============================================================================

Whatever the version, the identity is upgraded to the single ``id`` of Wizard 5.0, as the
backend's import does: ``organizationId`` + ``templateId`` (or the composed
``organizationId:templateId:version`` of the oldest descriptors) become ``id`` =
``<organizationId>.<templateId>``, and ``allowedPackages`` patterns ``orgId`` + ``kmId`` become
``id`` (``None`` when only the organization was named).

Only the descriptor is upgraded. Jinja templates and step options were written for the document
context of their version and are not touched, so every major version crossed adds a warning.
"""
from __future__ import annotations

import copy
import dataclasses
import typing

from ..coordinate import join_legacy_id, parse_legacy_reference
from ..errors import MetamodelVersionError, MigrationError
from ..versions import DOCUMENT_TEMPLATE_METAMODEL_VERSION, MetamodelVersion
from .metadata import upgrade_legacy_package_pattern


@dataclasses.dataclass(frozen=True, slots=True)
class MigrationResult:
    data: dict[str, typing.Any]
    source_version: MetamodelVersion
    warnings: list[str]
    #: the data differs from the input, or there is something to review
    changed: bool


def migrate_template_json(data: dict[str, typing.Any]) -> MigrationResult:
    """Upgrade a parsed ``template.json``, the local descriptor or a package's one.

    Validate the result with :class:`.metadata.DocumentTemplateMetadata` (local) or
    :class:`.metadata.DocumentTemplateBundle` (bundle).
    """
    if not isinstance(data, dict):
        raise MigrationError('template.json must contain an object')
    if 'metamodelVersion' not in data:
        raise MigrationError('template.json has no metamodelVersion')
    try:
        source = MetamodelVersion.parse(data['metamodelVersion'])
    except MetamodelVersionError as error:
        raise MigrationError(str(error)) from error
    target = DOCUMENT_TEMPLATE_METAMODEL_VERSION
    if source > target:
        raise MigrationError(f'Metamodel version {source} is newer than supported {target}')

    result = copy.deepcopy(data)
    warnings: list[str] = []
    _upgrade_legacy_identity(result, warnings)
    if source.major < 11:  # noqa: PLR2004
        _drop_pre_11_fields(result, warnings)
    result.setdefault('language', 'en')
    result['metamodelVersion'] = str(target)
    if source.major < target.major:
        warnings.append(
            f'Descriptor upgraded from metamodel {source} to {target}. Jinja templates and step '
            f'options were written for the document context of {source.major}.x and are not '
            'migrated; check them against the changes of every major version in between.')
    return MigrationResult(data=result, source_version=source, warnings=warnings,
                           changed=result != data or bool(warnings))


def _upgrade_legacy_identity(data: dict[str, typing.Any], warnings: list[str]) -> None:
    organization_id = data.pop('organizationId', None)
    template_id = data.pop('templateId', None)
    composed = data.get('id')
    legacy = (parse_legacy_reference(composed)
              if isinstance(composed, str) and composed.count(':') == 2 else None)  # noqa: PLR2004
    if organization_id is not None and template_id is not None:
        data['id'] = join_legacy_id(organization_id, template_id)
        if legacy is not None and legacy[0] != data['id']:
            warnings.append(f"id '{composed}' disagrees with organizationId and templateId; "
                            f"kept '{data['id']}'.")
    elif legacy is not None:
        data['id'] = legacy[0]
    if legacy is not None:
        if 'version' not in data:
            data['version'] = legacy[1]
        elif data['version'] != legacy[1]:
            warnings.append(f"id '{composed}' disagrees with version '{data['version']}'; "
                            'kept version.')
    if isinstance(data.get('allowedPackages'), list):
        data['allowedPackages'] = [upgrade_legacy_package_pattern(pattern)
                                   for pattern in data['allowedPackages']]


def _drop_pre_11_fields(data: dict[str, typing.Any], warnings: list[str]) -> None:
    if data.pop('recommendedPackageId', None) is not None:
        warnings.append('Removed recommendedPackageId (metamodel 11); use allowedPackages instead.')
    for fmt in data.get('formats') or []:
        if isinstance(fmt, dict):
            for key in ('color', 'shortName'):
                fmt.pop(key, None)
