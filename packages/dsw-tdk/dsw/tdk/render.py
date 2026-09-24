"""Rendering a local template project with dsw-templating, without any DSW instance."""
from __future__ import annotations

import dataclasses
import gettext
import io
import os
import typing
import uuid

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

from dsw.templating import (
    ContextDefaults,
    PandocSettings,
    RenderContext,
    RenderSettings,
    RequestsSettings,
    TemplateSettings,
    create_manager,
    enrich_context_config,
    register_plugin_steps,
)
from dsw.templating import Template as TemplateEngine
from dsw.templating.settings import bundled_pandoc_filters

from .model import TemplateFileType


if typing.TYPE_CHECKING:
    import pathlib

    from dsw.templating import DocumentFile

    from .model import Format, Template


class LocalAsset(typing.NamedTuple):
    uuid: str
    file_name: str
    content_type: str


class DirectoryProjectFiles:
    """Project files stored in a directory, named by their UUID or file name."""

    def __init__(self, root: pathlib.Path):
        self.root = root

    def resolve(self, file_uuid: str, name: str,
                content_type: str) -> pathlib.Path | None:
        for candidate in (self.root / file_uuid, self.root / name):
            if candidate.is_file():
                return candidate
        return None


def render_settings(*, pandoc_filters_dir: pathlib.Path | None = None,
                    pandoc_templates_dir: pathlib.Path | None = None,
                    secrets: dict[str, str] | None = None,
                    allow_requests: bool = False) -> RenderSettings:
    """Settings the document worker takes from its configuration.

    Filters are searched in `pandoc_filters_dir` first, then in the bundled
    ones. `secrets` and `requests` exist in templates only when configured
    (as in the worker, for a template with a configuration).
    """
    filter_dirs = [bundled_pandoc_filters()]
    if pandoc_filters_dir is not None:
        filter_dirs.insert(0, pandoc_filters_dir)
    template = None
    if secrets or allow_requests:
        template = TemplateSettings(
            secrets=secrets or {},
            requests=RequestsSettings(enabled=allow_requests),
        )
    return RenderSettings(
        pandoc=PandocSettings(filter_dirs=filter_dirs, templates_dir=pandoc_templates_dir),
        template=template,
    )


def find_format(template: Template, format_ref: str | None) -> Format:
    """Find a format by its UUID or name; the only format when not specified."""
    if format_ref is None:
        if len(template.formats) == 1:
            return template.formats[0]
        names = ', '.join(f'"{f.name}"' for f in template.formats)
        raise RuntimeError(f'The template has {len(template.formats)} formats, '
                           f'choose one of: {names}')
    for format_spec in template.formats:
        if format_ref in (format_spec.uuid, format_spec.name) or \
                format_ref.casefold() == (format_spec.name or '').casefold():
            return format_spec
    raise RuntimeError(f'Format "{format_ref}" not found in the template')


#: Keys of `documentContext` in the document worker configuration, with the
#: fields of ContextDefaults and the environment variables the worker reads
CONTEXT_DEFAULTS_KEYS: dict[str, tuple[str, str]] = {
    'serviceName': ('service_name', 'DOCUMENT_CONTEXT_SERVICE_NAME'),
    'serviceNameShort': ('service_name_short', 'DOCUMENT_CONTEXT_SERVICE_NAME_SHORT'),
    'serviceUrl': ('service_url', 'DOCUMENT_CONTEXT_SERVICE_URL'),
    'serviceDomainName': ('service_domain_name', 'DOCUMENT_CONTEXT_SERVICE_DOMAIN_NAME'),
    'defaultPrimaryColor': ('default_primary_color', 'DOCUMENT_CONTEXT_DEFAULT_PRIMARY_COLOR'),
    'defaultIllustrationsColor': ('default_illustrations_color',
                                  'DOCUMENT_CONTEXT_DEFAULT_ILLUSTRATIONS_COLOR'),
    'defaultLogoUrl': ('default_logo_url', 'DOCUMENT_CONTEXT_DEFAULT_LOGO_URL'),
    'defaultAppTitle': ('default_app_title', 'DOCUMENT_CONTEXT_DEFAULT_APP_TITLE'),
    'defaultAppTitleShort': ('default_app_title_short',
                             'DOCUMENT_CONTEXT_DEFAULT_APP_TITLE_SHORT'),
}


