import datetime
import dateutil.parser
import functools
import logging
import pathlib

from typing import Optional

from dsw.command_queue import CommandWorker, CommandQueue
from dsw.config.sentry import SentryReporter
from dsw.database.database import Database
from dsw.database.model import DBDocument, DBTenantConfig, \
    DBTenantLimits, PersistentCommand
from dsw.storage import S3Storage

from .build_info import BUILD_INFO
from .config import DocumentWorkerConfig
from .consts import DocumentState, COMPONENT_NAME, NULL_UUID, \
    CMD_COMPONENT, CMD_CHANNEL, PROG_NAME
from .context import Context
from .documents import DocumentFile, DocumentNameGiver
from .exceptions import create_job_exception, JobException
from .limits import LimitsEnforcer
from .templates import TemplateRegistry, Template, Format
from .utils import timeout, JobTimeoutError,\
    PdfWaterMarker, byte_size_format


LOG = logging.getLogger(__name__)


def handle_job_step(message):
    def decorator(func):
        @functools.wraps(func)
        def handled_step(job, *args, **kwargs):
            try:
                return func(job, *args, **kwargs)
            except JobTimeoutError as e:
                raise e  # re-raise (need to be cached by context manager)
            except Exception as e:
                LOG.debug('Handling exception', exc_info=True)
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
        self.template = None  # type: Optional[Template]
        self.format = None  # type: Optional[Format]
        self.tenant_uuid = command.tenant_uuid  # type: str
        self.doc_uuid = command.body['uuid']  # type: str
        self.doc_context = command.body  # type: dict
        self.doc = None  # type: Optional[DBDocument]
        self.final_file = None  # type: Optional[DocumentFile]
        self.tenant_config = None  # type: Optional[DBTenantConfig]
        self.tenant_limits = None  # type: Optional[DBTenantLimits]

    @property
    def safe_doc(self) -> DBDocument:
        if self.doc is None:
            raise RuntimeError('Document is not set but it should')
        return self.doc

    @property
    def safe_final_file(self) -> DocumentFile:
        if self.final_file is None:
            raise RuntimeError('Final file is not set but it should')
        return self.final_file

    @property
    def safe_template(self) -> Template:
        if self.template is None:
            raise RuntimeError('Template is not set but it should')
        return self.template

    @property
    def safe_format(self) -> Format:
        if self.format is None:
            raise RuntimeError('Format is not set but it should')
        return self.format

    @handle_job_step('Failed to get document from DB')
    def get_document(self):
        SentryReporter.set_context('template', '')
        SentryReporter.set_context('format', '')
        SentryReporter.set_context('document', '')
        if self.tenant_uuid != NULL_UUID:
            LOG.info(f'Limiting to tenant with UUID: {self.tenant_uuid}')
        LOG.info(f'Getting the document "{self.doc_uuid}" details from DB')
        self.doc = self.ctx.app.db.fetch_document(
            document_uuid=self.doc_uuid,
            tenant_uuid=self.tenant_uuid,
        )
        if self.doc is None:
            raise create_job_exception(
                job_id=self.doc_uuid,
                message='Document record not found in database',
            )
        self.doc.retrieved_at = datetime.datetime.now()
        LOG.info(f'Job "{self.doc_uuid}" details received')
        # verify state
        state = self.doc.state
        LOG.info(f'Original state of job is {state}')
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
        template_id = self.safe_doc.document_template_id
        format_uuid = self.safe_doc.format_uuid
        LOG.info(f'Document uses template {template_id} with format {format_uuid}')
        # update Sentry info
        SentryReporter.set_context('template', template_id)
        SentryReporter.set_context('format', format_uuid)
        SentryReporter.set_context('document', self.doc_uuid)
        # prepare template
        template = TemplateRegistry.get().prepare_template(
            tenant_uuid=self.tenant_uuid,
            template_id=template_id,
        )
        # prepare format
        template.prepare_format(format_uuid)
        self.format = template.formats.get(format_uuid)
        # check limits (PDF-only)
        self.tenant_config = self.ctx.app.db.fetch_tenant_config(tenant_uuid=self.tenant_uuid)
        self.tenant_limits = self.ctx.app.db.fetch_tenant_limits(tenant_uuid=self.tenant_uuid)
        LimitsEnforcer.check_format(
            job_id=self.doc_uuid,
            doc_format=self.safe_format,
            tenant_config=self.tenant_config,
        )
        # finalize
        self.template = template

    def _enrich_context(self):
        extras = dict()
        if self.safe_format.requires_via_extras('submissions'):
            submissions = self.ctx.app.db.fetch_questionnaire_submissions(
                questionnaire_uuid=self.safe_doc.questionnaire_uuid,
                tenant_uuid=self.tenant_uuid,
            )
            extras['submissions'] = [s.to_dict() for s in submissions]
        if self.safe_format.requires_via_extras('questionnaire'):
            questionnaire = self.ctx.app.db.fetch_questionnaire_simple(
                questionnaire_uuid=self.safe_doc.questionnaire_uuid,
                tenant_uuid=self.tenant_uuid,
            )
            extras['questionnaire'] = questionnaire.to_dict()
        self.doc_context['extras'] = extras

    @handle_job_step('Failed to build final document')
    def build_document(self):
        LOG.info('Building document by rendering template with context')
        doc = self.safe_doc
        # enrich context
        self._enrich_context()
        # render document
        final_file = self.safe_template.render(
            format_uuid=doc.format_uuid,
            context=self.doc_context,
        )
        # check limits
        LimitsEnforcer.check_doc_size(
            job_id=self.doc_uuid,
            doc_size=final_file.byte_size,
        )
        limit_size = None if self.tenant_limits is None else self.tenant_limits.storage
        used_size = self.ctx.app.db.get_currently_used_size(tenant_uuid=self.tenant_uuid)
        LimitsEnforcer.check_size_usage(
            job_id=self.doc_uuid,
            doc_size=final_file.byte_size,
            used_size=used_size,
            limit_size=limit_size,
        )
        # watermark
        if self.safe_format.is_pdf:
            final_file.content = LimitsEnforcer.make_watermark(
                doc_pdf=final_file.content,
                tenant_config=self.tenant_config,
            )
        # finalize
        self.final_file = final_file

    @handle_job_step('Failed to store document in S3')
    def store_document(self):
        s3_id = self.ctx.app.s3.identification
        final_file = self.safe_final_file
        LOG.info(f'Preparing S3 bucket {s3_id}')
        self.ctx.app.s3.ensure_bucket()
        LOG.info(f'Storing document to S3 bucket {s3_id}')
        self.ctx.app.s3.store_document(
            tenant_uuid=self.tenant_uuid,
            file_name=self.doc_uuid,
            content_type=final_file.object_content_type,
            data=final_file.content,
        )
        LOG.info(f'Document {self.doc_uuid} stored in S3 bucket {s3_id}')

    @handle_job_step('Failed to finalize document generation')
    def finalize(self):
        doc = self.safe_doc
        final_file = self.safe_final_file
        file_name = DocumentNameGiver.name_document(doc, final_file)
        doc.finished_at = datetime.datetime.now()
        doc.file_name = file_name
        doc.content_type = final_file.content_type
        doc.file_size = final_file.byte_size
        self.ctx.app.db.update_document_finished(
            finished_at=doc.finished_at,
            file_name=doc.file_name,
            content_type=doc.content_type,
            file_size=doc.file_size,
            worker_log=(
                f'Document "{file_name}" generated successfully '
                f'({byte_size_format(doc.file_size)}).'
            ),
            document_uuid=self.doc_uuid,
        )
        LOG.info(f'Document {self.doc_uuid} record finalized')

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
            LOG.warning(f'Tried to set state of {self.doc_uuid} to {state} but failed: {e}')
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

    def _sentry_job_exception(self) -> bool:
        if self.doc is None:
            return False
        template_id = self.safe_doc.document_template_id
        template_cfg = self.ctx.app.cfg.templates.get_config(template_id)
        if template_cfg is None:
            return False
        return template_cfg.send_sentry

    def run(self):
        try:
            self._run()
        except JobException as e:
            LOG.warning('Handled job error: %s', e.log_message())
            if self._sentry_job_exception():
                SentryReporter.capture_exception(e)
            if self.try_set_job_state(DocumentState.FAILED, e.db_message()):
                LOG.info(f'Set state to {DocumentState.FAILED}')
            else:
                LOG.error(f'Could not set state to {DocumentState.FAILED}')
                raise RuntimeError(f'Could not set state to {DocumentState.FAILED}')
        except Exception as e:
            SentryReporter.capture_exception(e)
            job_exc = create_job_exception(
                job_id=self.doc_uuid,
                message='Failed with unexpected error',
                exc=e,
            )
            LOG.error(job_exc.log_message())
            LOG.info('Failed with unexpected error', exc_info=e)
            if self.try_set_job_state(DocumentState.FAILED, job_exc.db_message()):
                LOG.info(f'Set state to {DocumentState.FAILED}')
            else:
                LOG.warning(f'Could not set state to {DocumentState.FAILED}')
                raise RuntimeError(f'Could not set state to {DocumentState.FAILED}')


