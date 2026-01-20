import datetime
import functools
import logging
import pathlib
import typing

import dateutil.parser
import sentry_sdk.types as sentry

from dsw.command_queue import CommandQueue, CommandWorker
from dsw.config.sentry import SentryReporter
from dsw.database.database import Database
from dsw.database.model import DBDocument, PersistentCommand
from dsw.storage import S3Storage

from . import consts
from .build_info import BUILD_INFO
from .config import DocumentWorkerConfig, TemplateConfig
from .context import Context
from .documents import DocumentFile, DocumentNameGiver
from .exceptions import DocumentNotFoundError, JobError, create_job_error
from .limits import LimitsEnforcer
from .templates import Format, Template, TemplateRegistry
from .utils import byte_size_format, check_metamodel_version


LOG = logging.getLogger(__name__)


def handle_job_step(message):
    def decorator(func):
        @functools.wraps(func)
        def handled_step(job, *args, **kwargs):
            try:
                return func(job, *args, **kwargs)
            except Exception as e:
                LOG.info('Handling exception', exc_info=True)
                new_exception = create_job_error(
                    job_id=job.doc_uuid,
                    message=message,
                    exc=e,
                )
                raise new_exception from e
        return handled_step
    return decorator


class Job:

    def __init__(self, command: PersistentCommand, document_uuid: str):
        self.ctx = Context.get()
        self.template: Template | None = None
        self.format: Format | None = None
        self.tenant_uuid = self.ctx.tenant_uuid = command.tenant_uuid
        self.doc_uuid: str = document_uuid
        self.doc_context: dict = command.body
        self.doc: DBDocument | None = None
        self.final_file: DocumentFile | None = None
        self.template_config: TemplateConfig | None = None
        self.tenant_limits = self.ctx.app.db.fetch_tenant_limits(self.tenant_uuid)

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

    def check_document_exists(self) -> bool:
        LOG.debug('Checking if document "%s" exists in DB', self.doc_uuid)
        try:
            doc = self.ctx.app.db.fetch_document(
                document_uuid=self.doc_uuid,
                tenant_uuid=self.tenant_uuid,
            )
            exists = doc is not None
            LOG.debug('Document "%s" exists: %s', self.doc_uuid, exists)
            return exists
        except Exception as e:
            LOG.error('Failed to check if document "%s" exists: %s',
                      self.doc_uuid, str(e))
            return False

    @handle_job_step('Failed to get document from DB')
    def get_document(self):
        SentryReporter.set_tags(phase='fetch')
        SentryReporter.set_tags(
            template='?',
            format='?',
        )
        if self.tenant_uuid != consts.NULL_UUID:
            LOG.info('Limiting to tenant with UUID: %s', self.tenant_uuid)
        LOG.info('Getting the document "%s" details from DB', self.doc_uuid)
        self.doc = self.ctx.app.db.fetch_document(
            document_uuid=self.doc_uuid,
            tenant_uuid=self.tenant_uuid,
        )
        if self.doc is None:
            raise create_job_error(
                job_id=self.doc_uuid,
                message='Document record not found in database',
                document_found=False,
            )
        self.doc.retrieved_at = datetime.datetime.now(tz=datetime.UTC)
        LOG.info('Job "%s" details received', self.doc_uuid)
        # verify state
        state = self.doc.state
        LOG.info('Original state of job is %s', state)
        if state == consts.DocumentState.FINISHED:
            raise create_job_error(
                job_id=self.doc_uuid,
                message='Document is already marked as finished',
            )
        self.ctx.app.db.update_document_retrieved(
            retrieved_at=self.doc.retrieved_at,
            document_uuid=self.doc_uuid,
        )

    @handle_job_step('Failed to prepare template')
    def prepare_template(self):
        SentryReporter.set_tags(phase='prepare')
        template_id = self.safe_doc.document_template_id
        format_uuid = self.safe_doc.format_uuid
        LOG.info('Document uses template %s with format %s',
                 template_id, format_uuid)
        # update Sentry info
        SentryReporter.set_tags(
            template=template_id,
            format=format_uuid,
        )
        # prepare template
        template = TemplateRegistry.get().prepare_template(
            tenant_uuid=self.tenant_uuid,
            template_id=template_id,
        )
        # prepare format
        if not template.prepare_format(format_uuid):
            raise create_job_error(
                job_id=self.doc_uuid,
                message=f'Format {format_uuid} is not found in template {template_id}',
            )
        self.format = template.formats.get(format_uuid)
        # finalize
        self.template = template
        # fetch template config
        self.template_config = self.ctx.app.cfg.templates.get_config(template_id)

    def _enrich_context_config(self):
        old = self.doc_context.get('config', {})

        client_url = old.get('clientUrl', '').rstrip('/')
        app_title = (old.get('appTitle', None) or
                     self.ctx.app.cfg.context.default_app_title)
        app_title_short = (old.get('appTitleShort', None) or
                           self.ctx.app.cfg.context.default_app_title_short)
        primary_color = (old.get('primaryColor', None) or
                         self.ctx.app.cfg.context.default_primary_color)
        illustrations_color = (old.get('illustrationsColor', None) or
                               self.ctx.app.cfg.context.default_illustrations_color)
        logo_url_template = (old.get('logoUrl', None) or
                             self.ctx.app.cfg.context.default_logo_url)
        logo_url = logo_url_template.replace('{{clientUrl}}', client_url)

        self.doc_context['config'].update({
            'serviceName': self.ctx.app.cfg.context.service_name,
            'serviceNameShort': self.ctx.app.cfg.context.service_name_short,
            'serviceUrl': self.ctx.app.cfg.context.service_url,
            'serviceDomainName': self.ctx.app.cfg.context.service_domain_name,
            'appTitle': app_title,
            'appTitleShort': app_title_short,
            'primaryColor': primary_color,
            'illustrationsColor': illustrations_color,
            'logoUrl': logo_url,
        })

    def _enrich_context(self):
        extras: dict[str, typing.Any] = {}
        if self.safe_format.requires_via_extras('submissions'):
            if self.safe_doc.project_uuid is None:
                submissions = []
            else:
                submissions = self.ctx.app.db.fetch_project_submissions(
                    project_uuid=self.safe_doc.project_uuid,
                    tenant_uuid=self.tenant_uuid,
                )
            extras['submissions'] = [s.to_dict() for s in submissions]
        if self.safe_format.requires_via_extras('questionnaire'):
            # older deprecated variant (questionnaire -> project)
            if self.safe_doc.project_uuid is None:
                extras['questionnaire'] = None
            else:
                questionnaire = self.ctx.app.db.fetch_project_simple(
                    project_uuid=self.safe_doc.project_uuid,
                    tenant_uuid=self.tenant_uuid,
                )
                extras['questionnaire'] = questionnaire.to_dict()
        if self.safe_format.requires_via_extras('project'):
            if self.safe_doc.project_uuid is None:
                extras['project'] = None
            else:
                project = self.ctx.app.db.fetch_project_simple(
                    project_uuid=self.safe_doc.project_uuid,
                    tenant_uuid=self.tenant_uuid,
                )
                extras['project'] = project.to_dict()
        self.doc_context['extras'] = extras
        self._enrich_context_config()

    def check_compliance(self):
        SentryReporter.set_tags(phase='check')
        check_metamodel_version(
            metamodel_version=str(self.doc_context.get('metamodelVersion', '0')),
        )

    @handle_job_step('Failed to build final document')
    def build_document(self):
        LOG.info('Building document by rendering template with context')
        doc = self.safe_doc
        # enrich context
        SentryReporter.set_tags(phase='enrich')
        self._enrich_context()
        # render document
        SentryReporter.set_tags(phase='render')
        final_file = self.safe_template.render(
            format_uuid=doc.format_uuid,
            project_uuid=self.safe_doc.project_uuid,
            context=self.doc_context,
        )
        # check limits
        SentryReporter.set_tags(phase='limit')
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
        # finalize
        self.final_file = final_file

    @handle_job_step('Failed to store document in S3')
    def store_document(self):
        SentryReporter.set_tags(phase='store')
        s3_id = self.ctx.app.s3.identification
        final_file = self.safe_final_file
        LOG.info('Preparing S3 bucket %s', s3_id)
        self.ctx.app.s3.ensure_bucket()
        LOG.info('Storing document to S3 bucket %s', s3_id)
        self.ctx.app.s3.store_document(
            tenant_uuid=self.tenant_uuid,
            file_name=self.doc_uuid,
            content_type=final_file.object_content_type,
            data=final_file.content,
        )
        LOG.info('Document %s stored in S3 bucket %s',
                 self.doc_uuid, s3_id)

    @handle_job_step('Failed to finalize document generation')
    def finalize(self):
        SentryReporter.set_tags(phase='finalize')
        doc = self.safe_doc
        final_file = self.safe_final_file
        file_name = DocumentNameGiver.name_document(doc, final_file)
        doc.finished_at = datetime.datetime.now(tz=datetime.UTC)
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
        LOG.info('Document %s record finalized', self.doc_uuid)

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
            LOG.warning('Tried to set state of %s to %s but failed: %s',
                        self.doc_uuid, state, str(e))
            return False

    def _run(self):
        self.check_compliance()
        self.get_document()

        self.prepare_template()
        self.build_document()
        self.store_document()

        self.finalize()

    def _set_failed(self, message: str):
        document_exists = self.check_document_exists()
        if not document_exists:
            LOG.warning('Document %s does not exist, cannot set to FAILED',
                        self.doc_uuid)
            return
        if self.try_set_job_state(consts.DocumentState.FAILED, message):
            LOG.info('Set state to FAILED')
        else:
            msg = 'Could not set state to FAILED'
            SentryReporter.capture_message(msg)
            LOG.error(msg)
            raise RuntimeError(msg)

    def run(self):
        try:
            self._run()
        except DocumentNotFoundError as e:
            LOG.warning('Document not found: %s', e.log_message())
        except JobError as e:
            LOG.warning('Handled job error: %s', e.log_message())
            SentryReporter.capture_exception(e)
            self._set_failed(e.db_message())
        except Exception as e:
            SentryReporter.capture_exception(e)
            job_exc = create_job_error(
                job_id=self.doc_uuid,
                message='Failed with unexpected error',
                exc=e,
            )
            LOG.error(job_exc.log_message())
            LOG.info('Failed with unexpected error', exc_info=e)
            self._set_failed(job_exc.db_message())


