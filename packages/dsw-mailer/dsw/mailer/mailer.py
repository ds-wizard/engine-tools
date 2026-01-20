import datetime
import logging
import math
import pathlib
import time

import dateutil.parser

from dsw.command_queue import CommandWorker, CommandQueue
from dsw.config.sentry import SentryReporter
from dsw.database.database import Database
from dsw.database.model import PersistentCommand
from dsw.storage import S3Storage

from .build_info import BUILD_INFO
from .config import MailerConfig, MailConfig, merge_mail_configs
from .consts import PROG_NAME
from .sender import send
from .consts import COMPONENT_NAME, CMD_CHANNEL, CMD_COMPONENT, \
    CMD_FUNCTION
from .context import Context
from .model import MessageRequest, MessageRecipient


LOG = logging.getLogger(__name__)


class Mailer(CommandWorker):

    def __init__(self, cfg: MailerConfig, workdir: pathlib.Path):
        self.cfg = cfg
        self.workdir = workdir
        self.rate_limiter = RateLimiter(
            window=cfg.mail.rate_limit_window,
            count=cfg.mail.rate_limit_count,
        )

        self._init_context(workdir=workdir)
        self._init_sentry()
        self.ctx = Context.get()

    def _init_context(self, workdir: pathlib.Path):
        Context.initialize(
            config=self.cfg,
            workdir=workdir,
            db=Database(cfg=self.cfg.db, connect=False),
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
            wait_timeout=Context.get().app.cfg.db.queue_timeout,
            work_timeout=Context.get().app.cfg.experimental.job_timeout,
        )
        return queue

    def run(self):
        LOG.info('Starting mailer worker (loop)')
        queue = self._run_preparation()
        queue.run()

    def run_once(self):
        LOG.info('Starting mailer worker (once)')
        queue = self._run_preparation()
        queue.run_once()

    def _get_locale_uuid(self, recipient_uuid: str, tenant_uuid: str) -> str | None:
        app_ctx = Context.get().app
        user = app_ctx.db.get_user(
            user_uuid=recipient_uuid,
            tenant_uuid=tenant_uuid,
        )
        if user is None:
            raise RuntimeError(f'Cannot find user: {recipient_uuid}')
        if user.locale is not None:
            return user.locale
        default_locale = app_ctx.db.get_default_locale(
            tenant_uuid=tenant_uuid,
        )
        if default_locale is not None:
            return default_locale.id
        return None

    def _get_msg_request(self, command: PersistentCommand) -> MessageRequest:
        mc = MailerCommand.load(command)
        if len(mc.recipients) == 0:
            raise RuntimeError('No recipients specified')
        first_recipient = mc.recipients[0]
        locale_uuid = None
        if first_recipient.uuid is not None:
            locale_uuid = self._get_locale_uuid(first_recipient.uuid, command.tenant_uuid)
        return mc.to_request(
            msg_id=command.uuid,
            trigger='PersistentComment',
            locale_uuid=locale_uuid,
        )

    def _get_mail_config(self, command: PersistentCommand) -> MailConfig:
        app_ctx = Context.get().app
        params: dict = command.body.get('parameters', {})
        mail_config_uuid: str | None = params.get('mailConfigUuid', None)
        db_cfg = None
        if mail_config_uuid is not None:
            LOG.debug('Loading mail config from DB: %s', mail_config_uuid)
            db_cfg = app_ctx.db.get_mail_config(
                mail_config_uuid=mail_config_uuid,
            )
        mail_cfg = merge_mail_configs(
            cfg=self.cfg,
            db_cfg=db_cfg,
        )
        LOG.debug('Mail config: %s', mail_cfg)
        return mail_cfg

    def work(self, command: PersistentCommand):
        # init Sentry info
        SentryReporter.set_tags(
            template='?',
            command_uuid=command.uuid,
            tenant_uuid=command.tenant_uuid,
        )
        Context.get().update_trace_id(command.uuid)
        # prepare
        rq = self._get_msg_request(command)
        mail_cfg = self._get_mail_config(command)
        # update Sentry info
        SentryReporter.set_tags(template=rq.template_name)
        # send the message
        self.send(rq, mail_cfg)
        # reset Sentry info
        SentryReporter.set_tags(
            template='-',
            command_uuid='-',
            tenant_uuid='-',
        )
        Context.get().update_trace_id('-')

    def process_timeout(self, e: BaseException):
        LOG.info('Failed with timeout')
        SentryReporter.capture_exception(e)

    def process_exception(self, e: BaseException):
        LOG.info('Failed with unexpected error', exc_info=e)
        SentryReporter.capture_exception(e)

    def send(self, rq: MessageRequest, cfg: MailConfig):
        LOG.info('Sending request: %s (%s)', rq.template_name, rq.id)
        # get template
        if not self.ctx.templates.has_template_for(rq):
            raise RuntimeError(f'Template not found: {rq.template_name}')
        # render
        LOG.info('Rendering message: %s', rq.template_name)
        LOG.warning('Should send with locale: %s', rq.locale_uuid)
        msg = self.ctx.templates.render(rq, cfg, Context.get().app)
        # send
        LOG.info('Sending message: %s', rq.template_name)
        send(msg, cfg)
        LOG.info('Message sent successfully')


