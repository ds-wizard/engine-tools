from importlib.metadata import PackageNotFoundError, version


COMPONENT_NAME = 'Data Seeder'
CMD_COMPONENT = 'data_seeder'
CMD_CHANNEL = 'data_seeder'
DEFAULT_ENCODING = 'utf-8'
DEFAULT_MIMETYPE = 'application/octet-stream'
DEFAULT_PLACEHOLDER = '<<|TENANT-ID|>>'
NULL_UUID = '00000000-0000-0000-0000-000000000000'
PROG_NAME = 'dsw-data-seeder'
PACKAGE_NAME = 'dsw-data-seeder'

try:
    __version__ = version(PACKAGE_NAME)
except PackageNotFoundError:
    __version__ = '0.0.0'
VERSION = __version__

VAR_APP_CONFIG_PATH = 'APPLICATION_CONFIG_PATH'
VAR_WORKDIR_PATH = 'WORKDIR_PATH'
VAR_SEEDER_RECIPE = 'SEEDER_RECIPE'
