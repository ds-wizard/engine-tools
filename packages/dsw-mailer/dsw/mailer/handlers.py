import os
import pathlib

from .cli import load_config_str
from .consts import VAR_APP_CONFIG_PATH, VAR_WORKDIR_PATH
from .mailer import Mailer


def lambda_handler(event, context):
    config_path = pathlib.Path(os.getenv(VAR_APP_CONFIG_PATH, '/var/task/application.yml'))
    workdir_path = pathlib.Path(os.getenv(VAR_WORKDIR_PATH, '/var/task/templates'))

    config = load_config_str(config_path.read_text())
    mailer = Mailer(config, workdir_path)
    mailer.run_once()
