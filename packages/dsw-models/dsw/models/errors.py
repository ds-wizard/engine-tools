class ModelsError(Exception):
    """Base class of all errors raised by dsw-models."""


class MetamodelVersionError(ModelsError):
    """Metamodel version is invalid or not supported."""


class MigrationError(ModelsError):
    """Content cannot be migrated to the current metamodel version."""
