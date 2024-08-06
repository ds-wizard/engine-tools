import click  # type: ignore
import json
import pathlib

from typing import IO

from dsw.config.parser import MissingConfigurationError

from .config import MailerConfig, MailerConfigParser
from .consts import (VERSION, VAR_APP_CONFIG_PATH, VAR_WORKDIR_PATH,
                     DEFAULT_ENCODING)
from .model import MessageRequest


def load_config_str(config_str: str) -> MailerConfig:
    parser = MailerConfigParser()
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


def validate_config(ctx, param, value: IO | None):
    content = ''
    if value is not None:
        content = value.read()
        value.close()
    return load_config_str(content)


def extract_message_request(ctx, param, value: IO):
    data = json.load(value)
    try:
        return MessageRequest.load_from_file(data)
    except Exception as e:
        click.echo('Error: Cannot parse message request', err=True)
        click.echo(f'{type(e).__name__}: {str(e)}')
        exit(1)


@click.group(name='dsw-mailer', help='Mailer for sending emails from DSW')
@click.pass_context
@click.version_option(version=VERSION)
@click.option('-c', '--config', envvar=VAR_APP_CONFIG_PATH,
              required=False, callback=validate_config,
              type=click.File('r', encoding=DEFAULT_ENCODING))
@click.option('-w', '--workdir', envvar=VAR_WORKDIR_PATH,
              type=click.Path(dir_okay=True, exists=True))
def cli(ctx, config: MailerConfig, workdir: str):
    path_workdir = pathlib.Path(workdir)
    from .mailer import Mailer
    config.log.apply()
    ctx.obj['mailer'] = Mailer(config, path_workdir)


@cli.command(name='send', help='Send message(s) from given file directly.')
@click.pass_context
@click.argument('msg-request', type=click.File('r', encoding=DEFAULT_ENCODING),
                callback=extract_message_request)
@click.option('-c', '--config', envvar=VAR_APP_CONFIG_PATH,
              required=False, callback=validate_config,
              type=click.File('r', encoding=DEFAULT_ENCODING))
def send(ctx, msg_request: MessageRequest, config: MailerConfig):
    from .mailer import Mailer
    mailer = ctx.obj['mailer']  # type: Mailer
    mailer.send(rq=msg_request, cfg=config.mail)


@cli.command(name='run', help='Run mailer worker processing message jobs.')
@click.pass_context
def run(ctx):
    from .mailer import Mailer
    mailer = ctx.obj['mailer']  # type: Mailer
    mailer.run()


def main():
    cli(obj={})
