import os
import pathlib
import sys

from .cli import load_config_str
from .consts import (VAR_APP_CONFIG_PATH, VAR_WORKDIR_PATH,
                     VAR_SEEDER_RECIPE, DEFAULT_ENCODING)
from .seeder import DataSeeder


# pylint: disable-next=unused-argument
def lambda_handler(event, context):
    config_path = pathlib.Path(os.getenv(VAR_APP_CONFIG_PATH, '/var/task/application.yml'))
    workdir_path = pathlib.Path(os.getenv(VAR_WORKDIR_PATH, '/var/task/data'))
    recipe_name = os.getenv(VAR_SEEDER_RECIPE, None)

    if recipe_name is None:
        print(f'Error: Missing recipe name (environment variable {VAR_SEEDER_RECIPE})')
        sys.exit(1)

    config = load_config_str(config_path.read_text(encoding=DEFAULT_ENCODING))
    seeder = DataSeeder(config, workdir_path)
    seeder.run_once(recipe_name)
