import pathlib
import sys
import typing

import click

from dsw.config.parser import MissingConfigurationError

from .config import SeederConfig, SeederConfigParser
from .consts import (PROG_NAME, VERSION, NULL_UUID, DEFAULT_ENCODING,
                     VAR_SEEDER_RECIPE, VAR_WORKDIR_PATH, VAR_APP_CONFIG_PATH)
from .seeder import DataSeeder, SeedRecipe, SentryReporter


def load_config_str(config_str: str) -> SeederConfig:
    parser = SeederConfigParser()
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


@click.group(name=PROG_NAME)
@click.version_option(version=VERSION)
@click.option('-c', '--config', envvar=VAR_APP_CONFIG_PATH,
              required=False, callback=validate_config,
              type=click.File('r', encoding=DEFAULT_ENCODING))
@click.option('-w', '--workdir', envvar=VAR_WORKDIR_PATH,
              type=click.Path(dir_okay=True, exists=True))
@click.pass_context
def cli(ctx: click.Context, config: SeederConfig, workdir: str):
    ctx.obj['cfg'] = config
    ctx.obj['workdir'] = pathlib.Path(workdir).absolute()


@cli.command(name='run', help='Run worker that listens to persistent commands.')
@click.option('-r', '--recipe', envvar=VAR_SEEDER_RECIPE, required=True)
@click.pass_context
def run(ctx: click.Context, recipe: str):
    cfg = ctx.obj['cfg']
    workdir = ctx.obj['workdir']
    seeder = DataSeeder(
        cfg=cfg,
        workdir=workdir,
        default_recipe_name=recipe,
    )
    try:
        seeder.run()
    except Exception as e:
        click.echo(f'Error: {e}', err=True)
        SentryReporter.capture_exception(e)
        sys.exit(2)


@cli.command(name='seed', help='Seed data directly.')
@click.option('-r', '--recipe', envvar=VAR_SEEDER_RECIPE, required=True)
@click.option('-t', '--tenant-uuid', default=NULL_UUID)
@click.pass_context
def seed(ctx: click.Context, recipe: str, tenant_uuid: str):
    cfg = ctx.obj['cfg']
    workdir = ctx.obj['workdir']
    seeder = DataSeeder(
        cfg=cfg,
        workdir=workdir,
        default_recipe_name=recipe,
    )
    try:
        seeder.seed(
            recipe_name=recipe,
            tenant_uuid=tenant_uuid,
        )
    except Exception as e:
        click.echo(f'Error: {e}', err=True)
        SentryReporter.capture_exception(e)
        sys.exit(2)


@cli.command(name='list', help='List recipes for data seeding.')
@click.pass_context
def recipes_list(ctx: click.Context):
    workdir = ctx.obj['workdir']
    recipes = SeedRecipe.load_from_dir(workdir)
    for recipe in recipes.values():
        click.echo(recipe)
        click.echo('-'*40)


def main():
    # pylint: disable-next=no-value-for-parameter
    cli(obj={})
