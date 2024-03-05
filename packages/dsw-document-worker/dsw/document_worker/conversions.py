import logging
import os
import pathlib
import rdflib
import shlex
import subprocess

from .config import DocumentWorkerConfig
from .consts import EXIT_SUCCESS, DEFAULT_ENCODING
from .documents import FileFormat, FileFormats


LOG = logging.getLogger(__name__)


def run_conversion(*, args: list, workdir: str, input_data: bytes, name: str,
                   source_format: FileFormat, target_format: FileFormat, timeout=None) -> bytes:
    command = ' '.join(args)
    LOG.info(f'Calling "{command}" to convert from {source_format} to {target_format}')
    p = subprocess.Popen(args,
                         cwd=workdir,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate(input=input_data, timeout=timeout)
    exit_code = p.returncode
    if exit_code != EXIT_SUCCESS:
        raise FormatConversionException(
            name, source_format, target_format,
            f'Failed to execute (exit code: {exit_code}): {stderr.decode(DEFAULT_ENCODING)}'
        )
    return stdout


class FormatConversionException(Exception):

    def __init__(self, convertor, source_format, target_format, message):
        self.convertor = convertor
        self.source_format = source_format
        self.target_format = target_format
        self.message = message

    def __str__(self):
        return f'{self.convertor} failed to convert {self.source_format}' \
               f' to {self.target_format} - {self.message}'


class Pandoc:
    FILTERS_PATH = pathlib.Path(os.getenv('PANDOC_FILTERS', '/pandoc/filters'))
    TEMPLATES_PATH = pathlib.Path(os.getenv('PANDOC_TEMPLATES', '/pandoc/templates'))

    def __init__(self, config: DocumentWorkerConfig, filter_names: list[str], template_name: str | None):
        self.config = config
        self.filter_names = filter_names
        self.template_name = template_name
        self._check_filters()
        self._check_template()

    def _check_filters(self):
        for name in self.filter_names:
            if not (self.FILTERS_PATH / name).is_file():
                raise RuntimeError(f'Pandoc filter "{name}" not found')

    def _check_template(self):
        if self.template_name and not (self.TEMPLATES_PATH / self.template_name).is_file():
            raise RuntimeError(f'Pandoc template "{self.template_name}" not found')

    def _extra_args(self):
        args = []
        if self.template_name:
            args.extend(['--template', str(self.TEMPLATES_PATH / self.template_name)])
        for filter_name in self.filter_names:
            if filter_name.endswith('.lua'):
                args.extend(['--lua-filter', str(self.FILTERS_PATH / filter_name)])
            else:
                args.extend(['--filter', str(self.FILTERS_PATH / filter_name)])
        return shlex.split(' '.join(args))

    def __call__(self, source_format: FileFormat, target_format: FileFormat,
                 data: bytes, metadata: dict, workdir: str) -> bytes:
        args = ['-f', source_format.name, '-t', target_format.name, '-o', '-']
        config_args = shlex.split(self.config.pandoc.args)
        template_args = self.extract_template_args(metadata)
        extra_args = self._extra_args()
        command = self.config.pandoc.command + template_args + config_args + extra_args + args
        return run_conversion(
            args=command,
            workdir=workdir,
            input_data=data,
            name=type(self).__name__,
            source_format=source_format,
            target_format=target_format,
            timeout=self.config.pandoc.timeout,
        )

    @staticmethod
    def extract_template_args(metadata: dict):
        return shlex.split(metadata.get('args', ''))


class RdfLibConvert:

    FORMATS = {
        FileFormats.RDF_XML: 'xml',
        FileFormats.N3: 'n3',
        FileFormats.NTRIPLES: 'ntriples',
        FileFormats.TURTLE: 'turtle',
        FileFormats.TRIG: 'trig',
        FileFormats.JSONLD: 'json-ld',
    }

    def __init__(self, config: DocumentWorkerConfig):
        self.config = config

    def __call__(self, source_format: FileFormat, target_format: FileFormat,
                 data: bytes, metadata: dict) -> bytes:
        g = rdflib.Graph().parse(
            data=data.decode(DEFAULT_ENCODING),
            format=self.FORMATS.get(source_format) or 'turtle',
        )
        result = g.serialize(
            format=self.FORMATS.get(target_format) or 'turtle',
            encoding=DEFAULT_ENCODING,
        )
        return result
