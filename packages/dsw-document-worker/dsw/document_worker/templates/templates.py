from __future__ import annotations

import dataclasses
import datetime
import logging
import os
import pathlib
import shutil
import typing

from dsw.templating import (
    PandocSettings,
    RenderContext,
    RenderSettings,
    RequestsSettings,
    SecuritySettings,
    TemplateSettings,
    register_plugin_steps,
)
from dsw.templating import Template as TemplateEngine
from dsw.templating.settings import bundled_pandoc_filters

from .. import consts
from ..context import Context
from .locales import LocaleLoader


if typing.TYPE_CHECKING:
    from dsw.database.model import (
        DBDocumentTemplate,
        DBDocumentTemplateAsset,
        DBDocumentTemplateFile,
    )
    from dsw.templating import DocumentFile, Format, TemplateLocale

    from ..config import DocumentWorkerConfig


LOG = logging.getLogger(__name__)


def render_settings(cfg: DocumentWorkerConfig, coordinates: str) -> RenderSettings:
    """Map the worker configuration onto what the rendering of a template needs."""
    template_cfg = cfg.templates.get_config(coordinates)
    template_settings = None
    if template_cfg is not None:
        template_settings = TemplateSettings(
            secrets=template_cfg.secrets,
            requests=RequestsSettings(
                enabled=template_cfg.requests.enabled,
                limit=template_cfg.requests.limit,
                timeout=template_cfg.requests.timeout,
            ),
        )
    return RenderSettings(
        security=SecuritySettings(
            allow_external_resources=cfg.security.allow_external_resources,
            allow_private_network=cfg.security.allow_private_network,
            allowed_hosts=cfg.security.allowed_hosts,
            allowed_paths=cfg.security.allowed_paths,
            max_redirects=cfg.security.max_redirects,
        ),
        pandoc=PandocSettings(
            command=cfg.pandoc.command,
            timeout=cfg.pandoc.timeout,
            # deployments may add their own filters and templates there
            filter_dirs=[
                pathlib.Path(os.getenv('PANDOC_FILTERS', '/pandoc/filters')),
                bundled_pandoc_filters(),
            ],
            templates_dir=pathlib.Path(os.getenv('PANDOC_TEMPLATES', '/pandoc/templates')),
        ),
        template=template_settings,
    )


class S3ProjectFiles:
    """Project files of one project, downloaded from S3 into the template directory."""

    def __init__(self, *, tenant_uuid: str, project_uuid: str | None, cache_dir: pathlib.Path):
        self.tenant_uuid = tenant_uuid
        self.project_uuid = project_uuid
        self.cache_dir = cache_dir

    def resolve(self, file_uuid: str, name: str,
                content_type: str) -> pathlib.Path | None:
        if self.project_uuid is None:
            LOG.warning('Project UUID is not set, cannot fetch project file')
            return None
        file_path = self.cache_dir / file_uuid
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            result = Context.get().app.s3.download_project_file(
                tenant_uuid=self.tenant_uuid,
                project_uuid=self.project_uuid,
                file_uuid=file_uuid,
                target_path=file_path,
            )
            if not result:
                return None
        return file_path


@dataclasses.dataclass
class TemplateComposite:
    template: DBDocumentTemplate
    files: dict[str, DBDocumentTemplateFile]
    assets: dict[str, DBDocumentTemplateAsset]


