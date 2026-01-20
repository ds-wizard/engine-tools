import pathlib
import sys
import typing

import click

from dsw.config.parser import MissingConfigurationError
from dsw.config.sentry import SentryReporter

from . import consts
from .config import DocumentWorkerConfig, DocumentWorkerConfigParser
from .worker import DocumentWorker


def load_config_str(config_str: str) -> DocumentWorkerConfig:
    parser = DocumentWorkerConfigParser()
    if not parser.can_read(config_str):
        click.echo('Error: Cannot parse config file', err=True)
        sys.exit(1)

    try:
        parser.read_string(config_str)
        parser.validate()
    except MissingConfigurationError as e:
        click.echo('Error: Missing configuration', err=True)
        for missing_item in e.missing:
            click.echo(f' - {missing_item}', err=True)
        sys.exit(1)

    config = parser.config
    config.log.apply()
    return config


# pylint: disable-next=unused-argument
def validate_config(ctx, param, value: typing.IO | None):
    content = ''
    if value is not None:
        content = value.read()
        value.close()
    return load_config_str(content)


@click.group(name='dsw-document-worker')
@click.version_option(version=consts.VERSION)
def main():
    pass


@main.command()
@click.argument('config', envvar=consts.VAR_APP_CONFIG_PATH,
                required=False, callback=validate_config,
                type=click.File('r', encoding=consts.DEFAULT_ENCODING))
@click.argument('workdir', envvar=consts.VAR_WORKDIR_PATH)
def run(config: DocumentWorkerConfig, workdir: str):
    config.log.apply()
    workdir_path = pathlib.Path(workdir)
    workdir_path.mkdir(parents=True, exist_ok=True)
    if not workdir_path.is_dir():
        click.echo(f'Workdir {workdir_path.as_posix()} is not usable')
        sys.exit(2)
    try:
        worker = DocumentWorker(config, workdir_path)
        worker.run()
    except Exception as e:
        SentryReporter.capture_exception(e)
        click.echo(f'Error: {e}', err=True)
        sys.exit(2)


@main.command()
def list_plugins():
    # pylint: disable-next=import-outside-toplevel
    from .plugins.manager import create_manager

    pm = create_manager()
    for plugin in pm.list_name_plugin():
        click.echo(f'{plugin[0]}: {plugin[1].__name__}')
