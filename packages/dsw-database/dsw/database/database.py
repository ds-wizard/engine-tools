import dataclasses
import datetime
import json
import logging
import psycopg2  # type: ignore
import psycopg2.extensions  # type: ignore
import psycopg2.extras  # type: ignore
import tenacity

from typing import List, Optional, Iterable

from dsw.config.model import DatabaseConfig

LOG = logging.getLogger(__name__)

NULL_UUID = '00000000-0000-0000-0000-000000000000'

ISOLATION_DEFAULT = psycopg2.extensions.ISOLATION_LEVEL_DEFAULT
ISOLATION_AUTOCOMMIT = psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT

RETRY_QUERY_MULTIPLIER = 0.5
RETRY_QUERY_TRIES = 3

RETRY_CONNECT_MULTIPLIER = 0.2
RETRY_CONNECT_TRIES = 10


class DocumentState:
    QUEUED = 'QueuedDocumentState'
    PROCESSING = 'InProgressDocumentState'
    FAILED = 'ErrorDocumentState'
    FINISHED = 'DoneDocumentState'


@dataclasses.dataclass
class DBDocument:
    uuid: str
    name: str
    state: str
    durability: str
    questionnaire_uuid: str
    questionnaire_event_uuid: str
    questionnaire_replies_hash: str
    template_id: str
    format_uuid: str
    file_name: str
    content_type: str
    worker_log: str
    creator_uuid: str
    retrieved_at: Optional[datetime.datetime]
    finished_at: Optional[datetime.datetime]
    created_at: datetime.datetime
    app_uuid: str
    file_size: int


@dataclasses.dataclass
class DBTemplate:
    id: str
    name: str
    organization_id: str
    template_id: str
    version: str
    metamodel_version: int
    description: str
    readme: str
    license: str
    allowed_packages: dict
    recommended_package_id: str
    formats: dict
    created_at: datetime.datetime
    app_uuid: str


@dataclasses.dataclass
class DBTemplateFile:
    template_id: str
    uuid: str
    file_name: str
    content: str
    app_uuid: str


@dataclasses.dataclass
class DBTemplateAsset:
    template_id: str
    uuid: str
    file_name: str
    content_type: str
    app_uuid: str
    file_size: int