class Template:
    """Local copy of a document template from the database, rendered by dsw-templating."""

    def __init__(self, tenant_uuid: str, template_dir: pathlib.Path,
                 db_template: TemplateComposite):
        ctx = Context.get()
        self.tenant_uuid = tenant_uuid
        self.template_dir = template_dir
        self.last_used = datetime.datetime.now(tz=datetime.UTC)
        self.db_template = db_template
        self.template_uuid = self.db_template.template.uuid
        self.coordinates = self.db_template.template.coordinates

        self.engine = TemplateEngine(
            template_dir=template_dir,
            formats=self.db_template.template.formats,
            assets=self.db_template.assets.values(),
            template_uuid=self.template_uuid,
            coordinates=self.coordinates,
            settings=render_settings(ctx.app.cfg, self.coordinates),
            plugins=ctx.app.pm,
        )
        self.render_ctx = RenderContext.null()
        self._locale_loader = LocaleLoader(
            cache_dir=template_dir / consts.LOCALES_CACHE_DIR,
            tenant_uuid=tenant_uuid,
        )

    @property
    def formats(self) -> dict[str, Format]:
        return self.engine.formats

    def _store_asset(self, asset: DBDocumentTemplateAsset):
        LOG.debug('Storing asset %s (%s)', asset.uuid, asset.file_name)
        local_path = self.template_dir / asset.file_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        result = Context.get().app.s3.download_template_asset(
            tenant_uuid=self.tenant_uuid,
            template_uuid=self.db_template.template.uuid,
            file_name=asset.uuid,
            target_path=local_path,
        )
        if not result:
            LOG.error('Asset "%s" cannot be retrieved', local_path.name)

    def _store_file(self, file: DBDocumentTemplateFile):
        LOG.debug('Storing file %s (%s)', file.uuid, file.file_name)
        local_path = self.template_dir / file.file_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(
            data=file.content,
            encoding='utf-8',
        )

    def _delete_asset(self, asset: DBDocumentTemplateAsset):
        LOG.debug('Deleting asset %s (%s)', asset.uuid, asset.file_name)
        local_path = self.template_dir / asset.file_name
        local_path.unlink(missing_ok=True)

    def _delete_file(self, file: DBDocumentTemplateFile):
        LOG.debug('Deleting file %s (%s)', file.uuid, file.file_name)
        local_path = self.template_dir / file.file_name
        local_path.unlink(missing_ok=True)

    def _update_asset(self, asset: DBDocumentTemplateAsset):
        LOG.debug('Updating asset %s (%s)', asset.uuid, asset.file_name)
        old_asset = self.db_template.assets[asset.uuid]
        local_path = self.template_dir / asset.file_name
        if old_asset.updated_at == asset.updated_at and local_path.exists():
            LOG.debug('- Asset %s (%s) did not change', asset.uuid, asset.file_name)
            return
        self._store_asset(asset)

    def _update_file(self, file: DBDocumentTemplateFile):
        LOG.debug('Updating file %s (%s)', file.uuid, file.file_name)
        old_file = self.db_template.files[file.uuid]
        local_path = self.template_dir / file.file_name
        if old_file.updated_at == file.updated_at and local_path.exists():
            LOG.debug('- File %s (%s) did not change', file.uuid, file.file_name)
            return
        self._store_file(file)

    def prepare_all_template_files(self):
        LOG.info('Storing all files of template %s locally', self.template_uuid)
        for file in self.db_template.files.values():
            self._store_file(file)

    def prepare_all_template_assets(self):
        LOG.info('Storing all assets of template %s locally', self.template_uuid)
        for asset in self.db_template.assets.values():
            self._store_asset(asset)

    def prepare_fs(self):
        LOG.info('Preparing directory for template %s', self.template_uuid)
        if self.template_dir.exists():
            shutil.rmtree(self.template_dir)
        self.template_dir.mkdir(parents=True)
        self.prepare_all_template_files()
        self.prepare_all_template_assets()

    @staticmethod
    def _resolve_change(old_keys: frozenset[str], new_keys: frozenset[str]):
        to_add = new_keys.difference(old_keys)
        to_del = old_keys.difference(new_keys)
        to_chk = old_keys.intersection(new_keys)
        return to_add, to_del, to_chk

    def update_template_files(self, db_files: dict[str, DBDocumentTemplateFile]):
        LOG.info('Updating files of template %s', self.template_uuid)
        to_add, to_del, to_chk = self._resolve_change(
            old_keys=frozenset(self.db_template.files.keys()),
            new_keys=frozenset(db_files.keys()),
        )
        for file_uuid in to_del:
            self._delete_file(self.db_template.files[file_uuid])
        for file_uuid in to_add:
            self._store_file(db_files[file_uuid])
        for file_uuid in to_chk:
            self._update_file(db_files[file_uuid])
        self.db_template.files = db_files

    def update_template_assets(self, db_assets: dict[str, DBDocumentTemplateAsset]):
        LOG.info('Updating assets of template %s', self.template_uuid)
        to_add, to_del, to_chk = self._resolve_change(
            old_keys=frozenset(self.db_template.assets.keys()),
            new_keys=frozenset(db_assets.keys()),
        )
        for asset_uuid in to_del:
            self._delete_asset(self.db_template.assets[asset_uuid])
        for asset_uuid in to_add:
            self._store_asset(db_assets[asset_uuid])
        for asset_uuid in to_chk:
            self._update_asset(db_assets[asset_uuid])
        self.db_template.assets = db_assets
        self.engine.assets = list(db_assets.values())

    def update_template(self, db_template: TemplateComposite):
        self.db_template.template = db_template.template
        self.engine.formats_metadata = db_template.template.formats
        if not self.template_dir.exists():
            self.template_dir.mkdir()
        self.update_template_files(db_template.files)
        self.update_template_assets(db_template.assets)

    def prepare_locale(self, *, language: str | None, locale: TemplateLocale | None):
        if locale is None:
            LOG.info('No locale for template %s - using null translations', self.template_uuid)
            self.render_ctx = RenderContext.null(language=language)
            return
        LOG.info('Loading locale %s (%s) for template %s',
                 locale.uuid, locale.code, self.template_uuid)
        self.render_ctx = RenderContext(
            translations=self._locale_loader.load(locale),
            language=language,
            locale=locale,
        )

    def prepare_format(self, format_uuid: str) -> bool:
        return self.engine.prepare_format(format_uuid)

    def has_format(self, format_uuid: str) -> bool:
        return self.engine.has_format(format_uuid)

    def __getitem__(self, format_uuid: str) -> Format:
        return self.engine[format_uuid]

    def render(self, format_uuid: str, project_uuid: str | None,
               context: dict) -> DocumentFile:
        self.last_used = datetime.datetime.now(tz=datetime.UTC)
        return self.engine.render(
            format_uuid,
            context,
            render_ctx=self.render_ctx,
            project_files=S3ProjectFiles(
                tenant_uuid=self.tenant_uuid,
                project_uuid=project_uuid,
                cache_dir=self.template_dir / 'project-files',
            ),
        )


