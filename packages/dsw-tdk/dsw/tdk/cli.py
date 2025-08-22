# pylint: disable=too-many-positional-arguments
import asyncio
import datetime
import logging
import mimetypes
import pathlib
import signal
import sys

import click
import humanize
import slugify
import watchfiles

from .api_client import WizardCommunicationError
from .config import CONFIG
from .consts import VERSION, DEFAULT_LIST_FORMAT, DEFAULT_ENCODING
from .core import TDKCore, TDKProcessingError
from .model import Template
from .utils import TemplateBuilder, FormatSpec, safe_utf8, create_dot_env
from .validation import ValidationError

CURRENT_DIR = pathlib.Path.cwd()
DIR_TYPE = click.Path(exists=True, dir_okay=True, file_okay=False, resolve_path=True,
                      readable=True, writable=True)
FILE_READ_TYPE = click.Path(exists=True, dir_okay=False, file_okay=True, resolve_path=True,
                            readable=True)
NEW_DIR_TYPE = click.Path(dir_okay=True, file_okay=False, resolve_path=True,
                          readable=True, writable=True)


class ClickPrinter:

    CHANGE_SIGNS = {
        watchfiles.Change.added: click.style('+', fg='green'),
        watchfiles.Change.modified: click.style('*', fg='yellow'),
        watchfiles.Change.deleted: click.style('-', fg='red'),
    }

    @staticmethod
    def error(message: str, **kwargs):
        click.secho(message=message, err=True, fg='red', **kwargs)

    @staticmethod
    def warning(message: str, **kwargs):
        click.secho('WARNING', fg='yellow', bold=True, nl=False, **kwargs)
        click.echo(f': {message}')

    @staticmethod
    def success(message: str):
        click.secho('SUCCESS', fg='green', bold=True, nl=False)
        click.echo(f': {message}')

    @staticmethod
    def failure(message: str):
        click.secho('FAILURE', fg='red', bold=True, nl=False)
        click.echo(f': {message}')

    @staticmethod
    def watch(message: str):
        click.secho('WATCH', fg='blue', bold=True, nl=False)
        click.echo(f': {message}')

    @classmethod
    def watch_change(cls, change_type: watchfiles.Change, filepath: pathlib.Path,
                     root: pathlib.Path):
        timestamp = datetime.datetime.now().isoformat(timespec='milliseconds')
        sign = cls.CHANGE_SIGNS[change_type]
        click.secho('WATCH', fg='blue', bold=True, nl=False)
        click.echo(f'@{timestamp} {sign} {filepath.relative_to(root)}')


def prompt_fill(text: str, obj, attr, **kwargs):
    while True:
        try:
            value = safe_utf8(click.prompt(text, **kwargs).strip())
            setattr(obj, attr, value)
            break
        except ValidationError as e:
            ClickPrinter.error(e.message)


def print_template_info(template: Template):
    click.echo(f'Template ID: {template.id}')
    click.echo(f'Name:        {template.name}')
    click.echo(f'License:     {template.license}')
    click.echo(f'Description: {template.description}')
    click.echo('Formats:')
    for format_spec in template.formats:
        click.echo(f' - {format_spec.name}')
    click.echo('Files:')
    for template_file in template.files.values():
        filesize = humanize.naturalsize(len(template_file.content))
        click.echo(f' - {template_file.filename.as_posix()} [{filesize}]')


def ensure_api_config(api_url: str | None, api_key: str | None):
    if api_url is not None:
        CONFIG.use_local_env()
        CONFIG.set_api_url(api_url)
    if not CONFIG.has_api_url:
        CONFIG.set_api_url(
            api_url=click.prompt('API URL'),
        )
    if api_key is not None:
        CONFIG.use_local_env()
        CONFIG.set_api_key(api_key)
    if not CONFIG.has_api_key:
        CONFIG.set_api_key(
            api_key=click.prompt('API Key', hide_input=True),
        )
    if not CONFIG.has_api_url or not CONFIG.has_api_key:
        ClickPrinter.error('API URL and API Key are required to proceed.')
        sys.exit(1)


