import collections
import dataclasses
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


@dataclasses.dataclass
class SeedRecipeDirective:
    path: pathlib.Path
    target: str | None
    order: int

    @property
    def id(self) -> str:
        return f'{self.order}::{self.path.as_posix()}::{self.target}'


@dataclasses.dataclass
class SeedRecipeDB:
    scripts: dict[str, SeedRecipeDirective]
    tenant_placeholder: str
    scripts_data: dict[str, str] = dataclasses.field(default_factory=collections.OrderedDict)

    @staticmethod
    def from_dict(data: dict, root_path: pathlib.Path) -> 'SeedRecipeDB':
        recipe_scripts: list[dict] = data.get('scripts', [])
        db_scripts: dict[str, SeedRecipeDirective] = collections.OrderedDict()
        for index, script in enumerate(recipe_scripts):
            target = script.get('target', None)
            path = str(script.get('path', ''))
            if path == '':
                continue
            filepath = pathlib.Path(path)
            if '*' in path:
                for item in sorted(list(root_path.glob(path))):
                    s = SeedRecipeDirective(item, target, index)
                    db_scripts[s.id] = s
            elif filepath.is_absolute():
                s = SeedRecipeDirective(filepath, target, index)
                db_scripts[s.id] = s
            else:
                s = SeedRecipeDirective(root_path / filepath, target, index)
                db_scripts[s.id] = s
        return SeedRecipeDB(
            scripts=db_scripts,
            tenant_placeholder=data.get('tenantIdPlaceholder', DEFAULT_PLACEHOLDER),
        )

    def load_db_scripts(self):
        for script_id, db_script in self.scripts.items():
            self.scripts_data[script_id] = db_script.path.read_text(
                encoding=DEFAULT_ENCODING,
            )


@dataclasses.dataclass
class SeedRecipeS3Object:
    local_path: pathlib.Path
    object_name: str
    target: str | None

    def __str__(self):
        return f'{self.local_path.as_posix()} -> {self.object_name} [{self.target}]'

    def update_object_name(self, replacements: dict[str, str]):
        for r_from, r_to in replacements.items():
            self.object_name = self.object_name.replace(r_from, r_to)


@dataclasses.dataclass
class SeedRecipeS3:
    copy: dict[str, SeedRecipeDirective]
    filename_replace: dict[str, str]
    objects: list[SeedRecipeS3Object] = dataclasses.field(default_factory=list)

    @staticmethod
    def from_dict(data: dict, root_path: pathlib.Path) -> 'SeedRecipeS3':
        recipe_copy: list[dict] = data.get('copy', [])
        copy_instructions: dict[str, SeedRecipeDirective] = collections.OrderedDict()
        for index, instruction in enumerate(recipe_copy):
            target = instruction.get('target', None)
            path = str(instruction.get('path', ''))
            if path == '':
                continue
            filepath = pathlib.Path(path)
            if '*' in path:
                for item in sorted(list(root_path.glob(path))):
                    s = SeedRecipeDirective(item, target, index)
                    copy_instructions[s.id] = s
            elif filepath.is_absolute():
                s = SeedRecipeDirective(filepath, target, index)
                copy_instructions[s.id] = s
            else:
                s = SeedRecipeDirective(root_path / filepath, target, index)
                copy_instructions[s.id] = s
        return SeedRecipeS3(
            copy=copy_instructions,
            filename_replace=data.get('filenameReplace', {}),
        )

    def load_s3_object_names(self):
        for s3_copy in self.copy.values():
            if s3_copy.path.is_dir():
                target = s3_copy.target
                for s3_object_path in s3_copy.path.glob('**/*'):
                    if s3_object_path.is_file():
                        target_object_name = str(
                            s3_object_path.relative_to(s3_copy.path).as_posix()
                        )
                        for r_from, r_to in self.filename_replace.items():
                            target_object_name = target_object_name.replace(r_from, r_to)
                        self.objects.append(SeedRecipeS3Object(
                            local_path=s3_object_path,
                            object_name=target_object_name,
                            target=target,
                        ))
            else:
                LOG.warning('S3 copy path is not a directory: %s', s3_copy.path)


