import pathlib
import sys

from typing import IO, Optional

import click

from dsw.config.parser import MissingConfigurationError
from dsw.config.sentry import SentryReporter

from .config import DocumentWorkerConfig, DocumentWorkerConfigParser
from .consts import VERSION
from .worker import DocumentWorker


def validate_config(ctx: click.Context, param: str, value: Optional[IO]):
    if value is None:
        content = ''
    else:
        content = value.read()
        value.close()
    parser = DocumentWorkerConfigParser()
    if not parser.can_read(content):
        click.echo('Error: Cannot parse config file', err=True)
        sys.exit(1)

    try:
        parser.read_string(content)
        parser.validate()
        return parser.config
    except MissingConfigurationError as exc:
        click.echo('Error: Missing configuration', err=True)
        for missing_item in exc.missing:
            click.echo(f' - {missing_item}')
        sys.exit(1)


@click.command(name='docworker')
@click.version_option(version=VERSION)
@click.argument('config', envvar='DOCWORKER_CONFIG',
                required=False, callback=validate_config,
                type=click.File('r', encoding='utf-8'))
@click.argument('workdir', envvar='DOCWORKER_WORKDIR')
def main(config: DocumentWorkerConfig, workdir: str):
    config.log.apply()
    workdir_path = pathlib.Path(workdir)
    workdir_path.mkdir(parents=True, exist_ok=True)
    if not workdir_path.is_dir():
        click.echo(f'Workdir {workdir_path.as_posix()} is not usable')
        sys.exit(2)
    try:
        worker = DocumentWorker(config, workdir_path)
        worker.run()
    except Exception as exc:
        SentryReporter.capture_exception(exc)
        click.echo(f'Ended with error: {exc}')
        sys.exit(2)
