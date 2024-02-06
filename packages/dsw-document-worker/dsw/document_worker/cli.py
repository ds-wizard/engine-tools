import click
import pathlib

from typing import IO, Optional

from dsw.config.parser import MissingConfigurationError
from dsw.config.sentry import SentryReporter

from .config import DocumentWorkerConfig, DocumentWorkerConfigParser
from .consts import (VERSION, VAR_APP_CONFIG_PATH, VAR_WORKDIR_PATH,
                     DEFAULT_ENCODING)


def load_config_str(config_str: str) -> DocumentWorkerConfig:
    parser = DocumentWorkerConfigParser()
    if not parser.can_read(config_str):
        click.echo('Error: Cannot parse config file', err=True)
        exit(1)

    try:
        parser.read_string(config_str)
        parser.validate()
    except MissingConfigurationError as e:
        click.echo('Error: Missing configuration', err=True)
        for missing_item in e.missing:
            click.echo(f' - {missing_item}', err=True)
        exit(1)

    config = parser.config
    config.log.apply()
    return config


def validate_config(ctx, param, value: Optional[IO]):
    content = ''
    if value is not None:
        content = value.read()
        value.close()
    return load_config_str(content)


@click.command(name='docworker')
@click.version_option(version=VERSION)
@click.argument('config', envvar=VAR_APP_CONFIG_PATH,
                required=False, callback=validate_config,
                type=click.File('r', encoding=DEFAULT_ENCODING))
@click.argument('workdir', envvar=VAR_WORKDIR_PATH,)
def main(config: DocumentWorkerConfig, workdir: str):
    from .worker import DocumentWorker
    config.log.apply()
    workdir_path = pathlib.Path(workdir)
    workdir_path.mkdir(parents=True, exist_ok=True)
    if not workdir_path.is_dir():
        click.echo(f'Workdir {workdir_path.as_posix()} is not usable')
        exit(2)
    try:
        worker = DocumentWorker(config, workdir_path)
        worker.run()
    except Exception as e:
        SentryReporter.capture_exception(e)
        click.echo(f'Ended with error: {e}')
        exit(2)
