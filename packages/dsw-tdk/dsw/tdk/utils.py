import jinja2  # type: ignore
import pathlib
import uuid

from typing import List, Set

from .consts import DEFAULT_ENCODING, DEFAULT_README
from .model import Template, TemplateFile, Format, Step, PackageFilter
from .validation import TemplateValidator, FormatValidator, StepValidator


TEMPLATES_DIR = pathlib.Path(__file__).parent / 'templates'

j2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
    extensions=['jinja2.ext.do'],
    autoescape=True,
)


class UUIDGen:

    _uuids = set()  # type: Set[uuid.UUID]

    @classmethod
    def used(cls) -> Set[uuid.UUID]:
        return cls._uuids

    @classmethod
    def generate(cls) -> uuid.UUID:
        result = uuid.uuid4()
        while result in cls._uuids:
            result = uuid.uuid4()
        cls._uuids.add(result)
        return result


class FormatSpec:

    def __init__(self):
        self.format = Format()
        self.step = Step(
            name='jinja',
            options={
                'template': 'template.html.j2',
                'content-type': 'text/html',
                'extension': 'html',
            }
        )
        self.format.uuid = str(UUIDGen.generate())
        self.format.steps.append(self.step)

    @property
    def name(self):
        return self.format.name

    @name.setter
    def name(self, value: str):
        self.format.name = value
        FormatValidator.validate_field(self.format, 'name')

    @property
    def content_type(self):
        return self.step.options['content-type']

    @content_type.setter
    def content_type(self, value: str):
        self.step.options['content-type'] = value
        StepValidator.validate(self.step, 'format')

    @property
    def file_extension(self):
        return self.step.options['extension']

    @file_extension.setter
    def file_extension(self, value: str):
        self.step.options['extension'] = value
        StepValidator.validate(self.step, 'format')

    @property
    def filename(self):
        return self.step.options['template']

    @filename.setter
    def filename(self, value: str):
        self.step.options['template'] = str(pathlib.PurePosixPath(pathlib.Path(value)))
        StepValidator.validate(self.step, 'format')


class TemplateBuilder:

    def __init__(self):
        self.template = Template()
        self._formats = []  # type: List[FormatSpec]

    @property
    def formats(self) -> List[FormatSpec]:
        return self._formats

    def _validate_field(self, field_name: str):
        TemplateValidator.validate_field(self.template, field_name)

    def add_format(self, format_spec: FormatSpec):
        self._formats.append(format_spec)
        self.template.formats.append(format_spec.format)

    @property
    def name(self):
        return self.template.name

    @name.setter
    def name(self, value: str):
        self.template.name = value
        self._validate_field('name')

    @property
    def template_id(self):
        return self.template.template_id

    @template_id.setter
    def template_id(self, value: str):
        self.template.template_id = value
        self._validate_field('template_id')

    @property
    def organization_id(self):
        return self.template.organization_id

    @organization_id.setter
    def organization_id(self, value: str):
        self.template.organization_id = value
        self._validate_field('organization_id')

    @property
    def version(self):
        return self.template.version

    @version.setter
    def version(self, value: str):
        self.template.version = value
        self._validate_field('version')

    @property
    def description(self):
        return self.template.description

    @description.setter
    def description(self, value: str):
        self.template.description = value
        self._validate_field('description')

    @property
    def license(self):
        return self.template.license

    @license.setter
    def license(self, value: str):
        self.template.license = value
        self._validate_field('license')

    def build(self) -> Template:
        readme = j2_env.get_template('README.md.j2').render(template=self.template)
        self.template.readme = readme
        self.template.tdk_config.readme_file = DEFAULT_README
        TemplateValidator.validate(self.template)
        for format_spec in self._formats:
            content = j2_env.get_template('starter.j2').render(template=self.template)
            self.template.files[format_spec.filename] = TemplateFile(
                filename=format_spec.filename,
                content_type='text/plain',
                content=content.encode(encoding=DEFAULT_ENCODING)
            )
            self.template.tdk_config.files.append(str(format_spec.filename))
        self.template.allowed_packages.append(PackageFilter())
        return self.template
