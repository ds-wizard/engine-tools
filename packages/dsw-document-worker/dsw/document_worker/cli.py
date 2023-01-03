import click
import pathlib
import logging
import sys

from typing import IO, Optional

from dsw.config.parser import MissingConfigurationError

from .config import DocumentWorkerConfig, DocumentWorkerConfigParser
from .sentry import SentryReporter
from .consts import VERSION


def validate_config(ctx, param, value: Optional[IO]):
    if value is None:
        content = ''
    else:
        content = value.read()
        value.close()
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
                required=False, callback=validate_config,
                type=click.File('r', encoding='utf-8'))
@click.argument('workdir', envvar='DOCWORKER_WORKDIR',
                type=click.Path(dir_okay=True, exists=True))
def main(config: DocumentWorkerConfig, workdir: str):
    logging.basicConfig(
        stream=sys.stdout,
        level=config.log.global_level,
        format=config.log.message_format
    )
    from .worker import DocumentWorker
    worker = DocumentWorker(config, pathlib.Path(workdir))
    try:
        worker.run()
    except Exception as e:
        SentryReporter.capture_exception(e)
        click.echo(f'Ended with error: {e}')
        exit(2)
