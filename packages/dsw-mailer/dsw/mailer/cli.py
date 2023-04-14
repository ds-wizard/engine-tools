import json
import pathlib
import sys

from typing import IO, Optional

import click  # type: ignore

from dsw.config.parser import MissingConfigurationError

from .config import MailerConfig, MailerConfigParser
from .consts import VERSION
from .mailer import Mailer
from .model import MessageRequest


def validate_config(ctx, param, value: Optional[IO]):
    if value is None:
        content = ''
    else:
        content = value.read()
        value.close()
    parser = MailerConfigParser()
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
            click.echo(f' - {missing_item}', err=True)
        sys.exit(1)


def extract_message_request(ctx, param, value: IO):
    data = json.load(value)
    try:
        return MessageRequest.load_from_file(data)
    except Exception as exc:
        click.echo('Error: Cannot parse message request', err=True)
        click.echo(f'{type(exc).__name__}: {str(exc)}')
        sys.exit(1)


@click.group(name='dsw-mailer')
@click.pass_context
@click.version_option(version=VERSION)
@click.option('-c', '--config', envvar='DSW_CONFIG',
              required=False, callback=validate_config,
              type=click.File('r', encoding='utf-8'))
@click.option('-w', '--workdir', envvar='MAILER_WORKDIR',
              type=click.Path(dir_okay=True, exists=True))
@click.option('-m', '--mode', envvar='MAILER_MODE',
              type=click.Choice(['wizard', 'registry']),
              default='wizard')
def cli(ctx, config: MailerConfig, workdir: str, mode: str):
    """Mailer for sending emails from DSW"""
    path_workdir = pathlib.Path(workdir)
    config.log.apply()
    ctx.obj['mailer'] = Mailer(config, path_workdir, mode)


@cli.command()
@click.pass_context
@click.argument('msg-request', type=click.File('r', encoding='utf-8'),
                callback=extract_message_request)
def send(ctx, msg_request: MessageRequest):
    """Send message(s) from given file directly"""
    mailer = ctx.obj['mailer']  # type: Mailer
    mailer.send(rq=msg_request, cfg=None)


@cli.command()
@click.pass_context
def run(ctx):
    """Run mailer worker processing message jobs"""
    mailer = ctx.obj['mailer']  # type: Mailer
    mailer.run()


def main(ctx_obj=None):
    ctx_obj = ctx_obj or {}
    cli(obj=ctx_obj)
