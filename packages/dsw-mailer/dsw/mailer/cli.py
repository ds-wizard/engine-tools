import click  # type: ignore
import json
import pathlib
import sys

from typing import IO

from dsw.config.parser import MissingConfigurationError

from .config import MailerConfig, MailerConfigParser
from .consts import VERSION
from .mailer import Mailer
from .model import MessageRequest


def validate_config(ctx, param, value: IO):
    content = value.read()
    parser = MailerConfigParser()
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
            click.echo(f' - {missing_item}', err=True)
        exit(1)


def extract_message_request(ctx, param, value: IO):
    data = json.load(value)
    try:
        return MessageRequest.load_from_file(data)
    except Exception as e:
        click.echo('Error: Cannot parse message request', err=True)
        click.echo(f'{type(e).__name__}: {str(e)}')
        exit(1)


@click.group(name='dsw-mailer')
@click.pass_context
@click.version_option(version=VERSION)
@click.option('-c', '--config', envvar='DSW_CONFIG',
              type=click.File('r', encoding='utf-8'),
              callback=validate_config)
@click.option('-w', '--workdir', envvar='MAILER_WORKDIR',
              type=click.Path(dir_okay=True, exists=True))
@click.option('-m', '--mode', envvar='MAILER_MODE',
              type=click.Choice(['wizard', 'registry']),
              default='wizard')
def cli(ctx, config: MailerConfig, workdir: str, mode: str):
    """Mailer for sending emails from DSW"""
    if not config.mail.enabled:
        click.echo('Mail is set to disabled, why even running mailer?')
        sys.exit(1)
    path_workdir = pathlib.Path(workdir)
    ctx.obj['mailer'] = Mailer(config, path_workdir, mode)


@cli.command()
@click.pass_context
@click.argument('msg-request', type=click.File('r', encoding='utf-8'),
                callback=extract_message_request)
def send(ctx, msg_request: MessageRequest):
    """Send message(s) from given file directly"""
    mailer = ctx.obj['mailer']  # type: Mailer
    mailer.send(rq=msg_request)


@cli.command()
@click.pass_context
def run(ctx):
    """Run mailer worker processing message jobs"""
    mailer = ctx.obj['mailer']  # type: Mailer
    mailer.run()


def main():
    cli(obj={})
