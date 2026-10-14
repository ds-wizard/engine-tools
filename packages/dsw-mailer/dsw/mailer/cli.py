from __future__ import annotations

import json
import pathlib
import sys
import typing

import click

from dsw.config.parser import InvalidConfigurationError, MissingConfigurationError

from . import consts, pot
from .config import MailerConfig, MailerConfigParser
from .mailer import Mailer, SentryReporter
from .model import MessageRequest


def load_config_str(config_str: str) -> MailerConfig:
    parser = MailerConfigParser()

    try:
        parser.read_string(config_str)
        parser.validate()
    except InvalidConfigurationError as e:
        click.echo('Error: Cannot parse config file', err=True)
        click.echo(f' - {e.message}', err=True)
        sys.exit(1)
    except MissingConfigurationError as e:
        click.echo('Error: Missing configuration', err=True)
        for missing_item in e.missing:
            click.echo(f' - {missing_item}', err=True)
        sys.exit(1)

    config = parser.config
    config.log.apply()
    return config


def validate_config(ctx, param, value: typing.IO | None):
    content = ''
    if value is not None:
        content = value.read()
        value.close()
    return load_config_str(content)


def extract_message_request(ctx, param, value: typing.IO):
    data = json.load(value)
    try:
        return MessageRequest.load_from_file(data)
    except Exception as e:
        click.echo('Error: Cannot parse message request', err=True)
        click.echo(f'{type(e).__name__}: {str(e)}')
        sys.exit(1)


@click.group(name='dsw-mailer', help='Mailer for sending emails from DSW')
@click.pass_context
@click.version_option(version=consts.VERSION)
@click.option('-c', '--config', envvar=consts.VAR_APP_CONFIG_PATH,
              required=False, type=click.Path(dir_okay=False),
              help='Configuration file, read only by the commands that need it.')
@click.option('-w', '--workdir', envvar=consts.VAR_WORKDIR_PATH,
              type=click.Path(file_okay=False, exists=True),
              help='Directory with the mail templates.')
def cli(ctx, config: str | None, workdir: str | None):
    ctx.ensure_object(dict)
    ctx.obj['config'] = config
    ctx.obj['workdir'] = workdir


def _templates_dir(ctx) -> pathlib.Path:
    if ctx.obj['workdir'] is None:
        raise click.UsageError(f'Missing the templates directory (--workdir or '
                               f'{consts.VAR_WORKDIR_PATH}).')
    return pathlib.Path(ctx.obj['workdir'])


def _mailer(ctx) -> Mailer:
    """The mailer is created only for the commands that need its configuration."""
    if 'mailer' not in ctx.obj:
        config_str = ''
        if ctx.obj['config'] is not None:
            try:
                config_str = pathlib.Path(ctx.obj['config']).read_text(
                    encoding=consts.DEFAULT_ENCODING)
            except OSError as e:
                raise click.BadParameter(str(e), param_hint="'-c' / '--config'") from e
        ctx.obj['mailer'] = Mailer(load_config_str(config_str), _templates_dir(ctx))
    return ctx.obj['mailer']


@cli.command(name='send', help='Send message(s) from given file directly.')
@click.pass_context
@click.argument('msg-request', type=click.File('r', encoding=consts.DEFAULT_ENCODING),
                callback=extract_message_request)
@click.option('-c', '--config', envvar=consts.VAR_APP_CONFIG_PATH,
              required=False, callback=validate_config,
              type=click.File('r', encoding=consts.DEFAULT_ENCODING))
def send(ctx, msg_request: MessageRequest, config: MailerConfig):
    mailer = _mailer(ctx)
    try:
        mailer.send(rq=msg_request, cfg=config.mail)
    except Exception as e:
        SentryReporter.capture_exception(e)
        click.echo(f'Error: {e}', err=True)
        sys.exit(2)


@cli.command(name='run', help='Run mailer worker processing message jobs.')
@click.pass_context
def run(ctx):
    mailer = _mailer(ctx)
    try:
        mailer.run()
    except Exception as e:
        SentryReporter.capture_exception(e)
        click.echo(f'Error: {e}', err=True)
        sys.exit(2)


@cli.command(name='make-pot',
             help='Build the POT of the mail templates, for translating them and for '
                  'sync-default-pot [default output: <TEMPLATES-DIR>/locale/mail.pot].')
@click.pass_context
@click.argument('templates-dir', required=False,
                type=click.Path(file_okay=False, exists=True))
@click.option('--kind', default=pot.DEFAULT_KIND, show_default=True,
              help='First part of Project-Id-Version (e.g. fw-mail-templates).')
@click.option('--version', 'pot_version', default=consts.VERSION, show_default=True,
              help='Second part of Project-Id-Version [default: the mailer version].')
@click.option('-o', '--output', type=click.Path(dir_okay=False), default=None)
def make_pot(ctx, templates_dir: str | None, kind: str, pot_version: str, output: str | None):
    templates = pathlib.Path(templates_dir) if templates_dir else _templates_dir(ctx)
    target = pathlib.Path(output) if output else templates / pot.POT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(pot.build_pot(templates, f'{kind}:{pot_version}'))
    click.echo(f'POT {kind}:{pot_version} written to {target}')


@cli.command(name='sync-default-pot',
             help='Make the default mail POT in S3 (mail-templates/mail.pot) the POT of the '
                  'templates, unless the stored one is newer. Run it after each deployment.')
@click.pass_context
@click.option('--force', is_flag=True, help='Replace the stored POT even if it is newer.')
def sync_default_pot(ctx, force: bool):
    mailer = _mailer(ctx)
    try:
        result = mailer.sync_default_pot(force=force)
    except Exception as e:
        SentryReporter.capture_exception(e)
        click.echo(f'Error: {e}', err=True)
        sys.exit(1)
    click.echo(f'Default mail POT: {result.value}')


def main():
    cli(obj={})
