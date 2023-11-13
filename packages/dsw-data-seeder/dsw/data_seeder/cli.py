import click  # type: ignore
import pathlib

from typing import IO, Optional

from dsw.config.parser import MissingConfigurationError

from .config import SeederConfig, SeederConfigParser
from .consts import PROG_NAME, VERSION, NULL_UUID
from .seeder import DataSeeder, SeedRecipe


def validate_config(ctx, param, value: Optional[IO]):
    if value is None:
        content = ''
    else:
        content = value.read()
        value.close()
    parser = SeederConfigParser()
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


@click.group(name=PROG_NAME)
@click.version_option(version=VERSION)
@click.option('-c', '--config', envvar='APPLICATION_CONFIG_PATH',
              required=False, callback=validate_config,
              type=click.File('r', encoding='utf-8'))
@click.option('-w', '--workdir', envvar='WORKDIR_PATH',
              type=click.Path(dir_okay=True, exists=True))
@click.pass_context
def cli(ctx: click.Context, config: SeederConfig, workdir: str):
    ctx.obj['cfg'] = config
    ctx.obj['workdir'] = pathlib.Path(workdir).absolute()
    config.log.apply()


@cli.command(name='run', help='Run worker that listens to persistent commands.')
@click.option('-r', '--recipe', envvar='SEEDER_RECIPE')
@click.pass_context
def run(ctx: click.Context, recipe: str):
    cfg = ctx.obj['cfg']
    workdir = ctx.obj['workdir']
    seeder = DataSeeder(cfg=cfg, workdir=workdir)
    seeder.run(recipe)


@cli.command(name='seed', help='Seed data directly.')
@click.option('-r', '--recipe', envvar='SEEDER_RECIPE')
@click.option('-t', '--tenant-uuid', default=NULL_UUID)
@click.pass_context
def seed(ctx: click.Context, recipe: str, tenant_uuid: str):
    cfg = ctx.obj['cfg']
    workdir = ctx.obj['workdir']
    seeder = DataSeeder(cfg=cfg, workdir=workdir)
    seeder.seed(recipe_name=recipe, tenant_uuid=tenant_uuid)


@cli.command(name='list', help='List recipes for data seeding.')
@click.pass_context
def list(ctx: click.Context):
    workdir = ctx.obj['workdir']
    recipes = SeedRecipe.load_from_dir(workdir)
    for recipe in recipes.values():
        click.echo(recipe)
        click.echo('-'*40)


def main():
    cli(obj=dict())
