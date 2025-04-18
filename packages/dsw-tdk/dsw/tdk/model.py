import enum
import json
import logging
import mimetypes
import pathlib

from collections import OrderedDict
from typing import Any

import pathspec

from .consts import VERSION, DEFAULT_ENCODING, METAMODEL_VERSION, PathspecFactory

mimetypes.init()


class TemplateFileType(enum.Enum):
    ASSET = 'asset'
    FILE = 'file'


class PackageFilter:

    def __init__(self, *, organization_id: str | None = None, km_id: str | None = None,
                 min_version: str | None = None, max_version: str | None = None):
        self.organization_id = organization_id
        self.km_id = km_id
        self.min_version = min_version
        self.max_version = max_version

    @classmethod
    def load(cls, data):
        return PackageFilter(
            organization_id=data.get('orgId', None),
            km_id=data.get('kmId', None),
            min_version=data.get('minVersion', None),
            max_version=data.get('maxVersion', None),
        )

    def serialize(self):
        return {
            'orgId': self.organization_id,
            'kmId': self.km_id,
            'minVersion': self.min_version,
            'maxVersion': self.max_version,
        }


class Step:

    def __init__(self, *, name: str | None = None,
                 options: dict[str, str] | None = None):
        self.name = name
        self.options = options or {}

    @classmethod
    def load(cls, data):
        return Step(
            name=data.get('name', None),
            options=data.get('options', None),
        )

    def serialize(self):
        return {
            'name': self.name,
            'options': self.options,
        }


class Format:

    DEFAULT_ICON = 'fas fa-file'

    def __init__(self, *, uuid: str | None = None, name: str | None = None,
                 icon: str | None = None):
        self.uuid = uuid
        self.name = name
        self.icon: str = icon or self.DEFAULT_ICON
        self.steps: list[Step] = []

    @classmethod
    def load(cls, data):
        format_spec = Format(
            uuid=data.get('uuid', None),
            name=data.get('name', None),
            icon=data.get('icon', None),
        )
        for s_data in data.get('steps', []):
            format_spec.steps.append(Step.load(s_data))
        return format_spec

    def serialize(self):
        return {
            'uuid': self.uuid,
            'name': self.name,
            'icon': self.icon,
            'steps': [step.serialize() for step in self.steps]
        }


class TDKConfig:

    DEFAULT_README = 'README.md'
    DEFAULT_FILES = ['*', '!.git/', '!.env']

    def __init__(self, *, version: str | None = None, readme_file: str | None = None,
                 files: list[str] | None = None):
        self.version: str = version or VERSION
        readme_file_str: str = readme_file or self.DEFAULT_README
        self.readme_file: pathlib.Path = pathlib.Path(readme_file_str)
        self.files: list[str] = files or []

    @classmethod
    def load(cls, data):
        return TDKConfig(
            version=data.get('version', VERSION),
            readme_file=data.get('readmeFile', cls.DEFAULT_README),
            files=data.get('files', cls.DEFAULT_FILES),
        )

    def use_default_files(self):
        self.files = self.DEFAULT_FILES

    def serialize(self):
        return {
            'version': self.version,
            'readmeFile': str(self.readme_file),
            'files': self.files,
        }


class TemplateFile:

    DEFAULT_CONTENT_TYPE = 'application/octet-stream'
    TEMPLATE_EXTENSIONS = ('.j2', '.jinja', '.jinja2', '.jnj')

    def __init__(self, *, filename: pathlib.Path,
                 remote_id: str | None = None, remote_type: TemplateFileType | None = None,
                 content_type: str | None = None, content: bytes = b''):
        self.remote_id = remote_id
        self.filename = filename
        self.content = content
        self.content_type: str = content_type or self.guess_type()
        self.remote_type: TemplateFileType = remote_type or self.guess_tfile_type()

    def guess_tfile_type(self):
        return TemplateFileType.FILE if self.is_text else TemplateFileType.ASSET

    def guess_type(self) -> str:
        filename = self.filename.name
        for ext in self.TEMPLATE_EXTENSIONS:
            if filename.endswith(ext):
                return 'text/jinja2'
        guessed_type = mimetypes.guess_type(filename, strict=False)
        if guessed_type is None or guessed_type[0] is None:
            return self.DEFAULT_CONTENT_TYPE
        return guessed_type[0]

    @property
    def is_text(self):
        if getattr(self, 'remote_type', None) == TemplateFileType.FILE:
            return True
        return self.content_type.startswith('text')

    @property
    def has_remote_id(self):
        return self.remote_id is not None