class DocumentWorker(CommandWorker):

    def __init__(self, config: DocumentWorkerConfig, workdir: pathlib.Path):
        self.config = config
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
        Context.get().update_trace_id('-')
        Context.get().update_document_id('-')
        PdfWaterMarker.initialize(
            watermark_filename=self.config.experimental.pdf_watermark,
            watermark_top=self.config.experimental.pdf_watermark_top,
        )
        if self.config.sentry.enabled and self.config.sentry.workers_dsn is not None:
            SentryReporter.initialize(
                dsn=self.config.sentry.workers_dsn,
                environment=self.config.general.environment,
                server_name=self.config.general.client_url,
                release=BUILD_INFO.version,
                prog_name=PROG_NAME,
                config=self.config.sentry,
            )

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

    def _run_preparation(self) -> CommandQueue:
        Context.get().app.db.connect()
        # prepare
        self._update_component_info()
        # init queue
        LOG.info('Preparing command queue')
        queue = CommandQueue(
            worker=self,
            db=Context.get().app.db,
            channel=CMD_CHANNEL,
            component=CMD_COMPONENT,
            timeout=Context.get().app.cfg.db.queue_timout,
        )
        return queue

    def run(self):
        LOG.info('Starting document worker (loop)')
        queue = self._run_preparation()
        queue.run()

    def run_once(self):
        LOG.info('Starting document worker (once)')
        queue = self._run_preparation()
        queue.run_once()

    def work(self, cmd: PersistentCommand):
        Context.get().update_trace_id(cmd.uuid)
        Context.get().update_document_id(cmd.body['uuid'])
        SentryReporter.set_context('cmd_uuid', cmd.uuid)
        LOG.info(f'Running job #{cmd.uuid}')
        job = Job(command=cmd)
        job.run()
        Context.get().update_trace_id('-')
        Context.get().update_document_id('-')

    def process_exception(self, e: Exception):
        SentryReporter.capture_exception(e)
