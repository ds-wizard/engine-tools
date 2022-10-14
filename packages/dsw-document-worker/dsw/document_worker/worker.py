import datetime
import functools
import logging
import pathlib
import uuid

from typing import Optional

from dsw.command_queue import CommandWorker, CommandQueue
from dsw.database.database import Database,\
    DBDocument, DBAppConfig, DBAppLimits, PersistentCommand
from dsw.storage import S3Storage

from .config import DocumentWorkerConfig
from .sentry import SentryReporter
from .consts import DocumentState, NULL_UUID, Queries
from .context import Context
from .documents import DocumentFile, DocumentNameGiver
from .exceptions import create_job_exception, JobException
from .limits import LimitsEnforcer
from .logging import DocWorkerLogger, DocWorkerLogFilter
from .templates import TemplateRegistry
from .utils import timeout, JobTimeoutError,\
    PdfWaterMarker, byte_size_format


def handle_job_step(message):
    def decorator(func):
        @functools.wraps(func)
        def handled_step(job, *args, **kwargs):
            try:
                return func(job, *args, **kwargs)
            except JobTimeoutError as e:
                raise e  # re-raise (need to be cached by context manager)
            except Exception as e:
                job.log.debug('Handling exception', exc_info=True)
                raise create_job_exception(
                    job_id=job.doc_uuid,
                    message=message,
                    exc=e,
                )
        return handled_step
    return decorator


