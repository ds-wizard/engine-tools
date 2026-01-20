import logging
import os
import pathlib
import sys

from . import consts
from .cli import load_config_str
from .seeder import DataSeeder, SentryReporter


LOG = logging.getLogger(__name__)


# pylint: disable-next=unused-argument
def lambda_handler(event, context):
    config_path = pathlib.Path(os.getenv(consts.VAR_APP_CONFIG_PATH, '/var/task/application.yml'))
    workdir_path = pathlib.Path(os.getenv(consts.VAR_WORKDIR_PATH, '/var/task/data'))
    recipe_name = os.getenv(consts.VAR_SEEDER_RECIPE, None)

    if recipe_name is None:
        LOG.error('Error: Missing recipe name (environment variable %s)', consts.VAR_SEEDER_RECIPE)
        sys.exit(1)

    config = load_config_str(config_path.read_text(encoding=consts.DEFAULT_ENCODING))
    try:
        seeder = DataSeeder(
            cfg=config,
            workdir=workdir_path,
            default_recipe_name=recipe_name or 'default',
        )
        seeder.run_once()
    except Exception as e:
        SentryReporter.capture_exception(e)
        raise e
