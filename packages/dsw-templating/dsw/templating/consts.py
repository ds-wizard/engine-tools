from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


DEFAULT_ENCODING = 'utf-8'
EXIT_SUCCESS = 0
PACKAGE_NAME = 'dsw-templating'
PLUGINS_ENTRYPOINT = 'dsw_templating_plugins'

JINJA_EXTENSIONS = ('jinja2.ext.do', 'jinja2.ext.loopcontrols')
JINJA_FILE_EXTENSIONS = ('.j2', '.jinja', '.jinja2', '.jnj')

# Rendering and POT extraction must agree on this: the msgid of a {% trans %}
# block depends on it, and the POT file is per document template while a step
# option would be per format.
JINJA_I18N_TRIMMED = True

DEFAULT_LANGUAGE = 'en'
DEFAULT_LOCALE_DOMAIN = 'default'

TEMPLATE_JSON_FILE_NAME = 'template.json'
PROJECT_FILES_DIR = 'project-files'

try:
    __version__ = version(PACKAGE_NAME)
except PackageNotFoundError:
    __version__ = '0.0.0'
VERSION = __version__


class FormatField:
    UUID = 'uuid'
    NAME = 'name'
    STEPS = 'steps'


class StepField:
    NAME = 'name'
    OPTIONS = 'options'