@dataclasses.dataclass
class PersistentCommand:
    uuid: str
    state: str
    component: str
    function: str
    body: dict
    last_error_message: Optional[str]
    attempts: int
    max_attempts: int
    app_uuid: str
    created_by: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @staticmethod
    def deserialize(data: dict):
        return PersistentCommand(
            uuid=data['uuid'],
            state=data['state'],
            component=data['component'],
            function=data['function'],
            body=json.loads(data['body']),
            last_error_message=data['last_error_message'],
            attempts=data['attempts'],
            max_attempts=data['max_attempts'],
            created_by=data['created_by'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            app_uuid=data.get('app_uuid', NULL_UUID),
        )


@dataclasses.dataclass
class DBAppConfig:
    uuid: str
    look_and_feel: dict
    privacy_and_support: dict
    feature: dict
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @property
    def feature_pdf_only(self) -> bool:
        return self.feature.get('pdfOnlyEnabled', False)

    @property
    def feature_pdf_watermark(self) -> bool:
        return self.feature.get('pdfWatermarkEnabled', False)

    @property
    def app_title(self) -> Optional[str]:
        return self.look_and_feel.get('appTitle', None)

    @property
    def support_email(self) -> Optional[str]:
        return self.privacy_and_support.get('supportEmail', None)

    @staticmethod
    def deserialize(data: dict):
        return DBAppConfig(
            uuid=data['uuid'],
            look_and_feel=data['look_and_feel'],
            privacy_and_support=data['privacy_and_support'],
            feature=data['feature'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
        )


@dataclasses.dataclass
class DBAppLimits:
    app_uuid: str
    storage: Optional[int]


def wrap_json_data(data: dict):
    return psycopg2.extras.Json(data)


class Database:

    SELECT_DOCUMENT = 'SELECT * FROM document WHERE uuid = %s AND app_uuid = %s LIMIT 1;'
    SELECT_APP_CONFIG = 'SELECT * FROM app_config WHERE uuid = %(app_uuid)s LIMIT 1;'
    SELECT_APP_LIMIT = 'SELECT uuid, storage FROM app_limit WHERE uuid = %(app_uuid)s LIMIT 1;'
    UPDATE_DOCUMENT_STATE = 'UPDATE document SET state = %s, worker_log = %s WHERE uuid = %s;'
    UPDATE_DOCUMENT_RETRIEVED = 'UPDATE document SET retrieved_at = %s, state = %s WHERE uuid = %s;'
    UPDATE_DOCUMENT_FINISHED = 'UPDATE document SET finished_at = %s, state = %s, ' \
                               'file_name = %s, content_type = %s, worker_log = %s, ' \
                               'file_size = %s WHERE uuid = %s;'
    SELECT_TEMPLATE = 'SELECT * FROM template WHERE id = %s AND app_uuid = %s LIMIT 1;'
    SELECT_TEMPLATE_FILES = 'SELECT * FROM template_file WHERE template_id = %s AND app_uuid = %s;'
    SELECT_TEMPLATE_ASSETS = 'SELECT * FROM template_asset WHERE template_id = %s AND app_uuid = %s;'

    SUM_FILE_SIZES = 'SELECT (SELECT COALESCE(SUM(file_size)::bigint, 0) ' \
                     'FROM document WHERE app_uuid = %(app_uuid)s) ' \
                     '+ (SELECT COALESCE(SUM(file_size)::bigint, 0) ' \
                     'FROM template_asset WHERE app_uuid = %(app_uuid)s) ' \
                     'as result;'

    def __init__(self, cfg: DatabaseConfig):
        self.cfg = cfg
        LOG.info('Preparing PostgreSQL connection for QUERY')
        self.conn_query = PostgresConnection(
            name='query',
            dsn=self.cfg.connection_string,
            timeout=self.cfg.connection_timeout,
            autocommit=False,
        )
        self.conn_query.connect()
        LOG.info('Preparing PostgreSQL connection for QUEUE')
        self.conn_queue = PostgresConnection(
            name='queue',
            dsn=self.cfg.connection_string,
            timeout=self.cfg.connection_timeout,
            autocommit=True,
        )
        self.conn_queue.connect()

    def connect(self):
        self.conn_query.connect()
        self.conn_queue.connect()

    @staticmethod
    def get_as_app_limits(result: dict) -> DBAppLimits:
        return DBAppLimits(
            app_uuid=result['uuid'],
            storage=result['storage'],
        )

    @staticmethod
    def get_as_document(result: dict) -> DBDocument:
        return DBDocument(
            uuid=result['uuid'],
            name=result['name'],
            state=result['state'],
            durability=result['durability'],
            questionnaire_uuid=result['questionnaire_uuid'],
            questionnaire_event_uuid=result['questionnaire_event_uuid'],
            questionnaire_replies_hash=result['questionnaire_replies_hash'],
            template_id=result['template_id'],
            format_uuid=result['format_uuid'],
            creator_uuid=result['creator_uuid'],
            retrieved_at=result['retrieved_at'],
            finished_at=result['finished_at'],
            created_at=result['created_at'],
            file_name=result['file_name'],
            content_type=result['content_type'],
            worker_log=result['worker_log'],
            app_uuid=result.get('app_uuid', NULL_UUID),
            file_size=result['file_size'],
        )

    @staticmethod
    def get_as_template(result: dict) -> DBTemplate:
        return DBTemplate(
            id=result['id'],
            name=result['name'],
            organization_id=result['organization_id'],
            template_id=result['template_id'],
            version=result['version'],
            metamodel_version=result['metamodel_version'],
            description=result['description'],
            readme=result['readme'],
            license=result['license'],
            allowed_packages=result['allowed_packages'],
            recommended_package_id=result['recommended_package_id'],
            formats=result['formats'],
            created_at=result['created_at'],
            app_uuid=result.get('app_uuid', NULL_UUID),
        )

    @staticmethod
    def get_as_template_file(result: dict) -> DBTemplateFile:
        return DBTemplateFile(
            template_id=result['template_id'],
            uuid=result['uuid'],
            file_name=result['file_name'],
            content=result['content'],
            app_uuid=result.get('app_uuid', NULL_UUID),
        )

    @staticmethod
    def get_as_template_asset(result: dict) -> DBTemplateAsset:
        return DBTemplateAsset(
            template_id=result['template_id'],
            uuid=result['uuid'],
            file_name=result['file_name'],
            content_type=result['content_type'],
            app_uuid=result.get('app_uuid', NULL_UUID),
            file_size=result['file_size'],
        )

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_document(self, document_uuid: str, app_uuid: str) -> Optional[DBDocument]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_DOCUMENT,
                vars=(document_uuid, app_uuid),
            )
            result = cursor.fetchall()
            if len(result) != 1:
                return None
            return self.get_as_document(result[0])

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_app_config(self, app_uuid: str) -> Optional[DBAppConfig]:
        return self.get_app_config(app_uuid)

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_app_limits(self, app_uuid: str) -> Optional[DBAppLimits]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_APP_LIMIT,
                vars={'app_uuid': app_uuid},
            )
            result = cursor.fetchall()
            if len(result) != 1:
                return None
            return self.get_as_app_limits(result[0])

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_template(self, template_id: str, app_uuid: str) -> Optional[DBTemplate]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_TEMPLATE,
                vars=(template_id, app_uuid),
            )
            result = cursor.fetchall()
            if len(result) != 1:
                return None
            return self.get_as_template(result[0])

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_template_files(self, template_id: str, app_uuid: str) -> List[DBTemplateFile]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_TEMPLATE_FILES,
                vars=(template_id, app_uuid),
            )
            return [self.get_as_template_file(x) for x in cursor.fetchall()]

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_template_assets(self, template_id: str, app_uuid: str) -> List[DBTemplateAsset]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_TEMPLATE_ASSETS,
                vars=(template_id, app_uuid),
            )
            return [self.get_as_template_asset(x) for x in cursor.fetchall()]

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def update_document_state(self, document_uuid: str, worker_log: str, state: str) -> bool:
        with self.conn_query.new_cursor() as cursor:
            cursor.execute(
                query=self.UPDATE_DOCUMENT_STATE,
                vars=(state, worker_log, document_uuid),
            )
            return cursor.rowcount == 1

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def update_document_retrieved(self, retrieved_at: datetime.datetime,
                                  document_uuid: str) -> bool:
        with self.conn_queue.new_cursor() as cursor:
            cursor.execute(
                query=self.UPDATE_DOCUMENT_RETRIEVED,
                vars=(
                    retrieved_at,
                    DocumentState.PROCESSING,
                    document_uuid,
                ),
            )
            return cursor.rowcount == 1

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def update_document_finished(
            self, finished_at: datetime.datetime, file_name: str, file_size: int,
            content_type: str,  worker_log: str, document_uuid: str
    ) -> bool:
        with self.conn_query.new_cursor() as cursor:
            cursor.execute(
                query=self.UPDATE_DOCUMENT_FINISHED,
                vars=(
                    finished_at,
                    DocumentState.FINISHED,
                    file_name,
                    content_type,
                    worker_log,
                    file_size,
                    document_uuid,
                ),
            )
            return cursor.rowcount == 1

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def get_currently_used_size(self, app_uuid: str):
        with self.conn_query.new_cursor() as cursor:
            cursor.execute(
                query=self.SUM_FILE_SIZES,
                vars={'app_uuid': app_uuid},
            )
            row = cursor.fetchone()
            return row[0]

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def get_app_config(self, app_uuid: str) -> Optional[DBAppConfig]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            try:
                cursor.execute(
                    query=self.SELECT_APP_CONFIG,
                    vars={'app_uuid': app_uuid},
                )
                result = cursor.fetchone()
                return DBAppConfig.deserialize(data=result)
            except Exception as e:
                LOG.warning(f'Could not retrieve app_config for app'
                            f' "{app_uuid}": {str(e)}')
                return None

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def execute_queries(self, queries: Iterable[str]):
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            for query in queries:
                cursor.execute(query=query)

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def execute_query(self, query: str, **kwargs):
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(query=query, vars=kwargs)


