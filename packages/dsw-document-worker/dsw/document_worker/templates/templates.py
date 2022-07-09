import base64
import datetime
import pathlib
import shutil

from typing import Optional

from ..connection.database import DBTemplate, DBTemplateFile, DBTemplateAsset
from ..consts import FormatField
from ..context import Context
from ..documents import DocumentFile
from ..templates.formats import Format


class TemplateException(Exception):

    def __init__(self, template_id: str, message: str):
        self.template_id = template_id
        self.message = message

    def __str__(self):
        return f'Error in template "{self.template_id}"\n' \
               f'- {self.message}'


class Asset:

    def __init__(self, asset_uuid: str, filename: str, content_type: str,
                 data: bytes):
        self.asset_uuid = asset_uuid
        self.filename = filename
        self.content_type = content_type
        self.data = data

    @property
    def data_base64(self) -> str:
        return base64.b64encode(self.data).decode('ascii')

    @property
    def src_value(self):
        return f'data:{self.content_type};base64,{self.data_base64}'


class TemplateComposite:

    def __init__(self, db_template, db_files, db_assets):
        self.template = db_template  # type: DBTemplate
        self.files = db_files  # type: dict[str, DBTemplateFile]
        self.assets = db_assets  # type: dict[str, DBTemplateAsset]


class Template:

    def __init__(self, app_uuid: str, template_dir: pathlib.Path,
                 db_template: TemplateComposite):
        self.app_uuid = app_uuid
        self.template_dir = template_dir
        self.last_used = datetime.datetime.utcnow()
        self.db_template = db_template
        self.template_id = self.db_template.template.id
        self.formats = dict()  # type: dict[str, Format]
        self.asset_prefix = f'templates/{self.db_template.template.id}'
        if Context.get().app.cfg.cloud.multi_tenant:
            self.asset_prefix = f'{self.app_uuid}/{self.asset_prefix}'

    def raise_exc(self, message: str):
        raise TemplateException(self.template_id, message)

    def fetch_asset(self, file_name: str) -> Optional[Asset]:
        Context.logger.info(f'Fetching asset "{file_name}"')
        file_path = self.template_dir / file_name
        asset = None
        for a in self.db_template.assets.values():
            if a.file_name == file_name:
                asset = a
                break
        if asset is None or not file_path.exists():
            Context.logger.error(f'Asset "{file_name}" not found')
            return None
        return Asset(
            asset_uuid=asset.uuid,
            filename=file_name,
            content_type=asset.content_type,
            data=file_path.read_bytes()
        )

    def asset_path(self, filename: str) -> str:
        return str(self.template_dir / filename)

    def _store_asset(self, asset: DBTemplateAsset):
        Context.logger.debug(f'Storing asset {asset.uuid} ({asset.file_name})')
        remote_path = f'{self.asset_prefix}/{asset.uuid}'
        local_path = self.template_dir / asset.file_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        result = Context.get().app.s3.download_file(remote_path, local_path)
        if not result:
            Context.logger.error(f'Asset "{local_path.name}" cannot be retrieved')

    def _store_file(self, file: DBTemplateFile):
        Context.logger.debug(f'Storing file {file.uuid} ({file.file_name})')
        local_path = self.template_dir / file.file_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(
            data=file.content,
            encoding='utf-8',
        )

    def _delete_asset(self, asset: DBTemplateAsset):
        Context.logger.debug(f'Deleting asset {asset.uuid} ({asset.file_name})')
        local_path = self.template_dir / asset.file_name
        local_path.unlink(missing_ok=True)

    def _delete_file(self, file: DBTemplateFile):
        Context.logger.debug(f'Deleting file {file.uuid} ({file.file_name})')
        local_path = self.template_dir / file.file_name
        local_path.unlink(missing_ok=True)

    def _update_asset(self, asset: DBTemplateAsset):
        Context.logger.debug(f'Updating asset {asset.uuid} ({asset.file_name})')
        # old_asset = self.db_template.assets[asset.uuid]
        local_path = self.template_dir / asset.file_name
        # TODO: check if changed while having the same UUID (?)
        if not local_path.exists():
            self._store_asset(asset)

    def _update_file(self, file: DBTemplateFile):
        Context.logger.debug(f'Updating file {file.uuid} ({file.file_name})')
        # old_file = self.db_template.files[file.uuid]
        local_path = self.template_dir / file.file_name
        # TODO: check if changed while having the same UUID (?)
        if not local_path.exists():
            self._store_file(file)

    def prepare_all_template_files(self):
        Context.logger.info(f'Storing all files of template {self.template_id} locally')
        for file in self.db_template.files.values():
            self._store_file(file)

    def prepare_all_template_assets(self):
        Context.logger.info(f'Storing all assets of template {self.template_id} locally')
        for asset in self.db_template.assets.values():
            self._store_asset(asset)

    def prepare_fs(self):
        Context.logger.info(f'Preparing directory for template {self.template_id}')
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

    def update_template_files(self, db_files: dict[str, DBTemplateFile]):
        Context.logger.info(f'Updating files of template {self.template_id}')
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

    def update_template_assets(self, db_assets: dict[str, DBTemplateAsset]):
        Context.logger.info(f'Updating assets of template {self.template_id}')
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

    def render(self, format_uuid: str, context: dict) -> DocumentFile:
        self.last_used = datetime.datetime.utcnow()
        return self[format_uuid].execute(context)


