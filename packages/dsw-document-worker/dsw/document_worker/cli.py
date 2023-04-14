import click
import pathlib

from typing import IO, Optional

from dsw.config.parser import MissingConfigurationError
from dsw.config.sentry import SentryReporter

from .config import DocumentWorkerConfig, DocumentWorkerConfigParser
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
@click.argument('workdir', envvar='DOCWORKER_WORKDIR')
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
