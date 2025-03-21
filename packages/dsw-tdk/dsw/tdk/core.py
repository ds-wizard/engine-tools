import asyncio
import datetime
import io
import json
import logging
import pathlib
import re
import shutil
import tempfile
import zipfile

import watchfiles

from .api_client import DSWAPIClient, DSWCommunicationError
from .consts import DEFAULT_ENCODING, REGEX_SEMVER
from .model import TemplateProject, Template, TemplateFile, TemplateFileType
from .utils import UUIDGen, create_dot_env
from .validation import ValidationError, TemplateValidator


ChangeItem = tuple[watchfiles.Change, pathlib.Path]


def _change(item: ChangeItem, root: pathlib.Path) -> str:
    return f'{item[0].name.upper()}[{item[1].relative_to(root).as_posix()}]'


class TDKProcessingError(RuntimeError):

    def __init__(self, message: str, hint: str):
        self.message = message
        self.hint = hint


METAMODEL_VERSION_SUPPORT = {
    1: (2, 5, 0),
    2: (2, 6, 0),
    3: (2, 12, 0),
    4: (3, 2, 0),
    5: (3, 5, 0),
    6: (3, 6, 0),
    7: (3, 7, 0),
    8: (3, 8, 0),
    9: (3, 10, 0),
    10: (3, 12, 0),
    11: (3, 20, 0),
    12: (4, 1, 0),
    13: (4, 3, 0),
    14: (4, 10, 0),
    15: (4, 12, 0),
    16: (4, 13, 0),
}


