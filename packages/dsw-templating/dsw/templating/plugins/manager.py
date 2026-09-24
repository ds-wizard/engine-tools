from __future__ import annotations

import typing

import pluggy

from .. import consts
from ..steps.base import Step, register_step


def create_manager() -> pluggy.PluginManager:
    """Plugin manager with every plugin installed under the entry point."""
    from . import specs as hookspecs

    pm = pluggy.PluginManager(consts.PACKAGE_NAME)
    pm.load_setuptools_entrypoints(consts.PLUGINS_ENTRYPOINT)
    pm.add_hookspecs(hookspecs)
    return pm


def register_plugin_steps(pm: pluggy.PluginManager):
    """Register the steps provided by plugins, alongside the built-in ones."""
    steps_dicts: typing.Iterable[dict[str, type[Step]]] = pm.hook.provide_steps()
    for steps_dict in steps_dicts:
        for name, step_class in steps_dict.items():
            if not issubclass(step_class, Step):
                raise RuntimeError(f'Provided class "{step_class}" is not a subclass of Step')
            register_step(name, step_class)