class SeedRecipe:

    # pylint: disable-next=too-many-arguments
    def __init__(self, *, name: str, description: str, root: pathlib.Path,
                 db: SeedRecipeDB, s3: SeedRecipeS3,
                 uuids_count: int, uuids_placeholder: str | None,
                 init_wait: float):
        # pylint: disable-next=too-many-instance-attributes
        self.name = name
        self.description = description
        self.root = root
        self.db = db
        self.s3 = s3
        self.prepared = False
        self.uuids_count = uuids_count
        self.uuids_placeholder = uuids_placeholder
        self.uuids_replacement: dict[str, str] = {}
        self.init_wait = init_wait

    def _prepare_uuids(self):
        if self.uuids_placeholder is not None:
            for i in range(self.uuids_count):
                key = self.uuids_placeholder.replace('[n]', f'[{i}]')
                self.uuids_replacement[key] = str(uuid.uuid4())

    def prepare(self):
        if self.prepared:
            return
        self.db.load_db_scripts()
        self.s3.load_s3_object_names()
        self._prepare_uuids()
        self.prepared = True
        for s3_object in self.s3.objects:
            s3_object.update_object_name(self.uuids_replacement)

    def run_prepare(self):
        self._prepare_uuids()

    def _replace_db_script(self, script: str, tenant_uuid: str) -> str:
        result = script.replace(self.db.tenant_placeholder, tenant_uuid)
        for uuid_key, uuid_value in self.uuids_replacement.items():
            result = result.replace(uuid_key, uuid_value)
        return result

    def iterate_db_scripts(self, tenant_uuid: str):
        return (
            (script_id, self._replace_db_script(script, tenant_uuid))
            for script_id, script in self.db.scripts_data.items()
        )

    def iterate_s3_objects(self):
        return (obj for obj in self.s3.objects)

    def __str__(self):
        scripts = '\n'.join((f'- {x}' for x in self.db.scripts))
        copy_instructions = '\n'.join(f'- {x}' for x in self.s3.copy.values())
        replaces = '\n'.join(
            (f'- "{x}" -> "{y}"' for x, y in self.s3.filename_replace.items())
        )
        return f'Recipe: {self.name}\n' \
               f'Loaded from: {self.root}\n' \
               f'{self.description}\n\n' \
               f'DB SQL Scripts:\n' \
               f'{scripts}\n' \
               f'DB Tenant UUID Placeholder: "{self.db.tenant_placeholder}"\n\n' \
               f'S3 Directory:\n' \
               f'{copy_instructions}\n' \
               f'S3 Filename Replace:\n' \
               f'{replaces}'

    @staticmethod
    def load_from_json(recipe_file: pathlib.Path) -> 'SeedRecipe':
        data = json.loads(recipe_file.read_text(
            encoding=DEFAULT_ENCODING,
        ))
        db: dict[str, typing.Any] = data.get('db', {})
        s3: dict[str, typing.Any] = data.get('s3', {})
        root_dir = recipe_file.parent
        return SeedRecipe(
            name=data['name'],
            description=data.get('description', ''),
            root=root_dir,
            db=SeedRecipeDB.from_dict(db, root_dir),
            s3=SeedRecipeS3.from_dict(s3, root_dir),
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
            db=SeedRecipeDB(
                scripts={},
                tenant_placeholder=DEFAULT_PLACEHOLDER,
            ),
            s3=SeedRecipeS3(
                copy={},
                filename_replace={},
            ),
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
        self.s3s = {}  # type: dict[str, S3Storage]

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
            self.dbs[db_id] = Database(
                cfg=extra_db_cfg,
                with_queue=False,
            )
        for s3_id, extra_s3_cfg in Context.get().app.cfg.extra_s3s.items():
            self.s3s[s3_id] = S3Storage(
                cfg=extra_s3_cfg,
                multi_tenant=self.cfg.cloud.multi_tenant,
            )

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
                script = self.recipe.db.scripts[script_id]
                LOG.debug(' -> Executing script: %s [target: %s]',
                          script_id, script.target)
                if script.target is not None and script.target in self.dbs:
                    used_targets.add(script.target)
                    with self.dbs[script.target].conn_query.new_cursor(use_dict=True) as c:
                        c.execute(query=sql_script)
                else:
                    with app_ctx.db.conn_query.new_cursor(use_dict=True) as c:
                        c.execute(query=sql_script)

            phase = 'S3'
            LOG.info('Transferring S3 objects')
            for s3_object in self.recipe.iterate_s3_objects():
                LOG.debug(' -> Reading: %s', s3_object.local_path.as_posix())
                data = s3_object.local_path.read_bytes()
                LOG.debug(' -> Sending: %s [target: %s]',
                          s3_object.object_name, s3_object.target)
                if s3_object.target is not None and s3_object.target in self.s3s:
                    self.s3s[s3_object.target].store_object(
                        tenant_uuid=tenant_uuid,
                        object_name=s3_object.object_name,
                        content_type=_guess_mimetype(s3_object.local_path.name),
                        data=data,
                    )
                else:
                    app_ctx.s3.store_object(
                        tenant_uuid=tenant_uuid,
                        object_name=s3_object.object_name,
                        content_type=_guess_mimetype(s3_object.local_path.name),
                        data=data,
                    )
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
