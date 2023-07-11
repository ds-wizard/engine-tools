import click  # type: ignore
import json
import pathlib

from typing import IO, Optional

from dsw.config.parser import MissingConfigurationError

from .config import MailerConfig, MailerConfigParser
from .consts import VERSION
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


@click.group(name='dsw-mailer', help='Mailer for sending emails from DSW')
@click.pass_context
@click.version_option(version=VERSION)
@click.option('-c', '--config', envvar='APPLICATION_CONFIG_PATH',
              required=False, callback=validate_config,
              type=click.File('r', encoding='utf-8'))
@click.option('-w', '--workdir', envvar='WORKDIR_PATH',
              type=click.Path(dir_okay=True, exists=True))
@click.option('-m', '--mode', envvar='MAILER_MODE',
              type=click.Choice(['wizard', 'registry']),
              default='wizard')
def cli(ctx, config: MailerConfig, workdir: str, mode: str):
    path_workdir = pathlib.Path(workdir)
    from .mailer import Mailer
    config.log.apply()
    ctx.obj['mailer'] = Mailer(config, path_workdir, mode)


@cli.command(name='send', help='Send message(s) from given file directly.')
@click.pass_context
@click.argument('msg-request', type=click.File('r', encoding='utf-8'),
                callback=extract_message_request)
def send(ctx, msg_request: MessageRequest):
    from .mailer import Mailer
    mailer = ctx.obj['mailer']  # type: Mailer
    mailer.send(rq=msg_request, cfg=None)


@cli.command(name='run', help='Run mailer worker processing message jobs.')
@click.pass_context
def run(ctx):
    from .mailer import Mailer
    mailer = ctx.obj['mailer']  # type: Mailer
    mailer.run()


def main():
    cli(obj={})