# pylint: disable=too-many-public-methods
class TDKCore:

    def _check_metamodel_version(self):
        mm_ver = self.safe_template.metamodel_version
        api_version = self.remote_version.split('~', maxsplit=1)[0]
        if '-' in api_version:
            api_version = api_version.split('-', maxsplit=1)[0]
        if 'v' == api_version[0]:
            api_version = api_version[1:]
        if not re.match(REGEX_SEMVER, api_version):
            self.logger.warning('Using non-stable release of API: %s', self.remote_version)
            return
        parts = api_version.split('.')
        ver = (int(parts[0]), int(parts[1]), int(parts[2]))
        vtag = f'v{ver[0]}.{ver[1]}.{ver[2]}'
        hint = 'Fix your metamodelVersion in template.json and/or visit docs'
        if mm_ver not in METAMODEL_VERSION_SUPPORT:
            raise TDKProcessingError(f'Unknown metamodel version: {mm_ver}', hint)
        min_version = METAMODEL_VERSION_SUPPORT[mm_ver]
        if min_version > ver:
            raise TDKProcessingError(f'Unsupported metamodel version for API {vtag}', hint)
        if mm_ver + 1 in METAMODEL_VERSION_SUPPORT:
            max_version = METAMODEL_VERSION_SUPPORT[mm_ver + 1]
            if ver >= max_version:
                raise TDKProcessingError(f'Unsupported metamodel version for API {vtag}', hint)

    def __init__(self, template: Template | None = None, project: TemplateProject | None = None,
                 client: DSWAPIClient | None = None, logger: logging.Logger | None = None):
        self.template = template
        self.project = project
        self.client = client
        self.remote_version = 'unknown~??????'
        self.logger = logger or logging.getLogger()
        self.loop = asyncio.get_event_loop()
        self.changes_processor = ChangesProcessor(self)
        self.remote_id = 'unknown'

    async def close(self):
        await self.safe_client.close()

    @property
    def safe_template(self) -> Template:
        if self.template is None:
            raise RuntimeError('No template is loaded')
        return self.template

    @property
    def safe_project(self) -> TemplateProject:
        if self.project is None:
            raise RuntimeError('No template is loaded')
        return self.project

    @property
    def safe_client(self) -> DSWAPIClient:
        if self.client is None:
            raise RuntimeError('No DSW API client specified')
        return self.client

    async def init_client(self, api_url: str, api_key: str):
        self.logger.info('Connecting to %s', api_url)
        self.client = DSWAPIClient(api_url=api_url, api_key=api_key)
        self.remote_version = await self.client.get_api_version()
        user = await self.client.get_current_user()
        self.logger.info('Successfully authenticated as %s %s (%s)',
                         user['firstName'], user['lastName'], user['email'])
        self.logger.debug('Connected to API version %s', self.remote_version)

    def prepare_local(self, template_dir):
        self.logger.debug('Preparing local template project')
        self.project = TemplateProject(template_dir=template_dir, logger=self.logger)

    def load_local(self, template_dir):
        self.prepare_local(template_dir=template_dir)
        self.logger.info('Loading local template project')
        self.safe_project.load()

    async def load_remote(self, template_id: str):
        self.logger.info('Retrieving template draft %s', template_id)
        self.template = await self.safe_client.get_template_draft(remote_id=template_id)
        self.logger.debug('Retrieving template draft files')
        files = await self.safe_client.get_template_draft_files(remote_id=template_id)
        self.logger.info('Retrieved %s file(s)', len(files))
        for tfile in files:
            self.safe_template.files[tfile.filename.as_posix()] = tfile
        self.logger.debug('Retrieving template draft assets')
        assets = await self.safe_client.get_template_draft_assets(remote_id=template_id)
        self.logger.info('Retrieved %s asset(s)', len(assets))
        for tfile in assets:
            self.safe_template.files[tfile.filename.as_posix()] = tfile

    async def download_bundle(self, template_id: str) -> bytes:
        self.logger.info('Retrieving template %s bundle', template_id)
        return await self.safe_client.get_template_bundle(remote_id=template_id)

    async def list_remote_templates(self) -> list[Template]:
        self.logger.info('Listing remote document templates')
        return await self.safe_client.get_templates()

    async def list_remote_drafts(self) -> list[Template]:
        self.logger.info('Listing remote document template drafts')
        return await self.safe_client.get_drafts()

    def verify(self) -> list[ValidationError]:
        template = self.template or self.safe_project.template
        if template is None:
            raise RuntimeError('No template is loaded')
        return TemplateValidator.collect_errors(template)

    def store_local(self, force: bool):
        if self.project is None:
            raise RuntimeError('No template project is initialized')
        self.project.template = self.safe_template
        if len(self.project.template.tdk_config.files) == 0:
            self.project.template.tdk_config.use_default_files()
            self.logger.warning('Using default _tdk.files in template.json, you may want '
                                'to change it to include relevant files')
        self.logger.debug('Initiating storing local template project (force=%s)', force)
        self.project.store(force=force)

    async def store_remote(self, force: bool):
        self.template = self.safe_project.template
        self._check_metamodel_version()
        org_id = await self.safe_client.get_organization_id()
        if org_id != self.safe_template.organization_id:
            self.logger.warning('There is different organization ID set in the DSW instance'
                                ' (local: %s, remote: %s)',
                                self.safe_template.organization_id, org_id)
        self.remote_id = self.safe_template.id_with_org(org_id)
        template_exists = await self.safe_client.check_draft_exists(remote_id=self.remote_id)
        if template_exists and force:
            self.logger.warning('Deleting existing remote document template draft (forced)')
            result = await self.safe_client.delete_template_draft(remote_id=self.remote_id)
            if not result:
                self.logger.error('Could not delete document template draft')
            template_exists = not result

        if template_exists:
            self.logger.info('Updating existing remote document template draft')
            await self.safe_client.update_template_draft(
                template=self.safe_template,
                remote_id=self.remote_id,
            )
            self.logger.debug('Retrieving remote assets')
            remote_assets = await self.safe_client.get_template_draft_assets(
                remote_id=self.remote_id,
            )
            self.logger.debug('Retrieving remote files')
            remote_files = await self.safe_client.get_template_draft_files(
                remote_id=self.remote_id,
            )
            await self.cleanup_remote_files(
                remote_assets=remote_assets,
                remote_files=remote_files,
            )
        else:
            self.logger.info('Creating remote document template draft')
            await self.safe_client.create_new_template_draft(
                template=self.safe_template,
                remote_id=self.remote_id,
            )
        await self.store_remote_files()

    async def _update_template_file(self, remote_tfile: TemplateFile, local_tfile: TemplateFile,
                                    project_update: bool = False):
        try:
            self.logger.debug('Updating existing remote %s %s (%s) started',
                              remote_tfile.remote_type.value, remote_tfile.filename.as_posix(),
                              remote_tfile.remote_id)
            local_tfile.remote_id = remote_tfile.remote_id
            if remote_tfile.remote_type == TemplateFileType.ASSET:
                result = await self.safe_client.put_template_draft_asset_content(
                    remote_id=self.remote_id,
                    tfile=local_tfile,
                )
            else:
                result = await self.safe_client.put_template_draft_file_content(
                    remote_id=self.remote_id,
                    tfile=local_tfile,
                )
            self.logger.debug('Updating existing remote %s %s (%s) finished: %s',
                              remote_tfile.remote_type.value, remote_tfile.filename.as_posix(),
                              remote_tfile.remote_id, 'ok' if result else 'failed')
            if project_update and result:
                self.safe_project.update_template_file(result)
        except Exception as e1:
            try:
                self.logger.debug('Trying to delete/create due to: %s', str(e1))
                await self._delete_template_file(tfile=remote_tfile)
                await self._create_template_file(tfile=local_tfile, project_update=True)
            except Exception as e2:
                self.logger.error('Failed to update existing remote %s %s: %s',
                                  remote_tfile.remote_type.value,
                                  remote_tfile.filename.as_posix(), e2)

    async def _delete_template_file(self, tfile: TemplateFile, project_update: bool = False):
        try:
            self.logger.debug('Deleting existing remote %s %s (%s) started',
                              tfile.remote_type.value, tfile.filename.as_posix(),
                              tfile.remote_id)
            if tfile.remote_type == TemplateFileType.ASSET:
                result = await self.safe_client.delete_template_draft_asset(
                    remote_id=self.remote_id,
                    asset_id=tfile.remote_id,
                )
            else:
                result = await self.safe_client.delete_template_draft_file(
                    remote_id=self.remote_id,
                    file_id=tfile.remote_id,
                )
            self.logger.debug('Deleting existing remote %s %s (%s) finished: %s',
                              tfile.remote_type.value, tfile.filename.as_posix(),
                              tfile.remote_id, 'ok' if result else 'failed')
            if project_update and result:
                self.safe_project.remove_template_file(tfile.filename)
        except Exception as e:
            self.logger.error('Failed to delete existing remote %s %s: %s',
                              tfile.remote_type.value, tfile.filename.as_posix(), e)

    async def cleanup_remote_files(self, remote_assets: list[TemplateFile],
                                   remote_files: list[TemplateFile]):
        for tfile in self.safe_project.safe_template.files.values():
            self.logger.debug('Cleaning up remote %s', tfile.filename.as_posix())
            for remote_asset in remote_assets:
                if remote_asset.filename == tfile.filename:
                    await self._delete_template_file(tfile=remote_asset, project_update=False)
            for remote_file in remote_files:
                if remote_file.filename == tfile.filename:
                    await self._delete_template_file(tfile=remote_file, project_update=False)

    async def _create_template_file(self, tfile: TemplateFile, project_update: bool = False):
        try:
            self.logger.debug('Storing remote %s %s started',
                              tfile.remote_type.value, tfile.filename.as_posix())
            if tfile.remote_type == TemplateFileType.ASSET:
                result = await self.safe_client.post_template_draft_asset(
                    remote_id=self.remote_id,
                    tfile=tfile,
                )
            else:
                result = await self.safe_client.post_template_draft_file(
                    remote_id=self.remote_id,
                    tfile=tfile,
                )
            self.logger.debug('Storing remote %s %s finished: %s',
                              tfile.remote_type.value, tfile.filename.as_posix(), result.remote_id)
            if project_update and result is not None:
                self.safe_project.update_template_file(result)
        except Exception as e:
            self.logger.error('Failed to store remote %s %s: %s',
                              tfile.remote_type.value, tfile.filename.as_posix(), e)

    async def store_remote_files(self):
        if len(self.safe_project.safe_template.files) == 0:
            self.logger.warning('No files to store, maybe you forgot to '
                                'update _tdk.files patterns in template.json?')
        for tfile in self.safe_project.safe_template.files.values():
            tfile.remote_id = None
            tfile.remote_type = TemplateFileType.FILE if tfile.is_text else TemplateFileType.ASSET
            await self._create_template_file(tfile=tfile, project_update=True)

    def create_package(self, output: pathlib.Path, force: bool):
        if output.exists() and not force:
            raise RuntimeError(f'File {output} already exists (not forced)')
        self.logger.debug('Opening ZIP file for write: %s', output.as_posix())
        with zipfile.ZipFile(output, mode='w', compression=zipfile.ZIP_DEFLATED) as pkg:
            descriptor = self.safe_project.safe_template.serialize_remote()
            files = []
            assets = []
            for tfile in self.safe_project.safe_template.files.values():
                if tfile.is_text:
                    self.logger.info('Adding template file %s', tfile.filename.as_posix())
                    files.append({
                        'uuid': str(UUIDGen.generate()),
                        'content': tfile.content.decode(encoding=DEFAULT_ENCODING),
                        'fileName': str(tfile.filename.as_posix()),
                    })
                else:
                    self.logger.info('Adding template asset %s', tfile.filename.as_posix())
                    assets.append({
                        'uuid': str(UUIDGen.generate()),
                        'contentType': tfile.content_type,
                        'fileName': str(tfile.filename.as_posix()),
                    })
                    self.logger.debug('Packaging template asset %s', tfile.filename.as_posix())
                    pkg.writestr(f'template/assets/{tfile.filename.as_posix()}', tfile.content)
            descriptor['files'] = files
            descriptor['assets'] = assets
            if len(files) == 0 and len(assets) == 0:
                self.logger.warning('No files or assets found in the template, maybe you forgot '
                                    'to update _tdk.files patterns in template.json?')
            timestamp = datetime.datetime.now(tz=datetime.UTC).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            descriptor['createdAt'] = timestamp
            descriptor['updatedAt'] = timestamp
            self.logger.debug('Packaging template.json file')
            pkg.writestr('template/template.json', data=json.dumps(descriptor, indent=4))
        self.logger.debug('ZIP packaging done')

    # pylint: disable=too-many-locals
    def extract_package(self, zip_data: bytes, template_dir: pathlib.Path | None, force: bool):
        with tempfile.TemporaryDirectory() as tmp_dir:
            io_zip = io.BytesIO(zip_data)
            with zipfile.ZipFile(io_zip) as pkg:
                pkg.extractall(tmp_dir)
            del io_zip
            tmp_root = pathlib.Path(tmp_dir) / 'template'
            template_file = tmp_root / 'template.json'
            assets_dir = tmp_root / 'assets'
            self.logger.debug('Extracting template data')
            if not template_file.exists():
                raise RuntimeError('Malformed package: missing template.json file')
            data = json.loads(template_file.read_text(encoding=DEFAULT_ENCODING))
            template = Template.load_local(data)
            template.tdk_config.use_default_files()
            self.logger.warning('Using default _tdk.files in template.json, you may want '
                                'to change it to include relevant files')
            self.logger.debug('Preparing template dir')
            if template_dir is None:
                template_dir = pathlib.Path.cwd() / template.id.replace(':', '_')
            if template_dir.exists():
                if not force:
                    raise RuntimeError(f'Template directory already exists: '
                                       f'{template_dir.as_posix()} (use force?)')
                shutil.rmtree(template_dir, ignore_errors=True)
            template_dir.mkdir(parents=True)
            self.logger.debug('Extracting template.json from package')
            local_template_json = template_dir / 'template.json'
            local_template_json.write_text(
                data=json.dumps(template.serialize_local_new(), indent=2),
                encoding=DEFAULT_ENCODING,
            )
            self.logger.debug('Extracting README.md from package')
            local_readme = template_dir / 'README.md'
            local_readme.write_text(
                data=data['readme'].replace('\r\n', '\n'),
                encoding=DEFAULT_ENCODING,
            )
            self.logger.debug('Extracting assets from package')
            for asset_file in assets_dir.rglob('*'):
                if asset_file.is_file():
                    target_asset = template_dir / asset_file.relative_to(assets_dir)
                    target_dir = target_asset.parent
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_asset.write_bytes(asset_file.read_bytes())
            self.logger.debug('Extracting files from package')
            for file_item in data.get('files', []):
                filename = file_item['fileName']
                content = file_item['content'].replace('\r\n', '\n')
                target_file = template_dir / filename
                target_dir = target_file.parent
                target_dir.mkdir(parents=True, exist_ok=True)
                target_file.write_text(data=content, encoding=DEFAULT_ENCODING)
        self.logger.debug('Extracting package done')

    def create_dot_env(self, output: pathlib.Path, force: bool, api_url: str, api_key: str):
        if output.exists():
            if force:
                self.logger.warning('Overwriting %s (forced)', output.as_posix())
            else:
                raise RuntimeError(f'File {output} already exists (not forced)')
        output.write_text(
            data=create_dot_env(api_url=api_url, api_key=api_key),
            encoding=DEFAULT_ENCODING,
        )

    async def watch_project(self, callback, stop_event: asyncio.Event):
        async for changes in watchfiles.awatch(
                self.safe_project.template_dir,
                stop_event=stop_event,
        ):
            await callback((
                change for change in ((change[0], pathlib.Path(change[1])) for change in changes)
                if self.safe_project.is_template_file(
                    change[1], include_descriptor=True, include_readme=True
                )
            ))

    async def update_descriptor(self):
        try:
            template_exists = await self.safe_client.check_draft_exists(
                remote_id=self.remote_id,
            )
            if template_exists:
                self.logger.info('Updating existing remote document template draft %s',
                                 self.safe_project.safe_template.id)
                await self.safe_client.update_template_draft(
                    template=self.safe_project.safe_template,
                    remote_id=self.remote_id,
                )
            else:
                self.logger.info('Document template draft %s does not exist on remote - full sync',
                                 self.safe_project.safe_template.id)
                await self.store_remote(force=False)
        except DSWCommunicationError as e:
            self.logger.error('Failed to update document template draft %s: %s',
                              self.safe_project.safe_template.id, e.message)
        except Exception as e:
            self.logger.error('Failed to update document template draft %s: %s',
                              self.safe_project.safe_template.id, e)

    async def delete_file(self, filepath: pathlib.Path):
        if not filepath.is_file():
            self.logger.debug('%s is not a regular file - skipping',
                              filepath.as_posix())
            return
        try:
            tfile = self.safe_project.get_template_file(filepath=filepath)
            if tfile is None:
                self.logger.info('File %s not tracked currently - skipping',
                                 filepath.as_posix())
                return
            await self._delete_template_file(tfile=tfile, project_update=True)
        except Exception as e:
            self.logger.error('Failed to delete file %s: %s',
                              filepath.as_posix(), e)

    async def update_file(self, filepath: pathlib.Path):
        if not filepath.is_file():
            self.logger.debug('%s is not a regular file - skipping',
                              filepath.as_posix())
            return
        try:
            remote_tfile = self.safe_project.get_template_file(filepath=filepath)
            local_tfile = self.safe_project.load_file(filepath=filepath)
            if remote_tfile is not None:
                await self._update_template_file(remote_tfile, local_tfile, project_update=True)
            else:
                await self._create_template_file(tfile=local_tfile, project_update=True)
        except Exception as e:
            self.logger.error('Failed to update file %s: %s', filepath.as_posix(), e)

    async def process_changes(self, changes: list[ChangeItem], force: bool):
        self.changes_processor.clear()
        try:
            await self.changes_processor.process_changes(changes, force)
        except Exception as e:
            self.logger.error('Failed to process changes: %s', e)


