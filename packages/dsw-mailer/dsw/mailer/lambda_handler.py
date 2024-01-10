import pathlib

from dsw.mailer.cli import validate_config
from dsw.mailer.mailer import Mailer


def lambda_handler(event, context):
    with open("/var/task/application.yml", "r") as config_file:
        config = validate_config(None, None, config_file)
    config.log.apply()
    mailer = Mailer(config, pathlib.Path("/var/task/templates"))
    mailer.run_once()
