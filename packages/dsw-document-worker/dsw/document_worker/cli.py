import click
import pathlib

from typing import IO

from dsw.config.parser import MissingConfigurationError

from .config import DocumentWorkerConfig, DocumentWorkerConfigParser
from .connection.sentry import SentryReporter
from .consts import VERSION
from .worker import DocumentWorker


def validate_config(ctx, param, value: IO):
    content = value.read()
    parser = DocumentWorkerConfigParser()
    if not parser.can_read(content):
        click.echo('Error: Cannot parse config file', err=True)
        exit(1)

    try:
        parser.read_string(content)
        parser.validate()
        return parser.config
    except MissingConfigurationError as e:
        click.echo('Error: Missing configuration', err=True)
        for missing_item in e.missing:
            click.echo(f' - {missing_item}')
        exit(1)


@click.command(name='docworker')
@click.version_option(version=VERSION)
@click.argument('config', envvar='DOCWORKER_CONFIG',
                type=click.File('r', encoding='utf-8'),
                callback=validate_config)
@click.argument('workdir', envvar='DOCWORKER_WORKDIR',
                type=click.Path(dir_okay=True, exists=True))
def main(config: DocumentWorkerConfig, workdir: str):
    worker = DocumentWorker(config, pathlib.Path(workdir))
    try:
        worker.run()
    except Exception as e:
        SentryReporter.capture_exception(e)
        click.echo(f'Ended with error: {e}')
        exit(2)
