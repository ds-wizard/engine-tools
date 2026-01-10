import base64
import dataclasses
import datetime
import logging
import pathlib
import shutil

from dsw.database.database import DBDocumentTemplate, \
    DBDocumentTemplateFile, DBDocumentTemplateAsset

from ..consts import FormatField
from ..context import Context
from ..documents import DocumentFile
from .formats import Format
from ..model.context import ProjectFile
from .steps.base import register_step, Step


LOG = logging.getLogger(__name__)


class TemplateException(Exception):

    def __init__(self, template_id: str, message: str):
        self.template_id = template_id
        self.message = message

    def __str__(self):
        return f'Error in template "{self.template_id}"\n' \
               f'- {self.message}'


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


@dataclasses.dataclass
class TemplateComposite:
    template: DBDocumentTemplate
    files: dict[str, DBDocumentTemplateFile]
    assets: dict[str, DBDocumentTemplateAsset]


class Template:

    def __init__(self, tenant_uuid: str, template_dir: pathlib.Path,
                 db_template: TemplateComposite):
        self.tenant_uuid = tenant_uuid
        self.template_dir = template_dir
        self.last_used = datetime.datetime.now(tz=datetime.UTC)
        self.db_template = db_template
        self.template_id = self.db_template.template.id

        self.formats: dict[str, Format] = {}
        self.project_uuid: str | None = None

    def raise_exc(self, message: str):
        raise TemplateException(self.template_id, message)

    def fetch_asset(self, file_name: str) -> Asset | None:
        LOG.info('Fetching asset "%s"', file_name)
        file_path = self.template_dir / file_name
        asset = None
        for a in self.db_template.assets.values():
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
        file_uuid = file.get('uuid', None)
        name = file.get('fileName', None)
        content_type = file.get('contentType', None)
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
        if self.project_uuid is None:
            LOG.warning('Project UUID is not set, cannot fetch project file')
            return None
        file_path = self.template_dir / 'project-files' / file_uuid
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
                LOG.error('Project file "%s" cannot be retrieved', file_uuid)
                return None
        return Asset(
            uuid=file_uuid,
            name=name,
            content_type=content_type,
            data=file_path.read_bytes(),
            path=file_path,
        )

    def asset_path(self, filename: str) -> str:
        return str(self.template_dir / filename)

    def _store_asset(self, asset: DBDocumentTemplateAsset):
        LOG.debug('Storing asset %s (%s)', asset.uuid, asset.file_name)
        local_path = self.template_dir / asset.file_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        result = Context.get().app.s3.download_template_asset(
            tenant_uuid=self.tenant_uuid,
            template_id=self.db_template.template.id,
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
        LOG.info('Storing all files of template %s locally', self.template_id)
        for file in self.db_template.files.values():
            self._store_file(file)

    def prepare_all_template_assets(self):
        LOG.info('Storing all assets of template %s locally', self.template_id)
        for asset in self.db_template.assets.values():
            self._store_asset(asset)

    def prepare_fs(self):
        LOG.info('Preparing directory for template %s', self.template_id)
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
        LOG.info('Updating files of template %s', self.template_id)
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
        LOG.info('Updating assets of template %s', self.template_id)
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

    def update_template(self, db_template: TemplateComposite):
        self.db_template.template = db_template.template
        if not self.template_dir.exists():
            self.template_dir.mkdir()
        self.update_template_files(db_template.files)
        self.update_template_assets(db_template.assets)

    def prepare_format(self, format_uuid: str):
        for format_meta in self.db_template.template.formats:
            if format_uuid == format_meta.get(FormatField.UUID, None):
                self.formats[format_uuid] = Format(self, format_meta)
                return True
        return False

    def has_format(self, format_uuid: str) -> bool:
        return any(map(
            lambda f: f[FormatField.UUID] == format_uuid,
            self.db_template.template.formats
        ))

    def __getitem__(self, format_uuid: str) -> Format:
        return self.formats[format_uuid]

    def render(self, format_uuid: str, project_uuid: str | None,
               context: dict) -> DocumentFile:
        Context.get().app.pm.hook.enrich_document_context(context=context)

        self.last_used = datetime.datetime.now(tz=datetime.UTC)
        self.project_uuid = project_uuid
        result = self[format_uuid].execute(context)
        self.project_uuid = None
        return result


class TemplateRegistry:

    _instance = None

    @classmethod
    def get(cls) -> 'TemplateRegistry':
        if cls._instance is None:
            cls._instance = TemplateRegistry()
        return cls._instance

    def __init__(self):
        self._templates: dict[str, dict[str, Template]] = {}
        self._load_plugin_steps()

    def _load_plugin_steps(self):
        for steps_dict in Context.get().app.pm.hook.provide_steps():
            for name, step_class in steps_dict.items():
                if not issubclass(step_class, Step):
                    raise RuntimeError(f'Provided class "{step_class}" is not a subclass of Step')
                register_step(name, step_class)

    def has_template(self, tenant_uuid: str, template_id: str) -> bool:
        return tenant_uuid in self._templates and \
               template_id in self._templates[tenant_uuid]

    def _set_template(self, tenant_uuid: str, template_id: str, template: Template):
        if tenant_uuid not in self._templates:
            self._templates[tenant_uuid] = {}
        self._templates[tenant_uuid][template_id] = template

    def get_template(self, tenant_uuid: str, template_id: str) -> Template:
        return self._templates[tenant_uuid][template_id]

    def _init_new_template(self, tenant_uuid: str, template_id: str,
                           db_template: TemplateComposite):
        workdir = Context.get().app.workdir
        template_dir = workdir / tenant_uuid / template_id.replace(':', '_')
        template = Template(
            tenant_uuid=tenant_uuid,
            template_dir=template_dir,
            db_template=db_template,
        )
        template.prepare_fs()
        self._set_template(tenant_uuid, template_id, template)

    def _refresh_template(self, tenant_uuid: str, template_id: str,
                          db_template: TemplateComposite):
        template = self.get_template(tenant_uuid, template_id)
        template.update_template(db_template)

    def prepare_template(self, tenant_uuid: str, template_id: str) -> Template:
        ctx = Context.get()
        query_args = {
            'template_id': template_id,
            'tenant_uuid': tenant_uuid,
        }
        db_template = ctx.app.db.fetch_template(**query_args)
        if db_template is None:
            raise RuntimeError(f'Template {template_id} not found in database')
        db_files = ctx.app.db.fetch_template_files(**query_args)
        db_assets = ctx.app.db.fetch_template_assets(**query_args)
        template_composite = TemplateComposite(
            template=db_template,
            files={f.uuid: f for f in db_files},
            assets={f.uuid: f for f in db_assets},
        )

        if self.has_template(tenant_uuid, template_id):
            self._refresh_template(tenant_uuid, template_id, template_composite)
        else:
            self._init_new_template(tenant_uuid, template_id, template_composite)

        return self.get_template(tenant_uuid, template_id)

    def _clear_template(self, tenant_uuid: str, template_id: str):
        template = self._templates[tenant_uuid].pop(template_id)
        if template.template_dir.exists():
            shutil.rmtree(template.template_dir)

    def cleanup(self):
        threshold = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=7)
        for tenant_uuid, templates in self._templates.items():
            for template_id, template in templates.items():
                if template.last_used < threshold:
                    self._clear_template(tenant_uuid, template_id)
