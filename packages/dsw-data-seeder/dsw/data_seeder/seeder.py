import collections
import json
import logging
import mimetypes
import pathlib
import time
import typing
import uuid

import dateutil.parser

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


class DBScript:

    def __init__(self, filepath: pathlib.Path, target: str, order: int):
        self.filepath = filepath
        self.target = target
        self.order = order

    @property
    def id(self) -> str:
        return f'{self.order}::{self.filepath.as_posix()}::{self.target}'


class SeedRecipe:

    # pylint: disable-next=too-many-arguments
    def __init__(self, *, name: str, description: str, root: pathlib.Path,
                 db_scripts: dict[str, DBScript], db_placeholder: str,
                 s3_dir: pathlib.Path | None, s3_fname_replace: dict[str, str],
                 uuids_count: int, uuids_placeholder: str | None,
                 init_wait: float):
        # pylint: disable-next=too-many-instance-attributes
        self.name = name
        self.description = description
        self.root = root
        self.db_scripts = db_scripts
        self.db_placeholder = db_placeholder
        self.s3_dir = s3_dir
        self.s3_fname_replace = s3_fname_replace
        self._db_scripts_data: dict[str, str] = collections.OrderedDict()
        self.s3_objects: dict[pathlib.Path, str] = collections.OrderedDict()
        self.prepared = False
        self.uuids_count = uuids_count
        self.uuids_placeholder = uuids_placeholder
        self.uuids_replacement: dict[str, str] = {}
        self.init_wait = init_wait

    def _load_db_scripts(self):
        for script_id, db_script in self.db_scripts.items():
            self._db_scripts_data[script_id] = db_script.filepath.read_text(
                encoding=DEFAULT_ENCODING,
            )

    def _load_s3_object_names(self):
        if self.s3_dir is None:
            return
        for s3_object_path in self.s3_dir.glob('**/*'):
            if s3_object_path.is_file():
                target_object_name = str(
                    s3_object_path.relative_to(self.s3_dir).as_posix()
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

    def _replace_db_script(self, script: str, tenant_uuid: str) -> str:
        result = script.replace(self.db_placeholder, tenant_uuid)
        for uuid_key, uuid_value in self.uuids_replacement.items():
            result = result.replace(uuid_key, uuid_value)
        return result

    def iterate_db_scripts(self, tenant_uuid: str):
        return (
            (script_id, self._replace_db_script(script, tenant_uuid))
            for script_id, script in self._db_scripts_data.items()
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
               f'DB Tenant UUID Placeholder: "{self.db_placeholder}"\n\n' \
               f'S3 Directory:\n' \
               f'{self.s3_dir if self.s3_dir is not None else "[nothing]"}\n' \
               f'S3 Filename Replace:\n' \
               f'{replaces}'

    @staticmethod
    def load_from_json(recipe_file: pathlib.Path) -> 'SeedRecipe':
        data = json.loads(recipe_file.read_text(
            encoding=DEFAULT_ENCODING,
        ))
        db: dict[str, typing.Any] = data.get('db', {})
        s3: dict[str, typing.Any] = data.get('s3', {})
        scripts: list[dict] = db.get('scripts', [])
        db_scripts: dict[str, DBScript] = collections.OrderedDict()
        for index, script in enumerate(scripts):
            target = script.get('target', '')
            filename = str(script.get('filename', ''))
            if filename == '':
                continue
            filepath = pathlib.Path(filename)
            if '*' in filename:
                for item in sorted(list(recipe_file.parent.glob(filename))):
                    s = DBScript(item, target, index)
                    db_scripts[s.id] = s
            elif filepath.is_absolute():
                s = DBScript(filepath, target, index)
                db_scripts[s.id] = s
            else:
                s = DBScript(recipe_file.parent / filepath, target, index)
                db_scripts[s.id] = s
        s3_dir = None
        if 'dir' in s3.keys():
            s3_dir = recipe_file.parent / s3['dir']
        return SeedRecipe(
            name=data['name'],
            description=data.get('description', ''),
            root=recipe_file.parent,
            db_scripts=db_scripts,
            db_placeholder=db.get('tenantIdPlaceholder', DEFAULT_PLACEHOLDER),
            s3_dir=s3_dir,
            s3_fname_replace=s3.get('filenameReplace', {}),
            uuids_count=data.get('uuids', {}).get('count', 0),
            uuids_placeholder=data.get('uuids', {}).get('placeholder', None),
            init_wait=data.get('initWait', 0),
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
            db_scripts={},
            db_placeholder=DEFAULT_PLACEHOLDER,
            s3_dir=pathlib.Path('/dev/null'),
            s3_fname_replace={},
            uuids_count=0,
            uuids_placeholder=None,
            init_wait=0,
        )


class DataSeeder(CommandWorker):

    def __init__(self, cfg: SeederConfig, workdir: pathlib.Path):
        self.cfg = cfg
        self.workdir = workdir
        self.recipe = SeedRecipe.create_default()  # type: SeedRecipe
        self.dbs = {}  # type: dict[str, Database]

        self._init_context(workdir=workdir)
        self._init_sentry()
        self._init_extra_connections()

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

    def _init_sentry(self):
        SentryReporter.initialize(
            config=self.cfg.sentry,
            release=BUILD_INFO.version,
            prog_name=PROG_NAME,
        )

    def _init_extra_connections(self):
        for db_id, extra_db_cfg in Context.get().app.cfg.extra_dbs.items():
            self.dbs[db_id] = Database(cfg=extra_db_cfg, with_queue=False)

    def _prepare_recipe(self, recipe_name: str):
        LOG.info('Loading recipe')
        recipes = SeedRecipe.load_from_dir(self.workdir)
        if recipe_name not in recipes.keys():
            raise RuntimeError(f'Recipe "{recipe_name}" not found')
        LOG.info('Preparing seed recipe')
        self.recipe = recipes[recipe_name]
        self.recipe.prepare()

    def _run_preparation(self, recipe_name: str) -> CommandQueue:
        SentryReporter.set_tags(recipe_name=recipe_name)
        # prepare
        self._prepare_recipe(recipe_name)
        self._update_component_info()
        # init queue
        LOG.info('Preparing command queue')
        queue = CommandQueue(
            worker=self,
            db=Context.get().app.db,
            channel=CMD_CHANNEL,
            component=CMD_COMPONENT,
            wait_timeout=Context.get().app.cfg.db.queue_timeout,
            work_timeout=Context.get().app.cfg.experimental.job_timeout,
        )
        return queue

    def run(self, recipe_name: str):
        LOG.info('Starting seeder worker (loop)')
        queue = self._run_preparation(recipe_name)
        queue.run()

    def run_once(self, recipe_name: str):
        LOG.info('Starting seeder worker (once)')
        queue = self._run_preparation(recipe_name)
        queue.run_once()

    def work(self, command: PersistentCommand):
        Context.get().update_trace_id(command.uuid)
        SentryReporter.set_tags(command_uuid=command.uuid)
        self.recipe.run_prepare()
        tenant_uuid = command.body['tenantUuid']
        LOG.info('Seeding recipe "%s" to tenant "%s"',
                 self.recipe.name, tenant_uuid)
        if command.attempts == 0 and self.recipe.init_wait > 0.01:
            LOG.info('Waiting for %s seconds (first attempt)',
                     self.recipe.init_wait)
            time.sleep(self.recipe.init_wait)
        self.execute(tenant_uuid)
        Context.get().update_trace_id('-')
        SentryReporter.set_tags(command_uuid='-')

    def process_timeout(self, e: BaseException):
        LOG.error('Failed with timeout', exc_info=e)

    def process_exception(self, e: BaseException):
        LOG.error('Failed with unexpected error', exc_info=e)

    @staticmethod
    def _update_component_info():
        built_at = dateutil.parser.parse(BUILD_INFO.built_at)
        LOG.info('Updating component info (%s, %s)',
                 BUILD_INFO.version, built_at.isoformat(timespec="seconds"))
        Context.get().app.db.update_component_info(
            name=COMPONENT_NAME,
            version=BUILD_INFO.version,
            built_at=built_at,
        )

    def seed(self, recipe_name: str, tenant_uuid: str):
        self._prepare_recipe(recipe_name)
        LOG.info('Executing recipe "%s"', recipe_name)
        self.execute(tenant_uuid=tenant_uuid)

    def execute(self, tenant_uuid: str):
        SentryReporter.set_tags(tenant_uuid=tenant_uuid)
        # Run SQL scripts
        app_ctx = Context.get().app
        phase = 'DB'
        used_targets = set()
        try:
            LOG.info('Running SQL scripts')
            for script_id, sql_script in self.recipe.iterate_db_scripts(tenant_uuid):
                LOG.debug(' -> Executing script: %s', script_id)
                script = self.recipe.db_scripts[script_id]
                if script.target in self.dbs:
                    used_targets.add(script.target)
                    with self.dbs[script.target].conn_query.new_cursor(use_dict=True) as c:
                        c.execute(query=sql_script)
                else:
                    with app_ctx.db.conn_query.new_cursor(use_dict=True) as c:
                        c.execute(query=sql_script)

            phase = 'S3'
            LOG.info('Transferring S3 objects')
            for local_file, object_name in self.recipe.iterate_s3_objects():
                LOG.debug(' -> Reading: %s', local_file.name)
                data = local_file.read_bytes()
                LOG.debug(' -> Sending: %s', object_name)
                app_ctx.s3.store_object(
                    tenant_uuid=tenant_uuid,
                    object_name=object_name,
                    content_type=_guess_mimetype(local_file.name),
                    data=data,
                )
                LOG.debug('    OK (stored)')
        except Exception as e:
            LOG.warning('Exception appeared [%s]: %s', type(e).__name__, e)
            LOG.error('Failed with unexpected error', exc_info=e)
            LOG.info('Rolling back DB changes')

            LOG.debug('Used extra DBs: %s', str(used_targets))
            conn = app_ctx.db.conn_query.connection
            LOG.debug('DEFAULT will roll back: %s / %s',
                      conn.pgconn.status, conn.pgconn.transaction_status)
            conn.rollback()
            LOG.debug('DEFAULT rolled back: %s / %s',
                      conn.pgconn.status, conn.pgconn.transaction_status)
            for target in used_targets:
                conn = self.dbs[target].conn_query.connection
                LOG.debug('%s will roll back: %s / %s',
                          target, conn.pgconn.status, conn.pgconn.transaction_status)
                conn.rollback()
                LOG.debug('%s rolled back: %s / %s',
                          target, conn.pgconn.status, conn.pgconn.transaction_status)
            raise RuntimeError(f'{phase}: {e}') from e
        else:
            LOG.info('Committing DB changes')
            app_ctx.db.conn_query.connection.commit()
            for target in used_targets:
                self.dbs[target].conn_query.connection.commit()
        finally:
            LOG.info('Data seeding done')
            SentryReporter.set_tags(tenant_uuid='-')
