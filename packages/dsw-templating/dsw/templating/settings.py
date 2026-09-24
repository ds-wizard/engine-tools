"""Everything a rendering needs to know about its environment.

The caller (e.g. the document worker) maps its own configuration onto these;
the library never reads configuration files or environment variables itself.
"""
from __future__ import annotations

import dataclasses
import importlib.resources
import pathlib


def bundled_pandoc_filters() -> pathlib.Path:
    """Directory with the Pandoc filters shipped with this package."""
    resource = importlib.resources.files('dsw.templating') / 'resources' / 'pandoc' / 'filters'
    return pathlib.Path(str(resource))


@dataclasses.dataclass
class SecuritySettings:
    """Which URLs may be fetched while rendering (see `UrlPolicy`)."""
    allow_external_resources: bool = True
    allow_private_network: bool = False
    allowed_hosts: list[str] = dataclasses.field(default_factory=list)
    allowed_paths: list[str] = dataclasses.field(default_factory=list)
    max_redirects: int = 3


@dataclasses.dataclass
class PandocSettings:
    command: list[str] = dataclasses.field(default_factory=lambda: ['pandoc', '--standalone'])
    timeout: float | None = None
    #: searched in order for a filter name, the first directory having it wins
    filter_dirs: list[pathlib.Path] = dataclasses.field(
        default_factory=lambda: [bundled_pandoc_filters()],
    )
    templates_dir: pathlib.Path | None = None

    def filter_path(self, name: str) -> pathlib.Path | None:
        for filter_dir in self.filter_dirs:
            path = filter_dir / name
            if path.is_file():
                return path
        return None

    def template_path(self, name: str) -> pathlib.Path | None:
        if self.templates_dir is None:
            return None
        path = self.templates_dir / name
        return path if path.is_file() else None


@dataclasses.dataclass
class RequestsSettings:
    """HTTP requests from Jinja templates (the `requests` global)."""
    enabled: bool = False
    limit: int = 100
    timeout: int = 1


@dataclasses.dataclass
class TemplateSettings:
    """Per-template settings; templates without them get no `secrets` global."""
    secrets: dict[str, str] = dataclasses.field(default_factory=dict)
    requests: RequestsSettings = dataclasses.field(default_factory=RequestsSettings)


@dataclasses.dataclass
class RenderSettings:
    security: SecuritySettings = dataclasses.field(default_factory=SecuritySettings)
    pandoc: PandocSettings = dataclasses.field(default_factory=PandocSettings)
    template: TemplateSettings | None = None
