import collections
import dateutil.parser
import json
import logging
import mimetypes
import pathlib
import uuid

from typing import Optional

from dsw.command_queue import CommandWorker, CommandQueue
from dsw.config.sentry import SentryReporter
from dsw.database.database import Database
from dsw.database.model import PersistentCommand
from dsw.storage import S3Storage

from .build_info import BUILD_INFO
from .config import SeederConfig
from .consts import DEFAULT_ENCODING, DEFAULT_MIMETYPE, DEFAULT_PLACEHOLDER, \
    COMPONENT_NAME, CMD_COMPONENT, CMD_CHANNEL, PROG_NAME
from .context import Context


LOG = logging.getLogger(__name__)


def _guess_mimetype(filename: str) -> str:
    try:
        content_type = mimetypes.guess_type(filename)[0]
        return content_type or DEFAULT_MIMETYPE
    except Exception:
        return DEFAULT_MIMETYPE


class SeedRecipe:

    def __init__(self, name: str, description: str, root: pathlib.Path,
                 db_scripts: list[pathlib.Path], db_placeholder: str,
                 s3_app_dir: Optional[pathlib.Path], s3_fname_replace: dict[str, str],
                 uuids_count: int, uuids_placeholder: Optional[str]):
        self.name = name
        self.description = description
        self.root = root
        self.db_scripts = db_scripts
        self.db_placeholder = db_placeholder
        self.s3_app_dir = s3_app_dir
        self.s3_fname_replace = s3_fname_replace
        self._db_scripts_data = collections.OrderedDict()  # type: dict[pathlib.Path, str]
        self.s3_objects = collections.OrderedDict()  # type: dict[pathlib.Path, str]
        self.prepared = False
        self.uuids_count = uuids_count
        self.uuids_placeholder = uuids_placeholder
        self.uuids_replacement = dict()  # type: dict[str, str]

    def _load_db_scripts(self):
        for db_script in self.db_scripts:
            self._db_scripts_data[db_script] = db_script.read_text(
                encoding=DEFAULT_ENCODING,
            )

    def _load_s3_object_names(self):
        if self.s3_app_dir is None:
            return
        for s3_object_path in self.s3_app_dir.glob('**/*'):
            if s3_object_path.is_file():
                target_object_name = str(
                    s3_object_path.relative_to(self.s3_app_dir).as_posix()
                )
                for r_from, r_to in self.s3_fname_replace.items():
                    target_object_name = target_object_name.replace(r_from, r_to)
                self.s3_objects[s3_object_path] = target_object_name

    def _prepare_uuids(self):
        if self.uuids_placeholder is not None:
            for i in range(self.uuids_count):
                key = self.uuids_placeholder.replace('[n]', f'[{i}]')
                self.uuids_replacement[key] = str(uuid.uuid4())

    def prepare(self):
        if self.prepared:
            return
        self._load_db_scripts()
        self._load_s3_object_names()
        self._prepare_uuids()
        self.prepared = True

    def run_prepare(self):
        self._prepare_uuids()

    def _replace_db_script(self, script: str, app_uuid: str) -> str:
        result = script.replace(self.db_placeholder, app_uuid)
        for uuid_key, uuid_value in self.uuids_replacement.items():
            result = result.replace(uuid_key, uuid_value)
        return result

    def iterate_db_scripts(self, app_uuid: str):
        return (
            (name, self._replace_db_script(script, app_uuid))
            for name, script in self._db_scripts_data.items()
        )

    def _replace_object_name(self, object_name: str) -> str:
        result = object_name
        for uuid_key, uuid_value in self.uuids_replacement.items():
            result = result.replace(uuid_key, uuid_value)
        return result

    def iterate_s3_objects(self):
        return (
            (local_name, self._replace_object_name(object_name))
            for local_name, object_name in self.s3_objects.items()
        )

    def __str__(self):
        scripts = '\n'.join((f'- {x}' for x in self.db_scripts))
        replaces = '\n'.join(
            (f'- "{x}" -> "{y}"' for x, y in self.s3_fname_replace.items())
        )
        return f'Recipe: {self.name}\n' \
               f'Loaded from: {self.root}\n' \
               f'{self.description}\n\n' \
               f'DB SQL Scripts:\n' \
               f'{scripts}\n' \
               f'DB APP UUID Placeholder: "{self.db_placeholder}"\n\n' \
               f'S3 App Dir:\n' \
               f'{self.s3_app_dir if self.s3_app_dir is not None else "[nothing]"}\n' \
               f'S3 Filename Replace:\n' \
               f'{replaces}'

    @staticmethod
    def load_from_json(recipe_file: pathlib.Path) -> 'SeedRecipe':
        data = json.loads(recipe_file.read_text(
            encoding=DEFAULT_ENCODING,
        ))
        db = data.get('db', {})  # type: dict
        s3 = data.get('s3', {})  # type: dict
        scripts = [
            pathlib.Path(x) for x in db.get('scripts', [])
        ]
        db_scripts = list()
        for script in scripts:
            if '*' in str(script):
                db_scripts.extend(
                    sorted([s for s in recipe_file.parent.glob(str(script))])
                )
            elif script.is_absolute():
                db_scripts.append(script)
            else:
                db_scripts.append(recipe_file.parent / script)
        s3_app_dir = None
        if 'appDir' in s3.keys():
            s3_app_dir = recipe_file.parent / s3['appDir']
        return SeedRecipe(
            name=data['name'],
            description=data.get('description', ''),
            root=recipe_file.parent,
            db_scripts=db_scripts,
            db_placeholder=db.get('appIdPlaceholder', DEFAULT_PLACEHOLDER),
            s3_app_dir=s3_app_dir,
            s3_fname_replace=s3.get('filenameReplace', {}),
            uuids_count=data.get('uuids', {}).get('count', 0),
            uuids_placeholder=data.get('uuids', {}).get('placeholder', None),
        )

    @staticmethod
    def load_from_dir(recipes_dir: pathlib.Path) -> dict[str, 'SeedRecipe']:
        recipe_files = recipes_dir.glob('*.seed.json')
        recipes = (SeedRecipe.load_from_json(f) for f in recipe_files)
        return {r.name: r for r in recipes}

    @staticmethod
    def create_default():
        return SeedRecipe(
            name='default',
            description='Default dummy recipe',
            root=pathlib.Path('/dev/null'),
            db_scripts=[],
            db_placeholder='<<|APP-ID|>>',
            s3_app_dir=pathlib.Path('/dev/null'),
            s3_fname_replace={},
            uuids_count=0,
            uuids_placeholder=None,
        )


