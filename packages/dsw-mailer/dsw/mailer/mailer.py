import datetime
import dateutil.parser
import logging
import math
import pathlib
import time
import urllib.parse

from dsw.command_queue import CommandWorker, CommandQueue
from dsw.config.sentry import SentryReporter
from dsw.database.database import Database
from dsw.database.model import PersistentCommand

from .build_info import BUILD_INFO
from .config import MailerConfig, MailConfig, merge_mail_configs
from .consts import PROG_NAME
from .sender import send
from .consts import COMPONENT_NAME, CMD_CHANNEL, CMD_COMPONENT, \
    CMD_FUNCTION
from .context import Context
from .model import MessageRequest


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
        self.ctx = Context.get()

    def _init_context(self, workdir: pathlib.Path):
        Context.initialize(
            config=self.cfg,
            workdir=workdir,
            db=Database(cfg=self.cfg.db, connect=False),
        )
        SentryReporter.initialize(
            config=self.cfg.sentry,
            release=BUILD_INFO.version,
            prog_name=PROG_NAME,
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

    def work(self, cmd: PersistentCommand):
        # update Sentry info
        SentryReporter.set_tags(
            template='?',
            command_uuid=cmd.uuid,
            tenant_uuid=cmd.tenant_uuid,
        )
        Context.get().update_trace_id(cmd.uuid)
        # work
        app_ctx = Context.get().app
        mc = MailerCommand.load(cmd)
        rq = mc.to_request(
            msg_id=cmd.uuid,
            trigger='PersistentComment',
        )
        # get tenant config from DB
        tenant_cfg = app_ctx.db.get_tenant_config(tenant_uuid=cmd.tenant_uuid)
        LOG.debug(f'Tenant config from DB: {tenant_cfg}')
        if tenant_cfg is not None:
            rq.style.from_dict(tenant_cfg.look_and_feel)
        # get mailer config from DB
        mail_cfg = merge_mail_configs(
            cfg=self.cfg,
            db_cfg=app_ctx.db.get_mail_config(tenant_uuid=cmd.tenant_uuid),
        )
        LOG.debug(f'Mail config from DB: {mail_cfg}')
        # client URL
        rq.client_url = cmd.body.get('clientUrl', app_ctx.cfg.general.client_url)
        rq.domain = urllib.parse.urlparse(rq.client_url).hostname
        # update Sentry info
        SentryReporter.set_tags(template=rq.template_name)
        self.send(rq, mail_cfg)
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
        LOG.info(f'Sending request: {rq.template_name} ({rq.id})')
        # get template
        if not self.ctx.templates.has_template_for(rq):
            raise RuntimeError(f'Template not found: {rq.template_name}')
        # render
        LOG.info(f'Rendering message: {rq.template_name}')
        msg = self.ctx.templates.render(rq, cfg)
        # send
        LOG.info(f'Sending message: {rq.template_name}')
        send(msg, cfg)
        LOG.info('Message sent successfully')


class RateLimiter:

    def __init__(self, window: int, count: int):
        self.window = window
        self.count = count
        self.hits = []  # type: list[float]

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
                LOG.info(f'Will sleep now for {sleep_time} second')
                time.sleep(sleep_time)


class MailerCommand:

    def __init__(self, recipients: list[str], mode: str, template: str, ctx: dict,
                 tenant_uuid: str, cmd_uuid: str):
        self.mode = mode
        self.template = template
        self.recipients = recipients
        self.ctx = ctx
        self.tenant_uuid = tenant_uuid
        self.cmd_uuid = cmd_uuid
        self._enrich_context()

    def to_request(self, msg_id: str, trigger: str) -> MessageRequest:
        return MessageRequest(
            message_id=msg_id,
            template_name=f'{self.mode}:{self.template}',
            trigger=trigger,
            ctx=self.ctx,
            recipients=self.recipients,
        )

    def _enrich_context(self):
        self.ctx['_meta'] = {
            'cmd_uuid': self.cmd_uuid,
            'recipients': self.recipients,
            'mode': self.mode,
            'template': self.template,
            'now': datetime.datetime.now(tz=datetime.UTC),
        }

    @staticmethod
    def load(cmd: PersistentCommand) -> 'MailerCommand':
        if cmd.component != CMD_COMPONENT:
            raise RuntimeError('Tried to process non-mailer command')
        if cmd.function != CMD_FUNCTION:
            raise RuntimeError(f'Unsupported function: {cmd.function}')
        try:
            return MailerCommand(
                mode=cmd.body['mode'],
                template=cmd.body['template'],
                recipients=cmd.body['recipients'],
                ctx=cmd.body['parameters'],
                tenant_uuid=cmd.tenant_uuid,
                cmd_uuid=cmd.uuid,
            )
        except KeyError as e:
            raise RuntimeError(f'Cannot parse command: {str(e)}')
