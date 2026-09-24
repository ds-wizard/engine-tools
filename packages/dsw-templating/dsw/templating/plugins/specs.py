from __future__ import annotations

import typing

import pluggy

from .. import consts


if typing.TYPE_CHECKING:
    from jinja2 import Environment

    from ..steps import Step


hookspec = pluggy.HookspecMarker(consts.PACKAGE_NAME)
hookimpl = pluggy.HookimplMarker(consts.PACKAGE_NAME)


@hookspec
def provide_steps() -> dict[str, type[Step]]:
    """
    Provide a dictionary of steps that the plugin can execute.

    Steps are used to process the document generation in a specific way. Each step
    must comply with the interface of the provided `Step` class. The plugin must make
    sure to return a list of steps that it can execute and in compliance with the
    `Step` class in the current implementation (use correct dsw-templating as
    a dependency). Plugins are loaded from the `dsw_templating_plugins` entry point
    and their steps are registered by `register_plugin_steps`.

    Before the format pipeline runs, every step gets `before_render(render_ctx)` called
    with the `RenderContext` of the document. The base implementation stores it, so a
    step that does not override it still has `self.translations`, `self.language` and
    the `self.gettext` / `self.ngettext` / `self.pgettext` helpers available. A step
    that overrides `before_render` must call `super().before_render(render_ctx)`.

    :return: a dictionary of steps that the plugin can execute
    """
    return {}


@hookspec
def enrich_document_context(context: dict) -> None:
    """
    Enrich the document context with custom data.

    The plugin can enrich the provided document context with custom data that can be
    used in the document generation process. The context is a dictionary that is passed
    to each step during the document generation process. The plugin can manipulate the
    context in any way it sees fit.

    :param context: the document context to enrich
    """


@hookspec
def enrich_jinja_env(jinja_env: Environment, options: dict[str, str]) -> None:
    """
    Enrich the Jinja environment with custom filters, tests, policies, etc.

    The plugin can enrich the provided Jinja environment with custom features like
    filters, tests, policies, global variables and other. It can manipulate the Jinja
    environment in any way it sees fit but should ensure that the environment is safe
    to use in the document generation process. This Jinja environment is used within
    all steps that are subclass of the `JinjaPoweredStep` (mainly the `jinja` step
    implemented in class `Jinja2Step`).

    The `jinja2.ext.i18n` extension is always enabled and its `gettext`, `ngettext`,
    `pgettext` and `npgettext` globals are re-installed before every rendering. The
    plugin must not provide globals with these names; to work with translations, it
    should override `Step.before_render` instead.

    :param jinja_env: the Jinja environment to enrich
    :param options: the options provided to the step
    """