class ClickLogger(logging.Logger):

    NAME = 'DSW-TDK-CLI'
    LEVEL_STYLES = {
        logging.CRITICAL: lambda x: click.style(x, fg='red', bold=True),
        logging.ERROR: lambda x: click.style(x, fg='red'),
        logging.WARNING: lambda x: click.style(x, fg='yellow'),
        logging.INFO: lambda x: click.style(x, fg='cyan'),
        logging.DEBUG: lambda x: click.style(x, fg='magenta'),
    }
    LEVELS = [
        logging.getLevelName(logging.CRITICAL),
        logging.getLevelName(logging.ERROR),
        logging.getLevelName(logging.WARNING),
        logging.getLevelName(logging.INFO),
        logging.getLevelName(logging.DEBUG),
    ]

    def __init__(self, show_timestamp: bool = False, show_level: bool = True, colors: bool = True):
        super().__init__(name=self.NAME)
        self.show_timestamp = show_timestamp
        self.show_level = show_level
        self.colors = colors
        self.muted = False

    def _format_level(self, level, justify=False):
        name = logging.getLevelName(level)  # type: str
        if justify:
            name = name.ljust(8, ' ')
        if self.colors and level in self.LEVEL_STYLES:
            name = self.LEVEL_STYLES[level](name)
        return name

    def _print_message(self, level, message):
        if self.show_timestamp:
            timestamp = datetime.datetime.now().isoformat(timespec='milliseconds')
            click.echo(timestamp + ' | ', nl=False)
        if self.show_level:
            sep = ' | ' if self.show_timestamp else ': '
            click.echo(self._format_level(level, justify=self.show_timestamp) + sep, nl=False)
        click.echo(message)

    # pylint: disable-next=unused-argument
    def _log(self, level, msg, args, *other, **kwargs):
        if not self.muted and isinstance(msg, str):
            self._print_message(level, msg % args)

    @staticmethod
    def default():
        logger = ClickLogger()
        logger.setLevel('INFO')
        return logger


class AliasedGroup(click.Group):

    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [x for x in self.list_commands(ctx)
                   if x.startswith(cmd_name)]
        if not matches:
            return None
        if len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        return ctx.fail(f'Too many matches: {", ".join(sorted(matches))}')


class CLIContext:

    def __init__(self):
        self.logger = ClickLogger.default()
        self.dot_env_file = None

    def debug_mode(self):
        self.logger.show_timestamp = True
        self.logger.setLevel(level=logging.DEBUG)

    def quiet_mode(self):
        self.logger.muted = True


def interact_formats() -> dict[str, FormatSpec]:
    add_format = click.confirm('Do you want to add a format?', default=True)
    formats: dict[str, FormatSpec] = {}
    while add_format:
        format_spec = FormatSpec()
        prompt_fill('Format name', obj=format_spec, attr='name', default='HTML')
        if format_spec.name not in formats or click.confirm(
                'There is already a format with this name. Do you want to change it?'
        ):
            prompt_fill('File extension', obj=format_spec, attr='file_extension',
                        default=format_spec.name.lower() if ' ' not in format_spec.name else None)
            prompt_fill('Content type', obj=format_spec, attr='content_type',
                        default=mimetypes.types_map.get(f'.{format_spec.file_extension}', None))
            t_path = pathlib.Path('src') / f'template.{format_spec.file_extension}.j2'
            prompt_fill(
                text='Jinja2 filename',
                obj=format_spec,
                attr='filename',
                default=str(t_path),
            )
            formats[format_spec.name] = format_spec
        click.echo('=' * 60)
        add_format = click.confirm('Do you want to add yet another format?', default=False)
    return formats


def interact_builder(builder: TemplateBuilder):
    prompt_fill('Template name', obj=builder, attr='name')
    prompt_fill('Organization ID', obj=builder, attr='organization_id')
    prompt_fill('Template ID', obj=builder, attr='template_id',
                default=slugify.slugify(builder.name))
    prompt_fill('Version', obj=builder, attr='version',
                default='0.1.0')
    prompt_fill('Description', obj=builder, attr='description',
                default='My custom template')
    prompt_fill('License', obj=builder, attr='license',
                default='CC0')
    click.echo('=' * 60)
    formats = interact_formats()
    for format_spec in formats.values():
        builder.add_format(format_spec)


def load_local(tdk: TDKCore, template_dir: pathlib.Path):
    try:
        tdk.load_local(template_dir=template_dir)
    except Exception as e:
        ClickPrinter.failure('Could not load local template')
        ClickPrinter.error(f'> {e}')
        sys.exit(1)


def dir_from_id(template_id: str) -> pathlib.Path:
    return pathlib.Path.cwd() / template_id.replace(':', '_')


@click.group(cls=AliasedGroup)
@click.option('-d', '--dot-env', default='.env', required=False,
              show_default=True, type=click.Path(file_okay=True, dir_okay=False),
              help='File path to dot-env file with environment variables.')
