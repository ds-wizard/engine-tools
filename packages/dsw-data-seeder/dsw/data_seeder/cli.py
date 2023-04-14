import pathlib
import sys

from typing import IO, Optional

import click  # type: ignore

from dsw.config.parser import MissingConfigurationError

from .config import SeederConfig, SeederConfigParser
from .consts import PROG_NAME, VERSION, NULL_UUID
from .seeder import DataSeeder, SeedRecipe


def validate_config(ctx: click.Context, param: str, value: Optional[IO]):
    cli_param = ctx.params[param]  # type: click.Parameter
    if value is None:
        content = ''
    else:
        content = value.read()
        value.close()
    parser = SeederConfigParser()
    if not parser.can_read(content):
        click.echo(f'Error: Cannot parse config file '
                   f'(passed via {cli_param.name})', err=True)
        sys.exit(1)
    try:
        parser.read_string(content)
        parser.validate()
    except MissingConfigurationError as exc:
        click.echo('Error: Missing configuration', err=True)
        for missing_item in exc.missing:
            click.echo(f' - {missing_item}')
        sys.exit(1)
    return parser.config


@click.group(name=PROG_NAME)
@click.version_option(version=VERSION)
@click.option('-c', '--config', envvar='DSW_CONFIG',
              required=False, callback=validate_config,
              type=click.File('r', encoding='utf-8'))
@click.option('-w', '--workdir', envvar='SEEDER_WORKDIR',
              type=click.Path(dir_okay=True, exists=True))
@click.pass_context
def cli(ctx: click.Context, config: SeederConfig, workdir: str):
    ctx.obj['cfg'] = config
    ctx.obj['workdir'] = pathlib.Path(workdir).absolute()
    config.log.apply()


@cli.command()
@click.option('-r', '--recipe', envvar='SEEDER_RECIPE')
@click.pass_context
def run(ctx: click.Context, recipe: str):
    """Run worker that listens to persistent commands"""
    cfg = ctx.obj['cfg']
    workdir = ctx.obj['workdir']
    seeder = DataSeeder(cfg=cfg, workdir=workdir)
    seeder.run(recipe)


@cli.command()
@click.option('-r', '--recipe', envvar='SEEDER_RECIPE')
@click.option('-a', '--app_uuid', default=NULL_UUID)
@click.pass_context
def seed(ctx: click.Context, recipe: str, app_uuid: str):
    """Seed data in DSW directly"""
    cfg = ctx.obj['cfg']
    workdir = ctx.obj['workdir']
    seeder = DataSeeder(cfg=cfg, workdir=workdir)
    seeder.seed(recipe_name=recipe, app_uuid=app_uuid)


@cli.command()
@click.pass_context
def list_recipes(ctx: click.Context):
    """List recipes for data seeding"""
    workdir = ctx.obj['workdir']
    recipes = SeedRecipe.load_from_dir(workdir)
    for recipe in recipes.values():
        click.echo(recipe)
        click.echo('-'*40)


def main(ctx_obj=None):
    ctx_obj = ctx_obj or {}
    cli(obj=ctx_obj)  # pylint: disable=no-value-for-parameter
