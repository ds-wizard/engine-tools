from __future__ import annotations

import importlib
import typing


if typing.TYPE_CHECKING:
    import types


class TemplateError(Exception):

    def __init__(self, template_uuid: str, message: str):
        self.template_uuid = template_uuid
        self.message = message

    def __str__(self):
        return f'Error in template "{self.template_uuid}"\n' \
               f'- {self.message}'


class TemplateTriggeredError(Exception):
    """Error invoked from a template to report a problem to a user (not system)."""

    def __init__(self, title, message):
        self.title = title
        self.message = message
        self.msg = f'{title}\n\n{message}'
        super().__init__(self.msg)

    def __str__(self):
        return self.msg


class MissingExtraError(ImportError):
    """An optional dependency of a step is not installed."""

    def __init__(self, module: str, extra: str):
        self.module = module
        self.extra = extra
        super().__init__(
            f'Module "{module}" is not installed, '
            f'install dsw-templating[{extra}] to use it',
            name=module,
        )


def require(module: str, extra: str) -> types.ModuleType:
    """Import an optional dependency, failing with the extra to install."""
    try:
        return importlib.import_module(module)
    except ImportError as e:
        raise MissingExtraError(module, extra) from e


class MissingModule:
    """Stands in for an optional module; fails as soon as it is used."""

    def __init__(self, module: str, extra: str):
        self._module = module
        self._extra = extra

    def __getattr__(self, name: str):
        raise MissingExtraError(self._module, self._extra)


def optional(module: str, extra: str) -> types.ModuleType | MissingModule:
    try:
        return importlib.import_module(module)
    except ImportError:
        return MissingModule(module, extra)
