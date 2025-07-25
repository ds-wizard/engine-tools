# pylint: disable=too-few-public-methods
CMD_CHANNEL = 'doc_worker'
CMD_COMPONENT = 'doc_worker'
COMPONENT_NAME = 'Document Worker'
CURRENT_METAMODEL = 16
DEFAULT_ENCODING = 'utf-8'
EXIT_SUCCESS = 0
NULL_UUID = '00000000-0000-0000-0000-000000000000'
PACKAGE_NAME = 'dsw-document-worker'
PLUGINS_ENTRYPOINT = 'dsw_document_worker_plugins'
PROG_NAME = 'docworker'
VERSION = '4.20.1'

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
