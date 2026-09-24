"""Rendering of DSW document templates, without any services behind it."""
from .consts import VERSION
from .context import ContextDefaults, enrich_context_config
from .documents import DocumentFile, FileFormat, FileFormats
from .exceptions import MissingExtraError, TemplateError, TemplateTriggeredError
from .formats import Format
from .locales import RenderContext, TemplateLocale
from .plugins import create_manager, hookimpl, hookspec, register_plugin_steps
from .settings import (
    PandocSettings,
    RenderSettings,
    RequestsSettings,
    SecuritySettings,
    TemplateSettings,
)
from .steps import FormatStepError, Step
from .steps.base import register_step
from .template import Asset, AssetMetadata, ProjectFileResolver, Template


__all__ = [
    'VERSION',
    'ContextDefaults', 'enrich_context_config',
    'Asset', 'AssetMetadata', 'ProjectFileResolver', 'Template',
    'DocumentFile', 'FileFormat', 'FileFormats',
    'Format', 'FormatStepError', 'Step', 'register_step',
    'MissingExtraError', 'TemplateError', 'TemplateTriggeredError',
    'RenderContext', 'TemplateLocale',
    'PandocSettings', 'RenderSettings', 'RequestsSettings', 'SecuritySettings',
    'TemplateSettings',
    'create_manager', 'hookimpl', 'hookspec', 'register_plugin_steps',
]
