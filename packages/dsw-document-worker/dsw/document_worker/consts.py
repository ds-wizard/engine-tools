from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


CMD_CHANNEL = 'doc_worker'
CMD_COMPONENT = 'doc_worker'
CMD_FUNCTION_GENERATE_POT_FILE = 'generatePotFile'
COMPONENT_NAME = 'Document Worker'
DEFAULT_ENCODING = 'utf-8'
EXIT_SUCCESS = 0
NULL_UUID = '00000000-0000-0000-0000-000000000000'
PACKAGE_NAME = 'dsw-document-worker'
PLUGINS_ENTRYPOINT = 'dsw_document_worker_plugins'
PROG_NAME = 'docworker'

JINJA_EXTENSIONS = ('jinja2.ext.do', 'jinja2.ext.loopcontrols')
JINJA_FILE_EXTENSIONS = ('.j2', '.jinja', '.jinja2', '.jnj')

# Rendering and POT extraction must agree on this: the msgid of a {% trans %}
# block depends on it, and the POT file is per document template while a step
# option would be per format.
JINJA_I18N_TRIMMED = True

DEFAULT_LANGUAGE = 'en'
DEFAULT_LOCALE_DOMAIN = 'default'
LOCALE_PO_FILE_NAME = 'translation.po'
LOCALE_MO_FILE_NAME = 'translation.mo'
LOCALE_STAMP_FILE_NAME = 'updated_at'
LOCALES_CACHE_DIR = '.locales'

try:
    __version__ = version(PACKAGE_NAME)
except PackageNotFoundError:
    __version__ = '0.0.0'
VERSION = __version__

VAR_APP_CONFIG_PATH = 'APPLICATION_CONFIG_PATH'
VAR_WORKDIR_PATH = 'WORKDIR_PATH'


class DocumentState:
    QUEUED = 'QueuedDocumentState'
    PROCESSING = 'InProgressDocumentState'
    FAILED = 'ErrorDocumentState'
    FINISHED = 'DoneDocumentState'


class TemplateAssetField:
    UUID = 'uuid'
    FILENAME = 'fileName'
    CONTENT_TYPE = 'contentType'


class FormatField:
    UUID = 'uuid'
    NAME = 'name'
    STEPS = 'steps'


class StepField:
    NAME = 'name'
    OPTIONS = 'options'


class DocumentNamingStrategy:
    UUID = 'uuid'
    SANITIZE = 'sanitize'
    SLUGIFY = 'slugify'

    _DEFAULT = SANITIZE
    _NAMES = {
        'uuid': UUID,
        'sanitize': SANITIZE,
        'slugify': SLUGIFY,
    }

    @classmethod
    def get(cls, name: str) -> str:
        return cls._NAMES.get(name.lower(), cls._DEFAULT)