@click.option('-e', '--environment', default=None, required=False,
              help='Configuration environment name.')
@click.option('--no-dot-env', is_flag=True, default=False,
              help='Do not load .env file, use only environment variables.')
@click.option('--no-config', is_flag=True, default=False,
              help='Do not load shared configuration, use only environment variables.')
@click.option('-q', '--quiet', is_flag=True,
              help='Hide additional information logs.')
@click.option('--debug', is_flag=True,
              help='Enable debug logging.')
@click.version_option(version=VERSION)
@click.pass_context
def main(ctx, quiet, debug, dot_env, environment, no_dot_env, no_config):
    if not no_config:
        try:
            CONFIG.load_home_config()
        except Exception as e:
            ClickPrinter.warning('Failed to load shared configuration')
            ClickPrinter.warning(f'> {e}')
    if not no_dot_env and dot_env is not None:
        dot_env_path = pathlib.Path(dot_env)
        if dot_env_path.exists():
            CONFIG.load_dotenv(path=dot_env_path)
    try:
        if environment is not None:
            CONFIG.switch_current_env(environment)
    except Exception as e:
        ClickPrinter.warning('Failed to set config environment')
        ClickPrinter.warning(f'> {e}')
    ctx.ensure_object(CLIContext)
    ctx.obj.dot_env_file = dot_env
    if quiet:
        ctx.obj.quiet_mode()
    if debug:
        ctx.obj.debug_mode()


@main.command(help='Create a new template project.', name='new')
@click.argument('TEMPLATE-DIR', type=NEW_DIR_TYPE, default=None, required=False)
@click.option('-f', '--force', is_flag=True, help='Overwrite any matching files.')
@click.pass_context
def new_template(ctx, template_dir, force):
    builder = TemplateBuilder()
    try:
        interact_builder(builder)
    except Exception:
        click.echo('')
        ClickPrinter.failure('Exited...')
        sys.exit(1)
    tdk = TDKCore(template=builder.build(), logger=ctx.obj.logger)
    template_dir = template_dir or dir_from_id(tdk.safe_template.id)
    tdk.prepare_local(template_dir=template_dir)
    try:
        tdk.store_local(force=force)
        ClickPrinter.success(f'Template project created: {template_dir}')
    except Exception as e:
        ClickPrinter.failure('Could not create new template project')
        ClickPrinter.error(f'> {e}')
        sys.exit(1)


@main.command(help='Download template from Wizard.', name='get')
@click.argument('TEMPLATE-ID')
@click.argument('TEMPLATE-DIR', type=NEW_DIR_TYPE, default=None, required=False)
@click.option('-u', '--api-url', metavar='API-URL', envvar='DSW_API_URL',
              help='URL of Wizard server API.')
@click.option('-k', '--api-key', metavar='API-KEY', envvar='DSW_API_KEY',
              help='API key for Wizard instance.')
@click.option('-f', '--force', is_flag=True, help='Overwrite any existing files.')
@click.pass_context
def get_template(ctx, template_id, template_dir, api_url, api_key, force):
    ensure_api_config(api_url, api_key)
    template_dir = pathlib.Path(template_dir or dir_from_id(template_id))

    async def main_routine():
        tdk = TDKCore(logger=ctx.obj.logger)
        template_type = 'unknown'
        zip_data = None
        try:
            await tdk.init_client(
                api_url=CONFIG.env.api_url,
                api_key=CONFIG.env.api_key,
            )
            try:
                await tdk.load_remote(template_id=template_id)
                template_type = 'draft'
            except Exception:
                zip_data = await tdk.download_bundle(template_id=template_id)
                template_type = 'bundle'
            await tdk.safe_client.close()
        except WizardCommunicationError as e:
            ClickPrinter.error('Could not get template:', bold=True)
            ClickPrinter.error(f'> {e.reason}\n> {e.message}')
            await tdk.safe_client.close()
            sys.exit(1)
        await tdk.safe_client.safe_close()
        if template_type == 'draft':
            tdk.prepare_local(template_dir=template_dir)
            try:
                tdk.store_local(force=force)
                ClickPrinter.success(f'Template draft {template_id} '
                                     f'downloaded to {template_dir}')
            except Exception as e:
                ClickPrinter.failure('Could not store template locally')
                ClickPrinter.error(f'> {e}')
                await tdk.safe_client.close()
                sys.exit(1)
        elif template_type == 'bundle' and zip_data is not None:
            try:
                tdk.extract_package(zip_data=zip_data, template_dir=template_dir, force=force)
                ClickPrinter.success(f'Template {template_id} (released) '
                                     f'downloaded to {template_dir}')
            except Exception as e:
                ClickPrinter.failure('Could not store template locally')
                ClickPrinter.error(f'> {e}')
                await tdk.safe_client.close()
                sys.exit(1)
        else:
            ClickPrinter.failure(f'{template_id} is not released nor draft of a document template')
            sys.exit(1)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_routine())


