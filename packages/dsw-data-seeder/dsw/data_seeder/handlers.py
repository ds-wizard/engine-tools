import os
import pathlib

from .cli import validate_config
from .seeder import DataSeeder


def lambda_handler(event, context):
    config_path = os.getenv('APPLICATION_CONFIG_PATH', '/var/task/application.yml')
    workdir_path = os.getenv('WORKDIR_PATH', '/var/task/data')
    recipe_name = os.getenv('SEEDER_RECIPE')

    with open(config_path, 'r') as config_file:
        config = validate_config(None, None, config_file)
    config.log.apply()
    seeder = DataSeeder(config, pathlib.Path(workdir_path))
    seeder.run_once(recipe_name)
