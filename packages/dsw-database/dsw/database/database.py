import datetime
import logging
import psycopg
import psycopg.rows
import psycopg.types.json
import tenacity

from typing import List, Iterable, Optional

from dsw.config.model import DatabaseConfig

from .model import DBDocumentTemplate, DBDocumentTemplateFile, \
    DBDocumentTemplateAsset, DBDocument, DBComponent, \
    DocumentState, DBTenantConfig, DBTenantLimits, DBSubmission, \
    DBInstanceConfigMail, DBQuestionnaireSimple

LOG = logging.getLogger(__name__)

RETRY_QUERY_MULTIPLIER = 0.5
RETRY_QUERY_TRIES = 3

RETRY_CONNECT_MULTIPLIER = 0.2
RETRY_CONNECT_TRIES = 10


def wrap_json_data(data: dict):
    return psycopg.types.json.Json(data)


class Database:

    # TODO: refactor queries and models
    SELECT_DOCUMENT = 'SELECT * FROM document WHERE uuid = %s AND tenant_uuid = %s LIMIT 1;'
    SELECT_QTN_DOCUMENTS = 'SELECT * FROM document WHERE questionnaire_uuid = %s AND tenant_uuid = %s;'
    SELECT_DOCUMENT_SUBMISSIONS = 'SELECT * FROM submission WHERE document_uuid = %s AND tenant_uuid = %s;'
    SELECT_QTN_SUBMISSIONS = 'SELECT s.* FROM document d JOIN submission s ON d.uuid = s.document_uuid ' \
                             'WHERE d.questionnaire_uuid = %s AND d.tenant_uuid = %s;'
    SELECT_QTN_SIMPLE = 'SELECT qtn.* FROM questionnaire qtn ' \
                        'WHERE qtn.uuid = %s AND qtn.tenant_uuid = %s;'
    SELECT_TENANT_CONFIG = 'SELECT * FROM tenant_config WHERE uuid = %(tenant_uuid)s LIMIT 1;'
    SELECT_TENANT_LIMIT = 'SELECT uuid, storage FROM tenant_limit_bundle WHERE uuid = %(tenant_uuid)s LIMIT 1;'
    UPDATE_DOCUMENT_STATE = 'UPDATE document SET state = %s, worker_log = %s WHERE uuid = %s;'
    UPDATE_DOCUMENT_RETRIEVED = 'UPDATE document SET retrieved_at = %s, state = %s WHERE uuid = %s;'
    UPDATE_DOCUMENT_FINISHED = 'UPDATE document SET finished_at = %s, state = %s, ' \
                               'file_name = %s, content_type = %s, worker_log = %s, ' \
                               'file_size = %s WHERE uuid = %s;'
    SELECT_TEMPLATE = 'SELECT * FROM document_template WHERE id = %s AND tenant_uuid = %s LIMIT 1;'
    SELECT_TEMPLATE_FILES = 'SELECT * FROM document_template_file ' \
                            'WHERE document_template_id = %s AND tenant_uuid = %s;'
    SELECT_TEMPLATE_ASSETS = 'SELECT * FROM document_template_asset ' \
                             'WHERE document_template_id = %s AND tenant_uuid = %s;'
    CHECK_TABLE_EXISTS = 'SELECT EXISTS(SELECT * FROM information_schema.tables' \
                         '                       WHERE table_name = %(table_name)s)'
    SELECT_MAIL_CONFIG = 'SELECT icm.* ' \
                         'FROM tenant_config tc JOIN instance_config_mail icm ' \
                         'ON tc.mail_config_uuid = icm.uuid ' \
                         'WHERE tc.uuid = %(tenant_uuid)s;'
    UPDATE_COMPONENT_INFO = 'INSERT INTO component (name, version, built_at, created_at, updated_at) ' \
                            'VALUES (%(name)s, %(version)s, %(built_at)s, %(created_at)s, %(updated_at)s)' \
                            'ON CONFLICT (name) DO ' \
                            'UPDATE SET version = %(version)s, built_at = %(built_at)s, updated_at = %(updated_at)s;'
    SELECT_COMPONENT_INFO = 'SELECT * FROM component WHERE name = %(name)s;'
    SUM_FILE_SIZES = 'SELECT (SELECT COALESCE(SUM(file_size)::bigint, 0) ' \
                     'FROM document WHERE tenant_uuid = %(tenant_uuid)s) ' \
                     '+ (SELECT COALESCE(SUM(file_size)::bigint, 0) ' \
                     'FROM document_template_asset WHERE tenant_uuid = %(tenant_uuid)s) ' \
                     'as result;'

    def __init__(self, cfg: DatabaseConfig, connect: bool = True,
                 with_queue: bool = True):
        self.cfg = cfg
        LOG.info('Preparing PostgreSQL connection for QUERY')
        self.conn_query = PostgresConnection(
            name='query',
            dsn=self.cfg.connection_string,
            timeout=self.cfg.connection_timeout,
            autocommit=False,
        )
        if connect:
            self.conn_query.connect()
        self.with_queue = with_queue
        if with_queue:
            LOG.info('Preparing PostgreSQL connection for QUEUE')
            self.conn_queue = PostgresConnection(
                name='queue',
                dsn=self.cfg.connection_string,
                timeout=self.cfg.connection_timeout,
                autocommit=True,
            )
            if connect:
                self.conn_queue.connect()

    def connect(self):
        self.conn_query.connect()
        if self.with_queue:
            self.conn_queue.connect()

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def _check_table_exists(self, table_name: str) -> bool:
        with self.conn_query.new_cursor() as cursor:
            try:
                cursor.execute(
                    query=self.CHECK_TABLE_EXISTS,
                    params={'table_name': table_name},
                )
                return cursor.fetchone()[0]
            except Exception:
                return False

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_document(self, document_uuid: str, tenant_uuid: str) -> Optional[DBDocument]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_DOCUMENT,
                params=(document_uuid, tenant_uuid),
            )
            result = cursor.fetchall()
            if len(result) != 1:
                return None
            return DBDocument.from_dict_row(result[0])

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_tenant_config(self, tenant_uuid: str) -> Optional[DBTenantConfig]:
        return self.get_tenant_config(tenant_uuid)

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_tenant_limits(self, tenant_uuid: str) -> Optional[DBTenantLimits]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_TENANT_LIMIT,
                params={'tenant_uuid': tenant_uuid},
            )
            result = cursor.fetchall()
            if len(result) != 1:
                return None
            return DBTenantLimits.from_dict_row(result[0])

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_template(
            self, template_id: str, tenant_uuid: str
    ) -> Optional[DBDocumentTemplate]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_TEMPLATE,
                params=(template_id, tenant_uuid),
            )
            result = cursor.fetchall()
            if len(result) != 1:
                return None
            return DBDocumentTemplate.from_dict_row(result[0])

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_template_files(
            self, template_id: str, tenant_uuid: str
    ) -> List[DBDocumentTemplateFile]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_TEMPLATE_FILES,
                params=(template_id, tenant_uuid),
            )
            return [DBDocumentTemplateFile.from_dict_row(x) for x in cursor.fetchall()]

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_template_assets(
            self, template_id: str, tenant_uuid: str
    ) -> List[DBDocumentTemplateAsset]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_TEMPLATE_ASSETS,
                params=(template_id, tenant_uuid),
            )
            return [DBDocumentTemplateAsset.from_dict_row(x) for x in cursor.fetchall()]

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_qtn_documents(self, questionnaire_uuid: str, tenant_uuid: str) -> List[DBDocument]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_QTN_DOCUMENTS,
                params=(questionnaire_uuid, tenant_uuid),
            )
            return [DBDocument.from_dict_row(x) for x in cursor.fetchall()]

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_document_submissions(self, document_uuid: str, tenant_uuid: str) -> List[DBSubmission]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_DOCUMENT_SUBMISSIONS,
                params=(document_uuid, tenant_uuid),
            )
            return [DBSubmission.from_dict_row(x) for x in cursor.fetchall()]

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_questionnaire_submissions(self, questionnaire_uuid: str, tenant_uuid: str) -> List[DBSubmission]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_QTN_SUBMISSIONS,
                params=(questionnaire_uuid, tenant_uuid),
            )
            return [DBSubmission.from_dict_row(x) for x in cursor.fetchall()]

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def fetch_questionnaire_simple(self, questionnaire_uuid: str, tenant_uuid: str) -> DBQuestionnaireSimple:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            cursor.execute(
                query=self.SELECT_QTN_SIMPLE,
                params=(questionnaire_uuid, tenant_uuid),
            )
            return DBQuestionnaireSimple.from_dict_row(cursor.fetchone())

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
                params=(state, worker_log, document_uuid),
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
        with self.conn_query.new_cursor() as cursor:
            cursor.execute(
                query=self.UPDATE_DOCUMENT_RETRIEVED,
                params=(
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
                params=(
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
    def get_currently_used_size(self, tenant_uuid: str):
        with self.conn_query.new_cursor() as cursor:
            cursor.execute(
                query=self.SUM_FILE_SIZES,
                params={'tenant_uuid': tenant_uuid},
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
    def get_tenant_config(self, tenant_uuid: str) -> Optional[DBTenantConfig]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            try:
                cursor.execute(
                    query=self.SELECT_TENANT_CONFIG,
                    params={'tenant_uuid': tenant_uuid},
                )
                result = cursor.fetchone()
                return DBTenantConfig.from_dict_row(data=result)
            except Exception as e:
                LOG.warning(f'Could not retrieve tenant_config for tenant'
                            f' "{tenant_uuid}": {str(e)}')
                return None

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def get_mail_config(self, tenant_uuid: str) -> Optional[DBInstanceConfigMail]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            if not self._check_table_exists(table_name='instance_config_mail'):
                return None
            try:
                cursor.execute(
                    query=self.SELECT_MAIL_CONFIG,
                    params={'tenant_uuid': tenant_uuid},
                )
                result = cursor.fetchone()
                if result is None:
                    return None
                return DBInstanceConfigMail.from_dict_row(data=result)
            except Exception as e:
                LOG.warning(f'Could not retrieve instance_config_mail for tenant'
                            f' "{tenant_uuid}": {str(e)}')
                return None

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def update_component_info(self, name: str, version: str, built_at: datetime.datetime):
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            if not self._check_table_exists(table_name='component'):
                return None
            ts_now = datetime.datetime.utcnow()
            try:
                cursor.execute(
                    query=self.UPDATE_COMPONENT_INFO,
                    params={
                        'name': name,
                        'version': version,
                        'built_at': built_at,
                        'created_at': ts_now,
                        'updated_at': ts_now,
                    },
                )
                self.conn_query.connection.commit()
            except Exception as e:
                LOG.warning(f'Could not update component info: {str(e)}')

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_QUERY_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_QUERY_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def get_component_info(self, name: str) -> Optional[DBComponent]:
        with self.conn_query.new_cursor(use_dict=True) as cursor:
            try:
                cursor.execute(
                    query=self.SELECT_COMPONENT_INFO,
                    params={'name': name},
                )
                result = cursor.fetchone()
                if result is None:
                    return None
                return DBComponent.from_dict_row(data=result)
            except Exception as e:
                LOG.warning(f'Could not get component info: {str(e)}')
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
            cursor.execute(query=query, params=kwargs)


class PostgresConnection:

    def __init__(self, name: str, dsn: str, timeout=30000, autocommit=False):
        self.name = name
        self.listening = False
        self.dsn = psycopg.conninfo.make_conninfo(
            conninfo=dsn,
            connect_timeout=timeout,
        )
        self.autocommit = autocommit
        self._connection = None  # type: Optional[psycopg.Connection]

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_CONNECT_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_CONNECT_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def _connect_db(self):
        LOG.info(f'Creating connection to PostgreSQL database "{self.name}"')
        connection = psycopg.connect(conninfo=self.dsn, autocommit=self.autocommit)
        if connection is None:
            raise RuntimeError('Failed to init DB connection')
        # test connection
        cursor = connection.cursor()
        cursor.execute(query='SELECT 1;')
        result = cursor.fetchone()
        if result is None:
            raise RuntimeError('Failed to verify DB connection')
        LOG.debug(f'DB connection verified (result={result[0]})')
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
            row_factory=psycopg.rows.dict_row if use_dict else psycopg.rows.tuple_row,
        )

    def reset(self):
        self.close()
        self.connect()

    def close(self):
        if self._connection:
            LOG.info(f'Closing connection to PostgreSQL database "{self.name}"')
            self._connection.close()
        self._connection = None