class DataSeeder(CommandWorker):

    def __init__(self, cfg: SeederConfig, workdir: pathlib.Path):
        self.cfg = cfg
        self.workdir = workdir
        self.recipe = SeedRecipe.create_default()  # type: SeedRecipe

        self._init_context(workdir=workdir)

    def _init_context(self, workdir: pathlib.Path):
        Context.initialize(
            config=self.cfg,
            workdir=workdir,
            db=Database(cfg=self.cfg.db),
            s3=S3Storage(
                cfg=self.cfg.s3,
                multi_tenant=self.cfg.cloud.multi_tenant,
            ),
        )
        SentryReporter.initialize(
            dsn=self.cfg.sentry.workers_dsn,
            environment=self.cfg.general.environment,
            server_name=self.cfg.general.client_url,
            release=BUILD_INFO.version,
            prog_name=PROG_NAME,
            config=self.cfg.sentry,
        )

    def _prepare_recipe(self, recipe_name: str):
        LOG.info('Loading recipe')
        recipes = SeedRecipe.load_from_dir(self.workdir)
        if recipe_name not in recipes.keys():
            raise RuntimeError(f'Recipe "{recipe_name}" not found')
        LOG.info('Preparing seed recipe')
        self.recipe = recipes[recipe_name]
        self.recipe.prepare()

    def run(self, recipe_name: str):
        SentryReporter.set_context('recipe_name', recipe_name)
        # prepare
        self._prepare_recipe(recipe_name)
        self._update_component_info()
        # work in queue
        LOG.info('Preparing command queue')
        queue = CommandQueue(
            worker=self,
            db=Context.get().app.db,
            channel=CMD_CHANNEL,
            component=CMD_COMPONENT,
        )
        queue.run()

    def work(self, cmd: PersistentCommand):
        Context.get().update_trace_id(cmd.uuid)
        SentryReporter.set_context('cmd_uuid', cmd.uuid)
        self.recipe.run_prepare()
        app_uuid = cmd.body['appUuid']
        LOG.info(f'Seeding recipe "{self.recipe.name}" '
                 f'to app with UUID "{app_uuid}"')
        self.execute(app_uuid)
        Context.get().update_trace_id('-')
        SentryReporter.set_context('cmd_uuid', '-')

    @staticmethod
    def _update_component_info():
        built_at = dateutil.parser.parse(BUILD_INFO.built_at)
        LOG.info(f'Updating component info ({BUILD_INFO.version}, '
                 f'{built_at.isoformat(timespec="seconds")})')
        Context.get().app.db.update_component_info(
            name=COMPONENT_NAME,
            version=BUILD_INFO.version,
            built_at=built_at,
        )

    def seed(self, recipe_name: str, app_uuid: str):
        self._prepare_recipe(recipe_name)
        LOG.info(f'Executing recipe "{recipe_name}"')
        self.execute(app_uuid=app_uuid)
        LOG.info('Committing')
        Context().get().app.db.conn_query.connection.commit()

    def execute(self, app_uuid: str):
        SentryReporter.set_context('app_uuid', app_uuid)
        # Run SQL scripts
        app_ctx = Context.get().app
        cursor = app_ctx.db.conn_query.new_cursor(use_dict=True)
        phase = 'DB'
        try:
            LOG.info('Running SQL scripts')
            for path, script in self.recipe.iterate_db_scripts(app_uuid):
                LOG.debug(f' -> Executing script: {path.name}')
                cursor.execute(query=script)
                LOG.debug(f'    OK: {cursor.statusmessage}')
            phase = 'S3'
            LOG.info('Transferring S3 objects')
            for local_file, object_name in self.recipe.iterate_s3_objects():
                LOG.debug(f' -> Reading: {local_file.name}')
                data = local_file.read_bytes()
                LOG.debug(f' -> Sending: {object_name}')
                app_ctx.s3.store_object(
                    app_uuid=app_uuid,
                    object_name=object_name,
                    content_type=_guess_mimetype(local_file.name),
                    data=data,
                )
                LOG.debug('    OK (stored)')
        except Exception as e:
            SentryReporter.capture_exception(e)
            LOG.warning(f'Exception appeared [{type(e).__name__}]: {e}')
            LOG.info('Failed with unexpected error', exc_info=e)
            app_ctx.db.conn_query.connection.rollback()
            raise RuntimeError(f'{phase}: {e}')
        finally:
            LOG.info('Data seeding done')
            SentryReporter.set_context('app_uuid', '-')
            cursor.close()
