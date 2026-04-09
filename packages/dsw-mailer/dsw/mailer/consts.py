from importlib.metadata import PackageNotFoundError, version


COMPONENT_NAME = 'Mailer'
CMD_CHANNEL = 'mailer'
CMD_COMPONENT = 'mailer'
CMD_FUNCTION = 'sendMail'
DEFAULT_ENCODING = 'utf-8'
NULL_UUID = '00000000-0000-0000-0000-000000000000'
PROG_NAME = 'dsw-mailer'
PACKAGE_NAME = 'dsw-mailer'

try:
    __version__ = version(PACKAGE_NAME)
except PackageNotFoundError:
    __version__ = '0.0.0'
VERSION = __version__

VAR_APP_CONFIG_PATH = 'APPLICATION_CONFIG_PATH'
VAR_WORKDIR_PATH = 'WORKDIR_PATH'
