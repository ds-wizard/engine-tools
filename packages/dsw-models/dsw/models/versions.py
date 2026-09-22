from __future__ import annotations

import typing

from .errors import MetamodelVersionError


class MetamodelVersion(typing.NamedTuple):
    """Two-part metamodel version, written as ``"major.minor"`` (backend ``SemVer2Tuple``)."""

    major: int
    minor: int = 0

    @classmethod
    def parse(cls, value: str | int | MetamodelVersion) -> MetamodelVersion:
        if isinstance(value, MetamodelVersion):
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return cls(major=value)
        if isinstance(value, str):
            parts = value.strip().split('.')
            if 1 <= len(parts) <= 2 and all(part.isdigit() for part in parts):
                return cls(*(int(part) for part in parts))
        raise MetamodelVersionError(f'Invalid metamodel version: {value!r}')

    def supports(self, other: MetamodelVersion) -> bool:
        """True if content of version ``other`` can be used by this version."""
        return self.major == other.major and other.minor <= self.minor

    def __str__(self) -> str:
        return f'{self.major}.{self.minor}'


KM_METAMODEL_VERSION = 20
DOCUMENT_TEMPLATE_METAMODEL_VERSION = MetamodelVersion(18, 3)