class ChangesProcessor:

    def __init__(self, tdk: TDKCore):
        self.tdk: TDKCore = tdk
        self.descriptor_change: ChangeItem | None = None
        self.readme_change: ChangeItem | None = None
        self.file_changes: list[ChangeItem] = []

    def clear(self):
        self.descriptor_change = None
        self.readme_change = None
        self.file_changes = []

    def _split_changes(self, changes: list[ChangeItem]):
        for change in changes:
            if change[1] == self.tdk.safe_project.descriptor_path:
                self.descriptor_change = change
            elif change[1] == self.tdk.safe_project.used_readme:
                self.readme_change = change
            elif self.tdk.safe_project.is_template_file(change[1]):
                self.file_changes.append(change)

    async def _process_file_changes(self):
        deleted = set()
        updated = set()
        for file_change in self.file_changes:
            self.tdk.logger.debug('Processing: %s',
                                  _change(file_change, self.tdk.safe_project.template_dir))
            change_type = file_change[0]
            filepath = file_change[1]
            if change_type == watchfiles.Change.deleted and filepath not in deleted:
                self.tdk.logger.debug('Scheduling delete operation')
                deleted.add(filepath)
                await self.tdk.delete_file(filepath)
            elif filepath not in updated:
                self.tdk.logger.debug('Scheduling update operation')
                updated.add(filepath)
                await self.tdk.update_file(filepath)

    async def _reload_descriptor(self, force: bool) -> bool:
        if self.descriptor_change is None:
            return False
        if self.descriptor_change[0] == watchfiles.Change.deleted:
            raise RuntimeError(f'Deleted {self.tdk.safe_project.descriptor_path} ... the end')
        self.tdk.logger.debug('Reloading %s file', TemplateProject.TEMPLATE_FILE)
        previous_id = self.tdk.safe_project.safe_template.id
        self.tdk.safe_project.load_descriptor()
        self.tdk.safe_project.load_readme()
        new_id = self.tdk.safe_project.safe_template.id
        if new_id != previous_id:
            self.tdk.logger.warning('Template ID changed from %s to %s',
                                    previous_id, new_id)
            self.tdk.safe_project.load()
            await self.tdk.store_remote(force=force)
            self.tdk.logger.info('Template fully reloaded... waiting for new changes')
            return True
        return False

    async def _reload_readme(self) -> bool:
        if self.readme_change is None:
            return False
        if self.readme_change[0] == watchfiles.Change.deleted:
            raise RuntimeError(f'Deleted used README file {self.tdk.safe_project.used_readme}')
        self.tdk.logger.debug('Reloading README file')
        self.tdk.safe_project.load_readme()
        return True

    async def _update_descriptor(self):
        if self.readme_change is not None or self.descriptor_change is not None:
            self.tdk.logger.debug('Updating template descriptor (metadata)')
            await self.tdk.update_descriptor()
            self.tdk.safe_project.template = self.tdk.safe_template

    async def process_changes(self, changes: list[ChangeItem], force: bool):
        self._split_changes(changes)
        full_reload = await self._reload_descriptor(force)
        if not full_reload:
            await self._reload_readme()
            await self._update_descriptor()
            await self._process_file_changes()
        self.tdk.logger.info('All changes processed... waiting for new changes')