class TemplateRegistry:

    _instance = None

    @classmethod
    def get(cls) -> TemplateRegistry:
        if cls._instance is None:
            cls._instance = TemplateRegistry()
        return cls._instance

    def __init__(self):
        self._templates: dict[str, dict[str, Template]] = {}
        register_plugin_steps(Context.get().app.pm)

    def has_template(self, tenant_uuid: str, template_uuid: str) -> bool:
        return tenant_uuid in self._templates and \
               template_uuid in self._templates[tenant_uuid]

    def _set_template(self, tenant_uuid: str, template_uuid: str, template: Template):
        if tenant_uuid not in self._templates:
            self._templates[tenant_uuid] = {}
        self._templates[tenant_uuid][template_uuid] = template

    def get_template(self, tenant_uuid: str, template_uuid: str) -> Template:
        return self._templates[tenant_uuid][template_uuid]

    def _init_new_template(self, tenant_uuid: str, template_uuid: str,
                           db_template: TemplateComposite):
        workdir = Context.get().app.workdir
        template_dir = workdir / tenant_uuid / str(template_uuid)
        template = Template(
            tenant_uuid=tenant_uuid,
            template_dir=template_dir,
            db_template=db_template,
        )
        template.prepare_fs()
        self._set_template(tenant_uuid, template_uuid, template)

    def _refresh_template(self, tenant_uuid: str, template_uuid: str,
                          db_template: TemplateComposite):
        template = self.get_template(tenant_uuid, template_uuid)
        template.update_template(db_template)

    def prepare_template(self, tenant_uuid: str, template_uuid: str) -> Template:
        ctx = Context.get()
        query_args = {
            'template_uuid': template_uuid,
            'tenant_uuid': tenant_uuid,
        }
        db_template = ctx.app.db.fetch_template(**query_args)
        if db_template is None:
            raise RuntimeError(f'Template {template_uuid} not found in database')
        db_files = ctx.app.db.fetch_template_files(**query_args)
        db_assets = ctx.app.db.fetch_template_assets(**query_args)
        template_composite = TemplateComposite(
            template=db_template,
            files={f.uuid: f for f in db_files},
            assets={f.uuid: f for f in db_assets},
        )

        if self.has_template(tenant_uuid, template_uuid):
            self._refresh_template(tenant_uuid, template_uuid, template_composite)
        else:
            self._init_new_template(tenant_uuid, template_uuid, template_composite)

        return self.get_template(tenant_uuid, template_uuid)

    def _clear_template(self, tenant_uuid: str, template_uuid: str):
        template = self._templates[tenant_uuid].pop(template_uuid)
        if template.template_dir.exists():
            shutil.rmtree(template.template_dir)

    def cleanup(self):
        threshold = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=7)
        for tenant_uuid, templates in self._templates.items():
            for template_uuid, template in templates.items():
                if template.last_used < threshold:
                    self._clear_template(tenant_uuid, template_uuid)