def context_defaults(overrides: dict[str, str] | None = None,
                     environ: typing.Mapping[str, str] = os.environ) -> ContextDefaults:
    """The worker's defaults, overridden by its environment variables and then `overrides`.

    `overrides` are keyed as `documentContext` in the worker configuration.
    """
    overrides = overrides or {}
    unknown = sorted(set(overrides) - set(CONTEXT_DEFAULTS_KEYS))
    if unknown:
        raise ValueError(f'Unknown context default {", ".join(unknown)} '
                         f'(known: {", ".join(CONTEXT_DEFAULTS_KEYS)})')
    values: dict[str, str] = {}
    for key, (field, var_name) in CONTEXT_DEFAULTS_KEYS.items():
        if key in overrides:
            values[field] = overrides[key]
        elif environ.get(var_name):
            values[field] = environ[var_name]
    return dataclasses.replace(ContextDefaults(), **values)


# What the document worker provides for a document without a project; the
# real values come from the database, which is not available locally.
EXTRAS_WITHOUT_PROJECT: dict[str, typing.Any] = {
    'submissions': [],
    'project': None,
    'questionnaire': None,
}


def requested_extras(format_spec: Format) -> list[str]:
    """Extras the steps of the format ask for (the ``extras`` step option)."""
    names: set[str] = set()
    for step in format_spec.steps:
        names.update(step.options.get('extras', '').split(','))
    return sorted(name for name in names if name in EXTRAS_WITHOUT_PROJECT)


def enrich_context(context: dict, format_spec: Format,
                   defaults: ContextDefaults | None = None) -> list[str]:
    """Add what the document worker adds to the context before rendering.

    ``config`` gets the service information and branding fallbacks (the
    worker's defaults), and extras requested by the format that the context
    does not provide are filled as for a document without a project. Returns
    the names of those extras.
    """
    context.setdefault('config', {})
    enrich_context_config(context, defaults or ContextDefaults())
    extras = context.setdefault('extras', {})
    missing = [name for name in requested_extras(format_spec) if name not in extras]
    for name in missing:
        extras[name] = EXTRAS_WITHOUT_PROJECT[name]
    return missing


def load_translations(po_file: pathlib.Path) -> gettext.GNUTranslations:
    """Compile a PO file (e.g. a translated POT file) for rendering."""
    with po_file.open('rb') as file:
        catalog = read_po(file)
    buffer = io.BytesIO()
    write_mo(buffer, catalog)
    buffer.seek(0)
    return gettext.GNUTranslations(buffer)


def _assets(template: Template) -> list[LocalAsset]:
    # only what is uploaded as an asset can be fetched as one on the server
    return [
        LocalAsset(
            uuid=file.remote_uuid or str(uuid.uuid5(uuid.NAMESPACE_URL, name)),
            file_name=name,
            content_type=file.content_type,
        )
        for name, file in template.files.items()
        if file.remote_type == TemplateFileType.ASSET
    ]


def prepare_directory(template: Template, target: pathlib.Path):
    """Write the files of the template as the server would have them."""
    for name, file in template.files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file.content)


def render_document(template: Template, *, workdir: pathlib.Path, format_uuid: str,
                    context: dict, render_ctx: RenderContext,
                    project_files: DirectoryProjectFiles | None = None,
                    settings: RenderSettings | None = None) -> DocumentFile:
    """Render the document from the template files, written into `workdir`."""
    prepare_directory(template, workdir)
    plugins = create_manager()
    register_plugin_steps(plugins)
    engine = TemplateEngine(
        template_dir=workdir,
        formats=[f.serialize() for f in template.formats],
        assets=_assets(template),
        template_uuid=template.uuid or template.coordinates,
        coordinates=template.coordinates,
        settings=settings or RenderSettings(),
        plugins=plugins,
    )
    return engine.render(format_uuid, context,
                         render_ctx=render_ctx, project_files=project_files)
