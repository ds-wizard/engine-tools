from __future__ import annotations

import base64
import json
import logging
import mimetypes
import typing
import uuid

from . import consts
from .exceptions import TemplateError
from .formats import Format
from .locales import RenderContext
from .settings import RenderSettings


if typing.TYPE_CHECKING:
    import pathlib
    from collections.abc import Iterable

    from pluggy import PluginManager

    from dsw.models.document_context.graph import ProjectFile

    from .documents import DocumentFile


LOG = logging.getLogger(__name__)


class AssetMetadata(typing.Protocol):
    """A template asset as registered with the template (e.g. in a database)."""

    @property
    def uuid(self) -> str: ...

    @property
    def file_name(self) -> str: ...

    @property
    def content_type(self) -> str: ...


class LocalAsset(typing.NamedTuple):
    uuid: str
    file_name: str
    content_type: str


class ProjectFileResolver(typing.Protocol):
    """Provides the content of a file uploaded to the project being rendered.

    Returns the content, a path to a local file holding it, or None when the
    file cannot be retrieved.
    """

    def resolve(self, file_uuid: str, name: str,
                content_type: str) -> bytes | pathlib.Path | None: ...


class Asset:

    def __init__(self, *, uuid: str, name: str, content_type: str,
                 data: bytes, path: pathlib.Path):
        self.uuid = uuid
        self.name = name
        self.content_type = content_type
        self.data = data
        self.path = path

    @property
    def is_image(self) -> bool:
        return self.content_type.startswith('image/')

    @property
    def data_base64(self) -> str:
        return base64.b64encode(self.data).decode('ascii')

    @property
    def data_url(self) -> str:
        return f'data:{self.content_type};base64,{self.data_base64}'

    @property
    def src_value(self):
        return self.data_url


class Template:
    """A document template on disk, rendered by one of its formats.

    Everything the rendering depends on is passed in: the template directory
    and its metadata, `RenderSettings`, the plugin manager and, per rendering,
    the `RenderContext` with translations and a `ProjectFileResolver`.
    """

    def __init__(self, *, template_dir: pathlib.Path, formats: list[dict],
                 assets: Iterable[AssetMetadata] = (), template_uuid: str = '',
                 coordinates: str = '', settings: RenderSettings | None = None,
                 plugins: PluginManager | None = None):
        self.template_dir = template_dir
        self.formats_metadata = formats
        self.assets: list[AssetMetadata] = list(assets)
        self.template_uuid = template_uuid
        self.coordinates = coordinates
        self.settings = settings or RenderSettings()
        if plugins is None:
            from .plugins import create_manager
            plugins = create_manager()
        self.plugins = plugins

        self.formats: dict[str, Format] = {}
        self.render_ctx = RenderContext.null()
        self._project_files: ProjectFileResolver | None = None

    @classmethod
    def from_directory(cls, template_dir: pathlib.Path, **kwargs) -> Template:
        """Load a template from its directory with ``template.json``.

        Every other file in the directory is an asset, with its content type
        guessed from the file name.
        """
        from dsw.models.document_template.metadata import DocumentTemplateMetadata
        from dsw.models.strictness import UnknownKeys, load

        metadata_file = template_dir / consts.TEMPLATE_JSON_FILE_NAME
        metadata = load(
            DocumentTemplateMetadata,
            json.loads(metadata_file.read_text(encoding=consts.DEFAULT_ENCODING)),
            unknown_keys=UnknownKeys.IGNORE,
        )
        assets = []
        for path in sorted(template_dir.rglob('*')):
            file_name = path.relative_to(template_dir).as_posix()
            if not path.is_file() or file_name == consts.TEMPLATE_JSON_FILE_NAME:
                continue
            assets.append(LocalAsset(
                uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, file_name)),
                file_name=file_name,
                content_type=mimetypes.guess_type(file_name)[0] or 'application/octet-stream',
            ))
        kwargs.setdefault('assets', assets)
        kwargs.setdefault('coordinates', metadata.coordinate)
        return cls(
            template_dir=template_dir,
            formats=[f.model_dump(mode='json', by_alias=True) for f in metadata.formats],
            **kwargs,
        )

    def raise_exc(self, message: str):
        raise TemplateError(self.template_uuid, message)

    def fetch_asset(self, file_name: str) -> Asset | None:
        LOG.info('Fetching asset "%s"', file_name)
        file_path = self.template_dir / file_name
        asset = None
        for a in self.assets:
            if a.file_name == file_name:
                asset = a
                break
        if asset is None or not file_path.exists():
            LOG.error('Asset "%s" not found', file_name)
            return None
        return Asset(
            uuid=asset.uuid,
            name=file_name,
            content_type=asset.content_type,
            data=file_path.read_bytes(),
            path=file_path,
        )

    def fetch_project_file(self, file: ProjectFile) -> Asset | None:
        return self._fetch_project_file(
            file_uuid=file.uuid,
            name=file.name,
            content_type=file.content_type,
        )

    def fetch_project_file_dict(self, file: dict) -> Asset | None:
        file_uuid = file.get('uuid')
        name = file.get('fileName')
        content_type = file.get('contentType')
        if isinstance(file_uuid, str) and isinstance(name, str) and isinstance(content_type, str):
            return self._fetch_project_file(
                file_uuid=file_uuid,
                name=name,
                content_type=content_type,
            )
        return None

    def _fetch_project_file(self, file_uuid: str, name: str,
                            content_type: str) -> Asset | None:
        LOG.info('Fetching project file "%s"', file_uuid)
        if self._project_files is None:
            LOG.warning('No project files available, cannot fetch project file')
            return None
        result = self._project_files.resolve(file_uuid, name, content_type)
        if result is None:
            LOG.error('Project file "%s" cannot be retrieved', file_uuid)
            return None
        if isinstance(result, bytes):
            file_path = self.template_dir / consts.PROJECT_FILES_DIR / file_uuid
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(result)
        else:
            file_path = result
        return Asset(
            uuid=file_uuid,
            name=name,
            content_type=content_type,
            data=file_path.read_bytes(),
            path=file_path,
        )

    def asset_path(self, filename: str) -> str:
        return str(self.template_dir / filename)

    def prepare_format(self, format_uuid: str) -> bool:
        for format_meta in self.formats_metadata:
            if format_uuid == format_meta.get(consts.FormatField.UUID):
                self.formats[format_uuid] = Format(self, format_meta)
                return True
        return False

    def has_format(self, format_uuid: str) -> bool:
        return any(
            f[consts.FormatField.UUID] == format_uuid
            for f in self.formats_metadata
        )

    def __getitem__(self, format_uuid: str) -> Format:
        return self.formats[format_uuid]

    def render(self, format_uuid: str, context: dict, *,
               render_ctx: RenderContext | None = None,
               project_files: ProjectFileResolver | None = None) -> DocumentFile:
        """Render the document with the (prepared) format.

        The format is prepared on the first use if `prepare_format` has not
        been called. The document context may be enriched by plugins.
        """
        if format_uuid not in self.formats and not self.prepare_format(format_uuid):
            self.raise_exc(f'Format {format_uuid} not found')
        self.plugins.hook.enrich_document_context(context=context)

        self.render_ctx = RenderContext.null() if render_ctx is None else render_ctx
        self._project_files = project_files
        try:
            return self[format_uuid].execute(context)
        finally:
            self._project_files = None