@main.command(help='Upload template to Wizard.', name='put')
@click.argument('TEMPLATE-DIR', type=DIR_TYPE, default=CURRENT_DIR, required=False)
@click.option('-u', '--api-url', metavar='API-URL', envvar='DSW_API_URL',
              help='URL of Wizard server API.')
@click.option('-k', '--api-key', metavar='API-KEY', envvar='DSW_API_KEY',
              help='API key for Wizard instance.')
@click.option('-f', '--force', is_flag=True,
              help='Delete template if already exists.')
@click.option('-w', '--watch', is_flag=True,
              help='Enter watch mode to continually upload changes.')
@click.pass_context
def put_template(ctx, template_dir, api_url, api_key, force, watch):
    ensure_api_config(api_url, api_key)
    tdk = TDKCore(logger=ctx.obj.logger)
    stop_event = asyncio.Event()

    async def watch_callback(changes):
        changes = list(changes)
        for change in changes:
            ClickPrinter.watch_change(
                change_type=change[0],
                filepath=change[1],
                root=tdk.safe_project.template_dir,
            )
        if len(changes) > 0:
            await tdk.process_changes(changes, force=force)

    async def main_routine():
        load_local(tdk, template_dir)
        try:
            await tdk.init_client(
                api_url=CONFIG.env.api_url,
                api_key=CONFIG.env.api_key,
            )
            await tdk.store_remote(force=force)
            ClickPrinter.success(f'Template {tdk.safe_project.safe_template.id} '
                                 f'uploaded to {api_url}')

            if watch:
                ClickPrinter.watch('Entering watch mode... (press Ctrl+C to abort)')
                await tdk.watch_project(watch_callback, stop_event)

            await tdk.safe_client.close()
        except TDKProcessingError as e:
            ClickPrinter.failure('Could not upload template')
            ClickPrinter.error(f'> {e.message}\n> {e.hint}')
            await tdk.safe_client.safe_close()
            sys.exit(1)
        except WizardCommunicationError as e:
            ClickPrinter.failure('Could not upload template')
            ClickPrinter.error(f'> {e.reason}\n> {e.message}')
            ClickPrinter.error('> Probably incorrect API URL, metamodel version, '
                               'or template already exists...')
            ClickPrinter.error('> Check if you are using the matching version')
            await tdk.safe_client.safe_close()
            sys.exit(1)

    # pylint: disable-next=unused-argument
    def set_stop_event(signal_num, frame):
        signal_name = signal.Signals(signal_num).name
        ClickPrinter.warning(f'Got {signal_name}, finishing... Bye!')
        stop_event.set()

    signal.signal(signal.SIGINT, set_stop_event)
    signal.signal(signal.SIGABRT, set_stop_event)

    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(main_routine())
    loop.run_until_complete(main_task)


@main.command(help='Create ZIP package for a template.', name='package')
@click.argument('TEMPLATE-DIR', type=DIR_TYPE, default=CURRENT_DIR, required=False)
@click.option('-o', '--output', default='template.zip', type=click.Path(writable=True),
              show_default=True, help='Target package file.')
@click.option('-f', '--force', is_flag=True, help='Delete package if already exists.')
@click.pass_context
def create_package(ctx, template_dir, output, force: bool):
    tdk = TDKCore(logger=ctx.obj.logger)
    load_local(tdk, template_dir)
    try:
        tdk.create_package(output=pathlib.Path(output), force=force)
    except Exception as e:
        ClickPrinter.failure('Failed to create the package')
        ClickPrinter.error(f'> {e}')
        sys.exit(1)
    filename = click.style(output, bold=True)
    ClickPrinter.success(f'Package {filename} created')


@main.command(help='Extract a template from ZIP package', name='unpackage')
@click.argument('TEMPLATE-PACKAGE', type=FILE_READ_TYPE, required=False)
@click.option('-o', '--output', type=NEW_DIR_TYPE, default=None, required=False,
              help='Target package file.')