class RateLimiter:

    def __init__(self, window: int, count: int):
        self.window = window
        self.count = count
        self.hits: list[float] = []

    def hit(self):
        if self.window == 0:
            return
        LOG.debug('Hit for checking rate limit')
        now = datetime.datetime.now(tz=datetime.UTC).timestamp()
        threshold = now - self.window
        while len(self.hits) > 0 and self.hits[0] < threshold:
            self.hits.pop()
        self.hits.append(now)

        if len(self.hits) >= self.count:
            LOG.info('Reached rate limit')
            sleep_time = math.ceil(self.window - now + self.hits[0])
            if sleep_time > 1:
                LOG.info('Will sleep now for %s seconds', sleep_time)
                time.sleep(sleep_time)


class MailerCommand:

    def __init__(self, *, recipients: list[MessageRecipient], mode: str,
                 template: str, ctx: dict, tenant_uuid: str, cmd_uuid: str):
        self.mode = mode
        self.template = template
        self.recipients = recipients
        self.ctx = ctx
        self.tenant_uuid = tenant_uuid
        self.cmd_uuid = cmd_uuid
        self._enrich_context()

    def to_request(self, msg_id: str, locale_uuid: str | None, trigger: str) -> MessageRequest:
        rq = MessageRequest(
            message_id=msg_id,
            template_name=f'{self.mode}:{self.template}',
            tenant_uuid=self.tenant_uuid,
            locale_uuid=locale_uuid,
            trigger=trigger,
            ctx=self.ctx,
            recipients=self.recipients,
        )
        rq.style.from_dict(self.ctx)
        return rq

    def _enrich_context(self):
        self.ctx['_meta'] = {
            'cmd_uuid': self.cmd_uuid,
            'recipients': self.recipients,
            'mode': self.mode,
            'template': self.template,
            'now': datetime.datetime.now(tz=datetime.UTC),
        }

    @staticmethod
    def load(command: PersistentCommand) -> 'MailerCommand':
        if command.component != CMD_COMPONENT:
            raise RuntimeError('Tried to process non-mailer command')
        if command.function != CMD_FUNCTION:
            raise RuntimeError(f'Unsupported function: {command.function}')
        try:
            return MailerCommand(
                mode=command.body['mode'],
                template=command.body['template'],
                recipients=[MessageRecipient.from_dict(data)
                            for data in command.body.get('recipients', [])],
                ctx=command.body['parameters'],
                tenant_uuid=command.tenant_uuid,
                cmd_uuid=command.uuid,
            )
        except KeyError as e:
            raise RuntimeError(f'Cannot parse command: {str(e)}') from e