class Job:

    def __init__(self, command: PersistentCommand):
        self.ctx = Context.get()
        self.log = Context.logger
        self.template = None
        self.format = None
        self.app_uuid = command.app_uuid
        self.doc_uuid = command.body['uuid']
        self.doc_context = command.body
        self.doc = None  # type: Optional[DBDocument]
        self.final_file = None  # type: Optional[DocumentFile]
        self.app_config = None  # type: Optional[DBAppConfig]
        self.app_limits = None  # type: Optional[DBAppLimits]

    @handle_job_step('Failed to get document from DB')
    def get_document(self):
        SentryReporter.set_context('template', '')
        SentryReporter.set_context('format', '')
        SentryReporter.set_context('document', '')
        if self.app_uuid != NULL_UUID:
            self.log.info(f'Limiting to app with UUID: {self.app_uuid}')
        self.log.info(f'Getting the document "{self.doc_uuid}" details from DB')
        self.doc = self.ctx.app.db.fetch_document(
            document_uuid=self.doc_uuid,
            app_uuid=self.app_uuid,
        )
        if self.doc is None:
            raise create_job_exception(
                job_id=self.doc_uuid,
                message='Document record not found in database',
            )
        self.doc.retrieved_at = datetime.datetime.now()
        self.log.info(f'Job "{self.doc_uuid}" details received')
        # verify state
        state = self.doc.state
        self.log.info(f'Original state of job is {state}')
        if state == DocumentState.FINISHED:
            raise create_job_exception(
                job_id=self.doc_uuid,
                message='Document is already marked as finished',
            )
        self.ctx.app.db.update_document_retrieved(
            retrieved_at=self.doc.retrieved_at,
            document_uuid=self.doc_uuid,
        )

    @handle_job_step('Failed to prepare template')
    def prepare_template(self):
        template_id = self.doc.template_id
        format_uuid = self.doc.format_uuid
        self.log.info(f'Document uses template {template_id} with format {format_uuid}')
        # update Sentry info
        SentryReporter.set_context('template', template_id)
        SentryReporter.set_context('format', format_uuid)
        SentryReporter.set_context('document', self.doc_uuid)
        # prepare template
        self.template = TemplateRegistry.get().prepare_template(
            app_uuid=self.app_uuid,
            template_id=template_id,
        )
        # prepare format
        self.template.prepare_format(format_uuid)
        self.format = self.template.formats.get(format_uuid)
        # check limits (PDF-only)
        self.app_config = self.ctx.app.db.fetch_app_config(app_uuid=self.app_uuid)
        self.app_limits = self.ctx.app.db.fetch_app_limits(app_uuid=self.app_uuid)
        LimitsEnforcer.check_format(
            job_id=self.doc_uuid,
            doc_format=self.format,
            app_config=self.app_config,
        )

    @handle_job_step('Failed to build final document')
    def build_document(self):
        self.log.info('Building document by rendering template with context')
        self.final_file = self.template.render(
            format_uuid=self.doc.format_uuid,
            context=self.doc_context,
        )
        # Check limits
        LimitsEnforcer.check_doc_size(
            job_id=self.doc_uuid,
            doc_size=self.final_file.byte_size,
        )
        limit_size = None if self.app_limits is None else self.app_limits.storage
        used_size = self.ctx.app.db.get_currently_used_size(app_uuid=self.app_uuid)
        LimitsEnforcer.check_size_usage(
            job_id=self.doc_uuid,
            doc_size=self.final_file.byte_size,
            used_size=used_size,
            limit_size=limit_size,
        )
        # Watermark
        if self.format.is_pdf:
            self.final_file.content = LimitsEnforcer.make_watermark(
                doc_pdf=self.final_file.content,
                app_config=self.app_config,
            )

    @handle_job_step('Failed to store document in S3')
    def store_document(self):
        s3_id = self.ctx.app.s3.identification
        self.log.info(f'Preparing S3 bucket {s3_id}')
        self.ctx.app.s3.ensure_bucket()
        self.log.info(f'Storing document to S3 bucket {s3_id}')
        self.ctx.app.s3.store_document(
            app_uuid=self.app_uuid,
            file_name=self.doc_uuid,
            content_type=self.final_file.content_type,
            data=self.final_file.content,
        )
        self.log.info(f'Document {self.doc_uuid} stored in S3 bucket {s3_id}')

    @handle_job_step('Failed to finalize document generation')
    def finalize(self):
        file_name = DocumentNameGiver.name_document(self.doc, self.final_file)
        self.doc.finished_at = datetime.datetime.now()
        self.doc.file_name = file_name
        self.doc.content_type = self.final_file.content_type
        self.doc.file_size = self.final_file.byte_size
        self.ctx.app.db.update_document_finished(
            finished_at=self.doc.finished_at,
            file_name=self.doc.file_name,
            content_type=self.doc.content_type,
            file_size=self.doc.file_size,
            worker_log=(
                f'Document "{file_name}" generated successfully '
                f'({byte_size_format(self.doc.file_size)}).'
            ),
            document_uuid=self.doc_uuid,
        )
        self.log.info(f'Document {self.doc_uuid} record finalized')

    def set_job_state(self, state: str, message: str) -> bool:
        return self.ctx.app.db.update_document_state(
            document_uuid=self.doc_uuid,
            worker_log=message,
            state=state,
        )

    def try_set_job_state(self, state: str, message: str) -> bool:
        try:
            return self.set_job_state(state, message)
        except Exception as e:
            SentryReporter.capture_exception(e)
            self.log.warning(f'Tried to set state of {self.doc_uuid} to {state} but failed: {e}')
            return False

    def _run(self):
        self.get_document()
        try:
            with timeout(Context.get().app.cfg.experimental.job_timeout):
                self.prepare_template()
                self.build_document()
                self.store_document()
        except TimeoutError:
            LimitsEnforcer.timeout_exceeded(
                job_id=self.doc_uuid,
            )
        self.finalize()

    def run(self):
        try:
            self._run()
        except JobException as e:
            self.log.error(e.log_message())
            if self.try_set_job_state(DocumentState.FAILED, e.db_message()):
                self.log.info(f'Set state to {DocumentState.FAILED}')
            else:
                self.log.error(f'Could not set state to {DocumentState.FAILED}')
                raise RuntimeError(f'Could not set state to {DocumentState.FAILED}')
        except Exception as e:
            SentryReporter.capture_exception(e)
            job_exc = create_job_exception(
                job_id=self.doc_uuid,
                message='Failed with unexpected error',
                exc=e,
            )
            Context.logger.error(job_exc.log_message())
            if self.try_set_job_state(DocumentState.FAILED, job_exc.db_message()):
                self.log.info(f'Set state to {DocumentState.FAILED}')
            else:
                self.log.warning(f'Could not set state to {DocumentState.FAILED}')
                raise RuntimeError(f'Could not set state to {DocumentState.FAILED}')