@click.option('-f', '--force', is_flag=True, help='Overwrite folder if already exists.')
@click.pass_context
def extract_package(ctx, template_package, output, force: bool):
    tdk = TDKCore(logger=ctx.obj.logger)
    try:
        data = pathlib.Path(template_package).read_bytes()
        tdk.extract_package(
            zip_data=data,
            template_dir=pathlib.Path(output) if output is not None else output,
            force=force,
        )
    except Exception as e:
        ClickPrinter.failure('Failed to extract the package')
        ClickPrinter.error(f'> {e}')
        sys.exit(1)
    ClickPrinter.success(f'Package {template_package} extracted')


@main.command(help='List templates from Wizard via API.', name='list')
@click.option('-u', '--api-url', metavar='API-URL', envvar='DSW_API_URL',
              help='URL of Wizard server API.')
@click.option('-k', '--api-key', metavar='API-KEY', envvar='DSW_API_KEY',
              help='API key for Wizard instance.')
@click.option('--output-format', default=DEFAULT_LIST_FORMAT,
              metavar='FORMAT', help='Entry format string for printing.')
@click.option('-r', '--released-only', is_flag=True, help='List only released templates')
@click.option('-d', '--drafts-only', is_flag=True, help='List only template drafts')
@click.pass_context
def list_templates(ctx, api_url, api_key, output_format: str,
                   released_only: bool, drafts_only: bool):
    ensure_api_config(api_url, api_key)

    async def main_routine():
        tdk = TDKCore(logger=ctx.obj.logger)
        try:
            await tdk.init_client(
                api_url=CONFIG.env.api_url,
                api_key=CONFIG.env.api_key,
            )
            if released_only:
                templates = await tdk.list_remote_templates()
                for template in templates:
                    click.echo(output_format.format(template=template))
            elif drafts_only:
                drafts = await tdk.list_remote_drafts()
                for template in drafts:
                    click.echo(output_format.format(template=template))
            else:
                click.echo('Document Templates (released)')
                templates = await tdk.list_remote_templates()
                for template in templates:
                    click.echo(output_format.format(template=template))
                click.echo('\nDocument Templates Drafts')
                drafts = await tdk.list_remote_drafts()
                for template in drafts:
                    click.echo(output_format.format(template=template))
            await tdk.safe_client.safe_close()

        except WizardCommunicationError as e:
            ClickPrinter.failure('Failed to get list of templates')
            ClickPrinter.error(f'> {e.reason}\n> {e.message}')
            await tdk.safe_client.safe_close()
            sys.exit(1)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_routine())


@main.command(help='Verify a template project.', name='verify')
@click.argument('TEMPLATE-DIR', type=DIR_TYPE, default=CURRENT_DIR, required=False)
@click.pass_context
def verify_template(ctx, template_dir):
    tdk = TDKCore(logger=ctx.obj.logger)
    load_local(tdk, template_dir)
    errors = tdk.verify()
    if len(errors) == 0:
        ClickPrinter.success('The template is valid!')
        print_template_info(template=tdk.safe_project.safe_template)
    else:
        ClickPrinter.failure('The template is invalid!')
        click.echo('Found violations:')
        for err in errors:
            click.echo(f' - {err.field_name}: {err.message}')


@main.group(help='Manage shared user configuration (~/.dsw-tdk).', name='config')
@click.pass_context
# pylint: disable-next=unused-argument
def config(ctx):
    pass


@config.command(name='init', help='Initialize the shared user configuration (~/.dsw-tdk).')
@click.option('-f', '--force', is_flag=True, help='Overwrite file if already exists.')
def config_init(force):
    if CONFIG.HOME_CONFIG.exists() and not force:
        ClickPrinter.error('Configuration file already exists. Use `--force` to overwrite it.')
        sys.exit(1)
    CONFIG.shared_envs.clear()
    CONFIG.default_env_name = None

    click.echo('You need to specify your first environment name (default one).')
    click.echo('Recommendation: use short and lowercase name, e.g. "production"')
    environment = click.prompt('Environment name', default='production')
    api_url = click.prompt('API URL')
    api_key = click.prompt('API Key', hide_input=True)
    try:
        CONFIG.add_shared_env(
            name=environment,
            api_url=api_url,
            api_key=api_key,
        )
        CONFIG.default_env_name = environment
    except Exception as e:
        ClickPrinter.failure('Failed to add environment')
        ClickPrinter.error(f'> {e}')
        sys.exit(1)
    while True:
        add_another = click.confirm('Do you want to add another environment?', default=False)
        if not add_another:
            break
        environment = click.prompt('Environment name')
        api_url = click.prompt('API URL')
        api_key = click.prompt('API Key', hide_input=True)
        try:
            CONFIG.add_shared_env(
                name=environment,
                api_url=api_url,
                api_key=api_key,
            )
        except Exception as e:
            ClickPrinter.failure('Failed to add environment (skipping)')
            ClickPrinter.warning(f'> {e}')

    try:
        CONFIG.persist(force=force)
        ClickPrinter.success('Configuration initialized successfully.')
    except Exception as e:
        ClickPrinter.failure('Failed to initialize configuration')
        ClickPrinter.error(f'> {e}')
        sys.exit(1)