class Template:

    # pylint: disable-next=too-many-arguments
    def __init__(self, *, template_id=None, organization_id=None, version=None, name=None,
                 description=None, readme=None, template_license=None,
                 metamodel_version=None, tdk_config=None, loaded_json=None):
        self.template_id = template_id  # type: str
        self.organization_id = organization_id  # type: str
        self.version = version  # type: str
        self.name = name  # type: str
        self.description = description  # type: str
        self.readme = readme  # type: str
        self.license = template_license  # type: str
        self.metamodel_version: int = metamodel_version or METAMODEL_VERSION
        self.allowed_packages: list[PackageFilter] = []
        self.formats: list[Format] = []
        self.files: dict[str, TemplateFile] = {}
        self.extras: list[TemplateFile] = []
        self.tdk_config: TDKConfig = tdk_config or TDKConfig()
        self.loaded_json: OrderedDict = loaded_json or OrderedDict()

    @property
    def id(self) -> str:
        return f'{self.organization_id}:{self.template_id}:{self.version}'

    def id_with_org(self, organization_id: str) -> str:
        return f'{organization_id}:{self.template_id}:{self.version}'

    @classmethod
    def _common_load(cls, data):
        if 'id' in data.keys():
            composite_id = data['id']  # type: str
            if composite_id.count(':') != 2:
                raise RuntimeError(f'Invalid template ID: {composite_id}')
            org_id, tmp_id, version = composite_id.split(':')
        else:
            try:
                org_id = data['organizationId']
                tmp_id = data['templateId']
                version = data['version']
            except KeyError as e:
                raise RuntimeError('Cannot retrieve template ID') from e
        template = Template(
            template_id=tmp_id,
            organization_id=org_id,
            version=version,
            name=data.get('name', 'Unknown template'),
            description=data.get('description', ''),
            template_license=data.get('license', 'no-license'),
            metamodel_version=data.get('metamodelVersion', METAMODEL_VERSION),
            readme=data.get('readme', ''),
        )
        for ap_data in data.get('allowedPackages', []):
            template.allowed_packages.append(PackageFilter.load(ap_data))
        for f_data in data.get('formats', []):
            template.formats.append(Format.load(f_data))
        return template

    @classmethod
    def load_local(cls, data: OrderedDict):
        template = cls._common_load(data)
        if '_tdk' in data.keys():
            template.tdk_config = TDKConfig.load(data['_tdk'])
        template.loaded_json = data
        return template

    @classmethod
    def load_remote(cls, data: dict):
        return cls._common_load(data)

    def serialize_local(self) -> OrderedDict:
        self.loaded_json['templateId'] = self.template_id
        self.loaded_json['organizationId'] = self.organization_id
        self.loaded_json['version'] = self.version
        self.loaded_json['name'] = self.name
        self.loaded_json['description'] = self.description
        self.loaded_json['license'] = self.license
        self.loaded_json['metamodelVersion'] = self.metamodel_version
        # self.loaded_json['readme'] = self.readme
        self.loaded_json['allowedPackages'] = [ap.serialize() for ap in self.allowed_packages]
        self.loaded_json['formats'] = [f.serialize() for f in self.formats]
        self.loaded_json['_tdk'] = self.tdk_config.serialize()
        return self.loaded_json

    def serialize_remote(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'templateId': self.template_id,
            'organizationId': self.organization_id,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'license': self.license,
            'metamodelVersion': self.metamodel_version,
            'readme': self.readme,
            'allowedPackages': [ap.serialize() for ap in self.allowed_packages],
            'formats': [f.serialize() for f in self.formats],
            'phase': 'DraftDocumentTemplatePhase',
        }

    def serialize_for_update(self) -> dict[str, Any]:
        return {
            'templateId': self.template_id,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'license': self.license,
            'metamodelVersion': self.metamodel_version,
            'readme': self.readme,
            'allowedPackages': [ap.serialize() for ap in self.allowed_packages],
            'formats': [f.serialize() for f in self.formats],
            'phase': 'DraftDocumentTemplatePhase',
        }

    def serialize_for_create(self, based_on: str | None = None) -> dict[str, Any]:
        return {
            'basedOn': based_on,
            'name': self.name,
            'templateId': self.template_id,
            'version': self.version,
        }

    def serialize_local_new(self) -> dict[str, Any]:
        return {
            'templateId': self.template_id,
            'organizationId': self.organization_id,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'license': self.license,
            'metamodelVersion': self.metamodel_version,
            'allowedPackages': [ap.serialize() for ap in self.allowed_packages],
            'formats': [f.serialize() for f in self.formats],
            '_tdk': self.tdk_config.serialize(),
        }


def _to_ordered_dict(tuples: list[tuple[str, Any]]) -> OrderedDict:
    return OrderedDict(tuples)