class DocumentWorker(CommandWorker):

    def __init__(self, config: DocumentWorkerConfig, workdir: pathlib.Path):
        self.config = config
        self.current_job: Job | None = None

        self._init_context(workdir=workdir)
        self._init_sentry()

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

    def _init_sentry(self):
        SentryReporter.initialize(
            config=self.config.sentry,
            release=BUILD_INFO.version,
            prog_name=consts.PROG_NAME,
            event_level=None,
        )

        def filter_templates(event: sentry.Event, hint: sentry.Hint) -> sentry.Event | None:
            LOG.debug('Filtering Sentry event (template, %s, %s)',
                      event.get('event_id'), hint)

            if 'exc_info' in hint:
                exc_info = hint['exc_info']
                if isinstance(exc_info, tuple) and len(exc_info) > 1:
                    exc = exc_info[1]
                    if isinstance(exc, JobError) and exc.skip_reporting:
                        LOG.debug('Skipping Sentry event (JobError, %s, %s)',
                                  event.get('event_id'), hint)
                        return None

            template = event.get('tags', {}).get('template')
            phase = event.get('tags', {}).get('phase')
            if phase in ('render', 'prepare') and template is not None:
                template_config = Context.get().app.cfg.templates.get_config(template)
                send_sentry = template_config.send_sentry if template_config else False
                if not send_sentry:
                    LOG.debug('Skipping Sentry event (template, %s, %s)',
                              event.get('event_id'), hint)
                    return None
            LOG.debug('Sending Sentry event (template, %s, %s)',
                      event.get('event_id'), hint)
            return event

        SentryReporter.filters.append(filter_templates)

    @staticmethod
    def _update_component_info():
        built_at = dateutil.parser.parse(BUILD_INFO.built_at)
        LOG.info('Updating component info (%s, %s)',
                 BUILD_INFO.version, built_at.isoformat(timespec='seconds'))
        Context.get().app.db.update_component_info(
            name=consts.COMPONENT_NAME,
            version=BUILD_INFO.version,
            built_at=built_at,
        )

    def _run_preparation(self) -> CommandQueue:
        Context.get().app.db.connect()
        # prepare
        self._update_component_info()
        # init queue
        LOG.info('Preparing command queue')
        return CommandQueue(
            worker=self,
            db=Context.get().app.db,
            channel=consts.CMD_CHANNEL,
            component=consts.CMD_COMPONENT,
            wait_timeout=Context.get().app.cfg.db.queue_timeout,
            work_timeout=Context.get().app.cfg.experimental.job_timeout,
        )

    def run(self):
        LOG.info('Starting document worker (loop)')
        queue = self._run_preparation()
        queue.run()

    def run_once(self):
        LOG.info('Starting document worker (once)')
        queue = self._run_preparation()
        queue.run_once()

    def work(self, command: PersistentCommand):
        document_uuid = command.body['document']['uuid']
        Context.get().update_trace_id(command.uuid)
        Context.get().update_document_id(document_uuid)
        SentryReporter.set_tags(
            command_uuid=command.uuid,
            tenant_uuid=command.tenant_uuid,
            document_uuid=document_uuid,
            phase='init',
        )
        LOG.info('Running job #%s', command.uuid)
        self.current_job = Job(command=command, document_uuid=document_uuid)
        self.current_job.run()
        self.current_job = None
        SentryReporter.set_tags(
            command_uuid='-',
            tenant_uuid='-',
            document_uuid='-',
            phase='done',
        )
        Context.get().update_trace_id('-')
        Context.get().update_document_id('-')

    def process_exception(self, e: BaseException):
        LOG.info('Failed with exception')
        SentryReporter.capture_exception(e)

    def process_timeout(self, e: BaseException):
        LOG.info('Failed with timeout')
        SentryReporter.capture_exception(e)

        if self.current_job is not None:
            self.current_job.try_set_job_state(
                consts.DocumentState.FAILED,
                'Generating document exceeded the time limit',
            )
            self.current_job = None
