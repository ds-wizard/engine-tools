import os
import pathlib

from .cli import validate_config
from .mailer import Mailer


def lambda_handler(event, context):
    config_path = os.getenv('APPLICATION_CONFIG_PATH', '/var/task/application.yml')
    workdir_path = os.getenv('WORKDIR_PATH', '/var/task/templates')

    with open(config_path, 'r') as config_file:
        config = validate_config(None, None, config_file)
    config.log.apply()
    mailer = Mailer(config, pathlib.Path(workdir_path))
    mailer.run_once()
