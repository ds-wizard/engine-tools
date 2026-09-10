from __future__ import annotations

import pathlib
import re
from importlib.metadata import PackageNotFoundError, version

import pathspec


APP = 'dsw-tdk'
PACKAGE_NAME = 'dsw-tdk'

METAMODEL_VERSION_MAJOR = 18
METAMODEL_VERSION_MINOR = 3
METAMODEL_VERSION = f'{METAMODEL_VERSION_MAJOR}.{METAMODEL_VERSION_MINOR}'

try:
    __version__ = version(PACKAGE_NAME)
except PackageNotFoundError:
    __version__ = '0.0.0'
VERSION = __version__

REGEX_SEMVER = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+$')
REGEX_WIZARD_ID = re.compile(r'^[a-zA-Z0-9-_.]+$')
REGEX_ORGANIZATION_ID = REGEX_WIZARD_ID
REGEX_TEMPLATE_ID = REGEX_WIZARD_ID
REGEX_KM_ID = REGEX_WIZARD_ID
REGEX_MIME_TYPE = re.compile(r'^(?![-])(?!.*[-]$)[-\w.]+/[-\w.]+$')

DEFAULT_LIST_FORMAT = '{template.id:<50} {template.name:<30} [{template.uuid}]'
DEFAULT_ENCODING = 'utf-8'
DEFAULT_LANGUAGE = 'en'
DEFAULT_LOCALE_DOMAIN = 'default'
DEFAULT_README = pathlib.Path('README.md')

JINJA_EXTENSIONS = ('jinja2.ext.do', 'jinja2.ext.loopcontrols')
JINJA_I18N_TRIMMED = True
POT_FILE_DEFAULT = 'template.pot'

TEMPLATE_FILE = 'template.json'
PathspecFactory = pathspec.patterns.GitWildMatchPattern