class DocumentWorker(CommandWorker):

    def __init__(self, config: DocumentWorkerConfig, workdir: pathlib.Path):
        self.config = config
        self._prepare_logging()
        self._init_context(workdir=workdir)

    def _init_context(self, workdir: pathlib.Path):
        Context.initialize(
            config=self.config,
            workdir=workdir,
            db=Database(cfg=self.config.db),
            s3=S3Storage(
                cfg=self.config.s3,
                multi_tenant=self.config.cloud.multi_tenant,
            ),
        )
        PdfWaterMarker.initialize(
            watermark_filename=self.config.experimental.pdf_watermark,
            watermark_top=self.config.experimental.pdf_watermark_top,
        )
        if self.config.sentry.enabled and self.config.sentry.workers_dsn is not None:
            SentryReporter.initialize(
                dsn=self.config.sentry.workers_dsn,
                environment=self.config.general.environment,
                server_name=self.config.general.client_url,
            )

    def _prepare_logging(self):
        Context.logger.set_level(self.config.log.level)
        log_filter = DocWorkerLogFilter()
        logging.getLogger().addFilter(filter=log_filter)
        loggers = (logging.getLogger(n)
                   for n in logging.root.manager.loggerDict.keys())
        for logger in loggers:
            logger.addFilter(filter=log_filter)
        logging.setLoggerClass(DocWorkerLogger)

    def run(self):
        Context.get().app.db.connect()
        Context.logger.info('Preparing command queue')
        queue = CommandQueue(
            worker=self,
            db=Context.get().app.db,
            listen_query=Queries.LISTEN,
        )
        queue.run()

    def work(self) -> bool:
        Context.update_trace_id(str(uuid.uuid4()))
        ctx = Context.get()
        Context.logger.debug('Trying to fetch a new job')
        cursor = ctx.app.db.conn_query.new_cursor(use_dict=True)
        cursor.execute(Queries.SELECT_CMD, {'now': datetime.datetime.utcnow()})
        result = cursor.fetchall()
        if len(result) != 1:
            Context.logger.debug(f'Fetched {len(result)} jobs')
            return False

        command = PersistentCommand.from_dict_row(result[0])
        try:
            self._process_command(command)
        except Exception as e:
            Context.logger.warning(f'Errored with exception: {str(e)} ({type(e).__name__})')
            SentryReporter.capture_exception(e)
            ctx.app.db.execute_query(
                query=Queries.UPDATE_CMD_ERROR,
                attempts=command.attempts + 1,
                error_message=f'Failed with exception: {str(e)} ({type(e).__name__})',
                updated_at=datetime.datetime.utcnow(),
                uuid=command.uuid,
            )

        Context.logger.info('Committing transaction')
        ctx.app.db.conn_query.connection.commit()
        cursor.close()

        Context.logger.info('Job processing finished')
        Context.update_trace_id('-')
        return True

    def _process_command(self, command: PersistentCommand):
        app_ctx = Context.get().app
        Context.update_document_id(command.body['uuid'])
        Context.logger.info(f'Fetched job #{command.uuid}')
        job = Job(command=command)
        job.run()
        app_ctx.db.execute_query(
            query=Queries.UPDATE_CMD_DONE,
            attempts=command.attempts + 1,
            updated_at=datetime.datetime.utcnow(),
            uuid=command.uuid,
        )
