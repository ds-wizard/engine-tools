from __future__ import annotations

import os
import pathlib

from dsw.config import read_config

from . import consts
from .cli import load_config_str
from .mailer import Mailer, SentryReporter


def lambda_handler(event, context):
    config_path = pathlib.Path(os.getenv(consts.VAR_APP_CONFIG_PATH, '/var/task/application.yml'))
    workdir_path = pathlib.Path(os.getenv(consts.VAR_WORKDIR_PATH, '/var/task/templates'))

    config = load_config_str(read_config(config_path, encoding=consts.DEFAULT_ENCODING))
    try:
        mailer = Mailer(config, workdir_path)
        mailer.run_once()
    except Exception as e:
        SentryReporter.capture_exception(e)
        raise e