class PostgresConnection:

    def __init__(self, name: str, dsn: str, timeout=30000, autocommit=False):
        self.name = name
        self.listening = False
        self.dsn = psycopg2.extensions.make_dsn(dsn, connect_timeout=timeout)
        self.isolation = ISOLATION_AUTOCOMMIT if autocommit else ISOLATION_DEFAULT
        self._connection = None

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_CONNECT_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_CONNECT_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def _connect_db(self):
        LOG.info(f'Creating connection to PostgreSQL database "{self.name}"')
        connection = psycopg2.connect(dsn=self.dsn)
        connection.set_isolation_level(self.isolation)
        # test connection
        cursor = connection.cursor()
        cursor.execute(query='SELECT * FROM persistent_command;')
        result = cursor.fetchall()
        LOG.debug(f'Jobs in queue: {result}')
        cursor.close()
        connection.commit()
        self._connection = connection
        self.listening = False

    def connect(self):
        if not self._connection or self._connection.closed != 0:
            self._connect_db()

    @property
    def connection(self):
        self.connect()
        return self._connection

    def new_cursor(self, use_dict: bool = False):
        return self.connection.cursor(
            cursor_factory=psycopg2.extras.DictCursor if use_dict else None,
        )

    def reset(self):
        self.close()
        self.connect()

    def close(self):
        if self._connection:
            LOG.info(f'Closing connection to PostgreSQL database "{self.name}"')
            self._connection.close()
        self._connection = None
