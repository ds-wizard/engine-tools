from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


COMPONENT_NAME = 'Mailer'
CMD_CHANNEL = 'Mailer'
CMD_COMPONENT = 'Mailer'
CMD_FUNCTION = 'sendMail'
DEFAULT_ENCODING = 'utf-8'
NULL_UUID = '00000000-0000-0000-0000-000000000000'
PROG_NAME = 'dsw-mailer'
PACKAGE_NAME = 'dsw-mailer'
#: the Registry server's mails: English, no locales, no custom templates
REGISTRY_MODE = 'registry'
TRIGGER = 'PersistentCommand'

try:
    __version__ = version(PACKAGE_NAME)
except PackageNotFoundError:
    __version__ = '0.0.0'
VERSION = __version__

VAR_APP_CONFIG_PATH = 'APPLICATION_CONFIG_PATH'
VAR_WORKDIR_PATH = 'WORKDIR_PATH'
