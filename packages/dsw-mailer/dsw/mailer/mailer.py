from __future__ import annotations

import copy
import datetime
import gettext
import logging
import math
import pathlib
import tempfile
import time
import typing
import zipfile

import dateutil.parser

from dsw.command_queue import CommandQueue, CommandWorker
from dsw.config.sentry import SentryReporter
from dsw.database.database import Database
from dsw.storage import S3Storage

from . import consts, pot
from .build_info import BUILD_INFO
from .config import MailConfig, MailerConfig, merge_mail_configs
from .context import Context
from .locales import LocaleLoader, resolve_mail_locale
from .model import MailMessage, MessageRecipient, MessageRequest
from .sender import send
from .templates import TemplateRegistry


if typing.TYPE_CHECKING:
    from dsw.database.model import PersistentCommand


LOG = logging.getLogger(__name__)


class Mailer(CommandWorker):

    #: the default POT is synced once per process (worker start, Lambda cold start)
    _default_pot_synced = False

    def __init__(self, cfg: MailerConfig, workdir: pathlib.Path):
        self.cfg = cfg
        self.workdir = workdir
        #: compiled mail template locales; the templates directory may be read-only (Lambda)
        self.cache_dir = pathlib.Path(tempfile.gettempdir()) / 'dsw-mailer'
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
            component=consts.CMD_COMPONENT,
        )

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
        self._sync_default_pot_at_startup()
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

    def sync_default_pot(self, *, force: bool = False) -> pot.SyncResult:
        return pot.sync_default_pot(self.ctx.app.s3, self.workdir, force=force)

    def _sync_default_pot_at_startup(self):
        """Never blocks sending mail: a failure is only reported."""
        if not self.cfg.mail.sync_default_pot or Mailer._default_pot_synced:
            return
        Mailer._default_pot_synced = True
        if not (self.workdir / pot.POT_PATH).exists():
            LOG.warning('No default mail POT in the templates (%s), not syncing it; '
                        'build it with: dsw-mailer make-pot', pot.POT_PATH)
            return
        try:
            self.sync_default_pot()
        except Exception as e:
            LOG.warning('Cannot sync the default mail POT: %s', str(e))
            SentryReporter.capture_exception(e)

    def run(self):
        LOG.info('Starting mailer worker (loop)')
        queue = self._run_preparation()
        queue.run()

    def run_once(self):
        LOG.info('Starting mailer worker (once)')
        queue = self._run_preparation()
        queue.run_once()

    def _ui_locale_code(self, recipient: MessageRecipient, tenant_uuid: str) -> str | None:
        """Code of the recipient's enabled UI locale, if the recipient is a user with one."""
        if recipient.uuid is None:
            return None
        db = Context.get().app.db
        user = db.get_user(user_uuid=recipient.uuid, tenant_uuid=tenant_uuid)
        if user is None:
            LOG.warning('Recipient %s is not a user, using the default mail locale',
                        recipient.uuid)
            return None
        if user.locale is None:
            return None
        locale = db.get_locale(locale_uuid=user.locale, tenant_uuid=tenant_uuid)
        if locale is None or not locale.enabled:
            return None
        return locale.code

    def _get_msg_requests(self, mc: MailerCommand) -> list[MessageRequest]:
        """One request per recipient in their language, or one in English for all."""
        if len(mc.recipients) == 0:
            raise RuntimeError('No recipients specified')
        if mc.send_as_one or mc.mode == consts.REGISTRY_MODE:
            return [mc.to_request(msg_id=mc.cmd_uuid, trigger=consts.TRIGGER,
                                  locale_uuid=None, recipients=mc.recipients)]
        locales = Context.get().app.db.get_enabled_mail_template_locales(
            tenant_uuid=mc.tenant_uuid,
        )
        requests = []
        for recipient in mc.recipients:
            ui_code = self._ui_locale_code(recipient, mc.tenant_uuid)
            locale = resolve_mail_locale(ui_code, locales)
            LOG.debug('Recipient %s (UI locale %s) gets mail locale %s',
                      recipient.uuid, ui_code, None if locale is None else locale.code)
            requests.append(mc.to_request(
                msg_id=mc.cmd_uuid,
                trigger=consts.TRIGGER,
                locale_uuid=None if locale is None else locale.uuid,
                recipients=[recipient],
            ))
        return requests

    def _get_mail_config(self, command: PersistentCommand) -> MailConfig:
        app_ctx = Context.get().app
        params: dict = command.body.get('parameters', {})
        mail_config_uuid: str | None = params.get('mailConfigUuid')
        custom_templates: bool = params.get('mailCustomTemplates', False)
        db_cfg = None
        if mail_config_uuid is not None:
            LOG.debug('Loading mail config from DB: %s', mail_config_uuid)
            db_cfg = app_ctx.db.get_mail_config(
                mail_config_uuid=mail_config_uuid,
            )
            if db_cfg is None:
                raise RuntimeError(f'Cannot find mail config: {mail_config_uuid}')
        mail_cfg = merge_mail_configs(
            cfg=self.cfg,
            db_cfg=db_cfg,
        )
        mail_cfg.custom_templates = custom_templates
        LOG.debug('Mail config: %s', mail_cfg)
        return mail_cfg

    def _prepare_custom_templates(self, tenant_uuid: str, destination: pathlib.Path):
        destination.mkdir(parents=True, exist_ok=True)
        zip_path = destination / 'mail-templates.zip'
        # Download the zip file from S3
        downloaded = self.ctx.app.s3.download_mail_templates(
            tenant_uuid=tenant_uuid,
            target_path=zip_path,
        )
        if not downloaded:
            raise RuntimeError(f'Cannot download custom mail templates for tenant {tenant_uuid}')
        # Extract the zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(destination)
        # Remove the zip file after extraction
        zip_path.unlink()

    def work(self, command: PersistentCommand):
        # init Sentry info
        SentryReporter.set_command(command)
        SentryReporter.set_tags(template='?')
        Context.get().update_trace_id(command.uuid)
        # prepare
        requests = self._get_msg_requests(MailerCommand.load(command))
        mail_cfg = self._get_mail_config(command)
        # send the messages
        for rq in requests:
            SentryReporter.set_tags(template=rq.template_name)
            self.send(rq, mail_cfg)
        # reset Sentry info
        SentryReporter.reset_command()
        SentryReporter.set_tags(template='-')
        Context.get().update_trace_id('-')

    def process_timeout(self, e: BaseException):
        LOG.info('Failed with timeout')
        SentryReporter.capture_exception(e)

    def process_exception(self, e: BaseException):
        LOG.info('Failed with unexpected error', exc_info=e)
        SentryReporter.capture_exception(e)

    def _render_builtin(self, rq: MessageRequest, cfg: MailConfig,
                        translations: gettext.NullTranslations) -> MailMessage:
        if not self.ctx.templates.has_template_for(rq):
            raise RuntimeError(f'Template not found: {rq.template_name}')
        return self.ctx.templates.render(rq, cfg, translations)

    def _translations(self, rq: MessageRequest) -> gettext.NullTranslations:
        """Translations of the request's mail template locale; English if it cannot be used."""
        if rq.locale_uuid is None:
            return gettext.NullTranslations()
        app_ctx = Context.get().app
        try:
            locale = app_ctx.db.get_mail_template_locale(
                locale_uuid=rq.locale_uuid,
                tenant_uuid=rq.tenant_uuid,
            )
            if locale is None or not locale.enabled:
                LOG.warning('Mail template locale %s is not available, rendering in English',
                            rq.locale_uuid)
                return gettext.NullTranslations()
            LOG.info('Rendering with mail template locale %s (%s)', locale.code, locale.uuid)
            loader = LocaleLoader(
                s3=app_ctx.s3,
                cache_dir=self.cache_dir / 'mail-template-locales',
                tenant_uuid=rq.tenant_uuid,
            )
            return loader.load(locale)
        except Exception as e:
            LOG.warning('Cannot load mail template locale %s, rendering in English: %s',
                        rq.locale_uuid, str(e))
            SentryReporter.capture_exception(e)
            return gettext.NullTranslations()

    def send(self, rq: MessageRequest, cfg: MailConfig):
        LOG.info('Sending request: %s (%s)', rq.template_name, rq.id)
        translations = self._translations(rq)
        # render
        LOG.info('Rendering message: %s', rq.template_name)
        if cfg.custom_templates:
            with tempfile.TemporaryDirectory() as tmpdir:
                templates_dir = pathlib.Path(tmpdir) / 'templates'
                self._prepare_custom_templates(
                    tenant_uuid=rq.tenant_uuid,
                    destination=templates_dir,
                )
                templates = TemplateRegistry(
                    cfg=self.ctx.app.cfg,
                    workdir=templates_dir,
                )
                if templates.has_template_for(rq):
                    msg = templates.render(rq, cfg, translations)
                else:
                    LOG.info('Template "%s" not customized - using the built-in one',
                             rq.template_name)
                    msg = self._render_builtin(rq, cfg, translations)
        else:
            msg = self._render_builtin(rq, cfg, translations)
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
                 template: str, ctx: dict, tenant_uuid: str, cmd_uuid: str,
                 send_as_one: bool = False):
        self.mode = mode
        self.template = template
        self.recipients = recipients
        self.ctx = ctx
        self.tenant_uuid = tenant_uuid
        self.cmd_uuid = cmd_uuid
        #: one mail to all recipients in English, instead of one per recipient
        self.send_as_one = send_as_one
        self.now = datetime.datetime.now(tz=datetime.UTC)

    def to_request(self, msg_id: str, locale_uuid: str | None, trigger: str,
                   recipients: list[MessageRecipient]) -> MessageRequest:
        # rendering changes the context, so each request has its own copy
        ctx = copy.deepcopy(self.ctx)
        ctx['_meta'] = {
            'cmd_uuid': self.cmd_uuid,
            'recipients': recipients,
            'mode': self.mode,
            'template': self.template,
            'now': self.now,
        }
        rq = MessageRequest(
            message_id=msg_id,
            template_name=f'{self.mode}:{self.template}',
            tenant_uuid=self.tenant_uuid,
            locale_uuid=locale_uuid,
            trigger=trigger,
            ctx=ctx,
            recipients=recipients,
        )
        rq.style.from_dict(ctx)
        return rq

    @staticmethod
    def load(command: PersistentCommand) -> MailerCommand:
        if command.component != consts.CMD_COMPONENT:
            raise RuntimeError('Tried to process non-mailer command')
        if command.function != consts.CMD_FUNCTION:
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
                # missing in commands queued before Wizard 5.0
                send_as_one=command.body.get('sendAsOne', False),
            )
        except KeyError as e:
            raise RuntimeError(f'Cannot parse command: {str(e)}') from e