class TemplateProject:

    TEMPLATE_FILE = 'template.json'
    DEFAULT_PATTERNS = ['!**/.*', '!**/.*/', '!**/~*', '!**/~*/',
                        '!template.json', '!template.zip']

    json_decoder = json.JSONDecoder(object_pairs_hook=_to_ordered_dict)

    def __init__(self, template_dir: pathlib.Path, logger: logging.Logger):
        self.template_dir = pathlib.Path(template_dir)
        self.descriptor_path = self.template_dir / self.TEMPLATE_FILE
        self.template: Template | None = None
        self.used_readme: pathlib.Path | None = None
        self._logger = logger

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def safe_template(self) -> Template:
        if self.template is None:
            raise RuntimeError('Template is not loaded')
        return self.template

    def load_descriptor(self):
        if not self.descriptor_path.is_file():
            raise RuntimeError(f'Template file does not exist: {self.descriptor_path.as_posix()}')
        try:
            content = self.descriptor_path.read_text(encoding=DEFAULT_ENCODING)
            self.template = Template.load_local(self.json_decoder.decode(content))
        except Exception as e:
            raise RuntimeError(f'Unable to load template using {self.descriptor_path}.') from e

    def load_readme(self):
        readme = self.safe_template.tdk_config.readme_file
        if readme is not None:
            try:
                self.used_readme = self.template_dir / readme
                self.safe_template.readme = self.used_readme.read_text(encoding=DEFAULT_ENCODING)
            except Exception as e:
                raise RuntimeWarning(f'README file "{readme}" cannot be loaded: {e}') from e

    def load_file(self, filepath: pathlib.Path) -> TemplateFile:
        try:
            if filepath.is_absolute():
                filepath = filepath.relative_to(self.template_dir)
            tfile = TemplateFile(filename=filepath)
            with open(self.template_dir / filepath, mode='rb') as f:
                tfile.content = f.read()
            self.safe_template.files[filepath.as_posix()] = tfile
            return tfile
        except Exception as e:
            raise RuntimeWarning(f'Failed to load template file {filepath}: {e}') from e

    def load_files(self):
        self.safe_template.files.clear()
        for f in self.list_files():
            self.load_file(f)

    @property
    def files_pathspec(self) -> pathspec.PathSpec:
        patterns = self.safe_template.tdk_config.files + self.DEFAULT_PATTERNS
        return pathspec.PathSpec.from_lines(PathspecFactory, patterns)

    def list_files(self) -> list[pathlib.Path]:
        files = (pathlib.Path(p)
                 for p in self.files_pathspec.match_tree_files(str(self.template_dir)))
        if self.used_readme is not None:
            return list(p for p in files if p != self.used_readme.relative_to(self.template_dir))
        return list(files)

    def _relative_paths_eq(self, filepath1: pathlib.Path | None,
                           filepath2: pathlib.Path | None) -> bool:
        if filepath1 is None or filepath2 is None:
            return False
        return filepath1.relative_to(self.template_dir) == filepath2.relative_to(self.template_dir)

    def is_template_file(self, filepath: pathlib.Path, include_descriptor: bool = False,
                         include_readme: bool = False):
        if include_readme and self._relative_paths_eq(filepath, self.used_readme):
            return True
        if include_descriptor and self._relative_paths_eq(filepath, self.descriptor_path):
            return True
        return self.files_pathspec.match_file(filepath.relative_to(self.template_dir))

    def load(self):
        self.load_descriptor()
        self.load_readme()
        self.load_files()

    def remove_template_file(self, filepath: pathlib.Path):
        if filepath.is_absolute():
            filepath = filepath.relative_to(self.template_dir)
        filename = filepath.as_posix()
        if filename in self.safe_template.files:
            del self.safe_template.files[filename]

    def update_template_file(self, tfile: TemplateFile):
        filename = tfile.filename.as_posix()
        self.safe_template.files[filename] = tfile

    def get_template_file(self, filepath: pathlib.Path) -> TemplateFile | None:
        if filepath.is_absolute():
            filepath = filepath.relative_to(self.template_dir)
        return self.safe_template.files.get(filepath.as_posix(), None)

    def _write_file(self, filepath: pathlib.Path, contents: bytes, force: bool):
        if filepath.exists() and not force:
            self.logger.warning(f'Skipping file {filepath} (not forced)')
            return
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_bytes(contents)
            self.logger.debug(f'Stored file {filepath}')
        except Exception as e:
            self.logger.error(f'Unable to write file {filepath}: {e}')

    def store_descriptor(self, force: bool):
        self._write_file(
            filepath=self.descriptor_path,
            contents=json.dumps(
                obj=self.safe_template.serialize_local(),
                indent=4
            ).encode(encoding=DEFAULT_ENCODING),
            force=force,
        )

    def store_readme(self, force: bool):
        if self.safe_template.tdk_config.readme_file is None:
            self.logger.warning('No README file specified for the template')
            return
        self._write_file(
            filepath=self.template_dir / self.safe_template.tdk_config.readme_file,
            contents=self.safe_template.readme.encode(encoding=DEFAULT_ENCODING),
            force=force,
        )

    def store_files(self, force: bool):
        for tfile in self.safe_template.files.values():
            self._write_file(
                filepath=self.template_dir / tfile.filename,
                contents=tfile.content,
                force=force,
            )

    def store(self, force: bool):
        self.logger.debug(f'Ensuring directory {self.template_dir.as_posix()}')
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f'Storing {self.TEMPLATE_FILE} descriptor')
        self.store_descriptor(force=force)
        self.logger.debug('Storing README file')
        self.store_readme(force=force)
        self.logger.debug('Storing template files')
        self.store_files(force=force)
        self.logger.debug('Storing finished')