class TemplateRegistry:

    _instance = None

    @classmethod
    def get(cls) -> 'TemplateRegistry':
        if cls._instance is None:
            cls._instance = TemplateRegistry()
        return cls._instance

    def __init__(self):
        self._templates = dict()  # type: dict[str, dict[str, Template]]

    def has_template(self, app_uuid: str, template_id: str) -> bool:
        return app_uuid in self._templates.keys() and \
               template_id in self._templates[app_uuid].keys()

    def _set_template(self, app_uuid: str, template_id: str, template: Template):
        if app_uuid not in self._templates.keys():
            self._templates[app_uuid] = dict()
        self._templates[app_uuid][template_id] = template

    def get_template(self, app_uuid: str, template_id: str) -> Template:
        return self._templates[app_uuid][template_id]

    def _init_new_template(self, app_uuid: str, template_id: str,
                           db_template: TemplateComposite):
        workdir = Context.get().app.workdir
        template_dir = workdir / app_uuid / template_id.replace(':', '_')
        template = Template(
            app_uuid=app_uuid,
            template_dir=template_dir,
            db_template=db_template,
        )
        template.prepare_fs()
        self._set_template(app_uuid, template_id, template)

    def _refresh_template(self, app_uuid: str, template_id: str,
                          db_template: TemplateComposite):
        template = self.get_template(app_uuid, template_id)
        template.update_template(db_template)

    def prepare_template(self, app_uuid: str, template_id: str) -> Template:
        ctx = Context.get()
        query_args = dict(
            template_id=template_id,
            app_uuid=app_uuid,
        )
        db_template = ctx.app.db.fetch_template(**query_args)
        if db_template is None:
            raise RuntimeError(f'Template {template_id} not found in database')
        db_files = ctx.app.db.fetch_template_files(**query_args)
        db_assets = ctx.app.db.fetch_template_assets(**query_args)
        template_composite = TemplateComposite(
            db_template=db_template,
            db_files={f.uuid: f for f in db_files},
            db_assets={f.uuid: f for f in db_assets},
        )

        if self.has_template(app_uuid, template_id):
            self._refresh_template(app_uuid, template_id, template_composite)
        else:
            self._init_new_template(app_uuid, template_id, template_composite)

        return self.get_template(app_uuid, template_id)

    def _clear_template(self, app_uuid: str, template_id: str):
        template = self._templates[app_uuid].pop(template_id)
        if template.template_dir.exists():
            shutil.rmtree(template.template_dir)

    def cleanup(self):
        # TODO: configurable
        threshold = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        for app_uuid, templates in self._templates.items():
            for template_id, template in templates.items():
                if template.last_used < threshold:
                    self._clear_template(app_uuid, template_id)
