"""Identity of library content: knowledge model packages, document templates and locales.

Since Wizard 5.0 an item is identified by a single ``id`` (characters ``[a-zA-Z0-9._-]``) and a
``version``. The ``reference`` ``<id>:<version>`` is computed only and is not part of any wire
model. Before 5.0 the identity was ``organizationId`` + ``kmId`` / ``templateId`` / ``localeId``
and the composed reference was ``<organizationId>:<entityId>:<version>``; such data is read by
joining the two ids into ``<organizationId>.<entityId>``.

Port of the backend ``Shared.Util.Reference`` and ``Shared.Api.Resource.Coordinate.CoordinateJM``.
"""
from __future__ import annotations

import typing


_REFERENCE_PARTS = 2
_LEGACY_REFERENCE_PARTS = 3


def join_legacy_id(organization_id: str, entity_id: str) -> str:
    return f'{organization_id}.{entity_id}'


def build_reference(id: str, version: str) -> str:  # noqa: A002
    return f'{id}:{version}'


def parse_reference(reference: str) -> tuple[str, str] | None:
    """``<id>:<version>`` as ``(id, version)``."""
    parts = reference.split(':')
    if len(parts) != _REFERENCE_PARTS:
        return None
    return parts[0], parts[1]


def parse_legacy_reference(reference: str) -> tuple[str, str] | None:
    """Like :func:`parse_reference`, also accepting ``<organizationId>:<entityId>:<version>``."""
    parts = reference.split(':')
    if len(parts) == _LEGACY_REFERENCE_PARTS:
        return join_legacy_id(parts[0], parts[1]), parts[2]
    return parse_reference(reference)


def upgrade_legacy_id(data: dict[str, typing.Any], entity_id_key: str) -> None:
    """Replace ``organizationId`` + ``entity_id_key`` by the joined ``id``, in place."""
    organization_id = data.pop('organizationId', None)
    entity_id = data.pop(entity_id_key, None)
    if organization_id is not None and entity_id is not None:
        data['id'] = join_legacy_id(organization_id, entity_id)


def upgrade_legacy_coordinate(data: dict[str, typing.Any], prefix: str) -> None:
    """Split a legacy ``<prefix>Id`` reference into ``<prefix>Id`` + ``<prefix>Version``, in place.

    A reference that cannot be parsed reads as no coordinate, as in the backend.
    """
    id_key, version_key = f'{prefix}Id', f'{prefix}Version'
    reference = data.get(id_key)
    if not isinstance(reference, str) or data.get(version_key) is not None:
        return
    coordinate = parse_legacy_reference(reference)
    data[id_key], data[version_key] = coordinate if coordinate is not None else (None, None)
