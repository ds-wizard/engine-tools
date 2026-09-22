"""Best-effort upgrade of older ``template.json`` descriptors to the current metamodel version.

The backend has no template migrations: it only accepts the same major version with a lower or
equal minor version. The steps below are derived from the published ``template.json`` schemas
(``ds-wizard/dsw-schemas``, versions 1–18.0) and the backend descriptor for 18.3:

========  =============================================================================
Version   Change
========  =============================================================================
11        ``formats[].color``, ``formats[].shortName`` and ``recommendedPackageId`` removed
17.0      ``metamodelVersion`` became a ``"major.minor"`` string
18.3      ``language`` added (default ``"en"``)
========  =============================================================================

Only the descriptor is upgraded. Jinja templates and step options were written for the document
context of their version and are not touched, so every major version crossed adds a warning.
"""
from __future__ import annotations

import copy
import dataclasses
import typing

from ..errors import MetamodelVersionError, MigrationError
from ..versions import DOCUMENT_TEMPLATE_METAMODEL_VERSION, MetamodelVersion


Kind = typing.Literal['local', 'bundle']


@dataclasses.dataclass(frozen=True, slots=True)
class MigrationResult:
    data: dict[str, typing.Any]
    source_version: MetamodelVersion
    warnings: list[str]
    #: the data differs from the input, or there is something to review
    changed: bool


def migrate_template_json(data: dict[str, typing.Any], *, kind: Kind = 'local') -> MigrationResult:
    """Upgrade a parsed ``template.json``; ``kind`` is the local descriptor or a package's one.

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
    _split_legacy_id(result, kind, warnings)
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


def _split_legacy_id(data: dict[str, typing.Any], kind: Kind, warnings: list[str]) -> None:
    legacy_id = data.get('id')
    if isinstance(legacy_id, str) and legacy_id.count(':') == 2:  # noqa: PLR2004
        organization_id, template_id, version = legacy_id.split(':')
        for key, value in (('organizationId', organization_id), ('templateId', template_id),
                           ('version', version)):
            if key not in data:
                data[key] = value
            elif data[key] != value:
                warnings.append(f"id '{legacy_id}' disagrees with {key} '{data[key]}'; kept {key}.")
    if kind == 'local':
        data.pop('id', None)
    elif all(key in data for key in ('organizationId', 'templateId', 'version')):
        data['id'] = f"{data['organizationId']}:{data['templateId']}:{data['version']}"


def _drop_pre_11_fields(data: dict[str, typing.Any], warnings: list[str]) -> None:
    if data.pop('recommendedPackageId', None) is not None:
        warnings.append('Removed recommendedPackageId (metamodel 11); use allowedPackages instead.')
    for fmt in data.get('formats') or []:
        if isinstance(fmt, dict):
            for key in ('color', 'shortName'):
                fmt.pop(key, None)