@config.command(name='edit', help='Edit the shared user configuration (~/.dsw-tdk).')
@click.option('-f', '--force', is_flag=True, help='Create file if does not exist.')
def config_edit(force):
    if not CONFIG.HOME_CONFIG.exists():
        if force:
            CONFIG.HOME_CONFIG.parent.mkdir(parents=True, exist_ok=True)
            CONFIG.HOME_CONFIG.touch()
        else:
            ClickPrinter.error('Configuration file does not exist. Use `init` command '
                               'or `--force` flag to create it.')
            sys.exit(1)
    click.edit(
        filename=str(CONFIG.HOME_CONFIG),
        extension='.cfg',
        require_save=True,
    )


@config.command(name='check', help='Check the current configuration that can be loaded.')
def config_check():
    hidden = click.style('(hidden)', fg='red', bold=True)
    not_set = click.style('(not set)', fg='yellow', bold=True)
    click.secho('Shared configuration (~/.dsw-tdk):', bold=True)
    for env_name, env in CONFIG.shared_envs.items():
        if env_name == CONFIG.current_env_name:
            env_out = click.style(env_name, fg='green', bold=True)
            click.echo(f'{env_out} (current)')
        elif env_name == CONFIG.default_env_name:
            env_out = click.style(env_name, fg='cyan', bold=True)
            click.echo(f'{env_out} (default)')
        else:
            env_out = click.style(env_name, fg='blue', bold=True)
            click.echo(env_out)
        click.echo(f'  API URL: {env.api_url if env.api_url else not_set}')
        click.echo(f'  API Key: {hidden if env.api_key else not_set}')
    click.echo('')
    click.secho('Project-local configuration:', bold=True)
    if CONFIG.current_env_name == CONFIG.LOCAL_CONFIG:
        env_out = click.style(CONFIG.LOCAL_CONFIG, fg='green', bold=True)
        click.echo(f'{env_out} (current)')
    else:
        env_out = click.style('local', fg='blue', bold=True)
        click.echo(env_out)
    if CONFIG.local_env.api_url:
        click.echo(f'  API URL: {CONFIG.local_env.api_url}')
    else:
        click.echo(f'  API URL: {not_set}')
    if CONFIG.local_env.api_key:
        click.echo(f'  API Key: {hidden}')
    else:
        click.echo(f'  API Key: {not_set}')


@config.command(name='dot-env', help='Create a .env file with API configuration.')
@click.argument('TEMPLATE-DIR', type=DIR_TYPE, default=CURRENT_DIR, required=False)
@click.option('-u', '--api-url', metavar='API-URL', envvar='DSW_API_URL',
              help='URL of Wizard server API.')
@click.option('-k', '--api-key', metavar='API-KEY', envvar='DSW_API_KEY',
              help='API key for Wizard instance.')
@click.option('-f', '--force', is_flag=True, help='Overwrite file if already exists.')
@click.pass_context
def config_create_dotenv(ctx, template_dir, api_url, api_key, force):
    ensure_api_config(api_url, api_key)
    filename = ctx.obj.dot_env_file or '.env'
    output = pathlib.Path(template_dir) / filename
    try:
        if output.exists():
            if force:
                ClickPrinter.warning(f'Overwriting {output.as_posix()} (forced)', )
            else:
                raise FileExistsError(f'File {output.as_posix()} already exists (not forced)')
        output.write_text(
            data=create_dot_env(
                api_url=CONFIG.env.api_url,
                api_key=CONFIG.env.api_key,
            ),
            encoding=DEFAULT_ENCODING,
        )
    except Exception as e:
        ClickPrinter.failure('Failed to create dot-env file')
        ClickPrinter.error(f'> {e}')
        sys.exit(1)
