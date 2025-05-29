import pathlib
import re

import pathspec

APP = 'dsw-tdk'
VERSION = '4.19.0'
METAMODEL_VERSION = 16

REGEX_SEMVER = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+$')
REGEX_WIZARD_ID = re.compile(r'^[a-zA-Z0-9-_.]+$')
REGEX_ORGANIZATION_ID = REGEX_WIZARD_ID
REGEX_TEMPLATE_ID = REGEX_WIZARD_ID
REGEX_KM_ID = REGEX_WIZARD_ID
REGEX_MIME_TYPE = re.compile(r'^(?![-])(?!.*[-]$)[-\w.]+/[-\w.]+$')

DEFAULT_LIST_FORMAT = '{template.id:<50} {template.name:<30}'
DEFAULT_ENCODING = 'utf-8'
DEFAULT_README = pathlib.Path('README.md')

TEMPLATE_FILE = 'template.json'
PathspecFactory = pathspec.patterns.GitWildMatchPattern
