import abc
import datetime
import dateutil.parser
import math
import pathlib
import time
import urllib.parse

from typing import Optional

from dsw.command_queue import CommandWorker, CommandQueue
from dsw.database.database import Database
from dsw.database.model import DBAppConfig, PersistentCommand, \
    DBInstanceConfigMail

from .build_info import BUILD_INFO
from .config import MailerConfig, MailConfig
from .connection import SMTPSender, SentryReporter
from .consts import COMPONENT_NAME, CMD_CHANNEL, CMD_COMPONENT
from .context import Context
from .model import MessageRequest


class Mailer(CommandWorker):

    def __init__(self, cfg: MailerConfig, workdir: pathlib.Path, mode: str):
        self.cfg = cfg
        self.workdir = workdir
        self.rate_limiter = RateLimiter(
            window=cfg.mail.rate_limit_window,
            count=cfg.mail.rate_limit_count,
        )

        self._prepare_logging()
        self._init_context(workdir=workdir, mode=mode)
        self.ctx = Context.get()

    def _init_context(self, workdir: pathlib.Path, mode: str):
        Context.initialize(
            config=self.cfg,
            workdir=workdir,
            db=Database(cfg=self.cfg.db),
            sender=SMTPSender(cfg=self.cfg.mail),
            mode=mode,
        )
        if self.cfg.sentry.enabled and self.cfg.sentry.workers_dsn is not None:
            SentryReporter.initialize(
                dsn=self.cfg.sentry.workers_dsn,
                environment=self.cfg.general.environment,
                server_name=self.cfg.general.client_url,
            )

    def _prepare_logging(self):
        Context.logger.set_level(self.cfg.log.level)

    @staticmethod
    def _update_component_info():
        built_at = dateutil.parser.parse(BUILD_INFO.built_at)
        Context.logger.info(f'Updating component info ({BUILD_INFO.version}, '
                            f'{built_at.isoformat(timespec="seconds")})')
        Context.get().app.db.update_component_info(
            name=COMPONENT_NAME,
            version=BUILD_INFO.version,
            built_at=built_at,
        )

    def run(self):
        Context.get().app.db.connect()
        # prepare
        self._update_component_info()
        # work in queue
        Context.logger.info('Preparing command queue')
        queue = CommandQueue(
            worker=self,
            db=Context.get().app.db,
            channel=CMD_CHANNEL,
            component=CMD_COMPONENT,
        )
        queue.run()

    def work(self, cmd: PersistentCommand):
        # update Sentry info
        SentryReporter.set_context('template', '')
        # work
        app_ctx = Context.get().app
        mc = load_mailer_command(cmd)
        mc.prepare(app_ctx.db)
        rq = mc.to_request(
            msg_id=cmd.uuid,
            trigger='PersistentComment',
        )
        # get mailer config from DB
        cfg = None
        if Context.is_wizard_mode():
            cfg = _transform_mail_config(
                cfg=app_ctx.db.get_mail_config(app_uuid=cmd.app_uuid),
            )
        Context.logger.debug(f'Config from DB: {cfg}')
        # client URL
        rq.client_url = cmd.body.get('clientUrl', app_ctx.cfg.general.client_url)
        rq.domain = urllib.parse.urlparse(rq.client_url).hostname
        # update Sentry info
        SentryReporter.set_context('template', rq.template_name)
        self.send(rq, cfg)

    def process_exception(self, e: Exception):
        SentryReporter.capture_exception(e)

    def send(self, rq: MessageRequest, cfg: Optional[MailConfig]):
        Context.logger.info(f'Sending request: {rq.template_name} ({rq.id})')
        # get template
        if not self.ctx.templates.has_template_for(rq):
            raise RuntimeError(f'Template not found: {rq.template_name}')
        # render
        Context.logger.info(f'Rendering message: {rq.template_name}')
        msg = self.ctx.templates.render(rq, cfg)
        # send
        Context.logger.info(f'Sending message: {rq.template_name}')
        self.ctx.app.sender.send(msg, cfg)
        Context.logger.info('Message sent successfully')


def _transform_mail_config(cfg: Optional[DBInstanceConfigMail]) -> Optional[MailConfig]:
    if cfg is None:
        return None
    return MailConfig(
        enabled=cfg.enabled,
        name=cfg.sender_name,
        email=cfg.sender_email,
        host=cfg.host,
        port=cfg.port,
        security=cfg.security,
        username=cfg.username,
        password=cfg.password,
        rate_limit_window=cfg.rate_limit_window,
        rate_limit_count=cfg.rate_limit_count,
        timeout=cfg.timeout,
        ssl=None,
        auth=None,
    )


#########################################################################################
# Commands and their logic
#########################################################################################


class RateLimiter:

    def __init__(self, window: int, count: int):
        self.window = window
        self.count = count
        self.hits = []  # type: list[float]

    def hit(self):
        if self.window == 0:
            return
        Context.logger.debug('Hit for checking rate limit')
        now = datetime.datetime.now().timestamp()
        threshold = now - self.window
        while len(self.hits) > 0 and self.hits[0] < threshold:
            self.hits.pop()
        self.hits.append(now)

        if len(self.hits) >= self.count:
            Context.logger.info('Reached rate limit')
            sleep_time = math.ceil(self.window - now + self.hits[0])
            if sleep_time > 1:
                Context.logger.info(f'Will sleep now for {sleep_time} second')
                time.sleep(sleep_time)


def _app_config_to_context(app_config: Optional[DBAppConfig]) -> dict:
    if app_config is None:
        return {}
    return {
        'supportEmail': app_config.support_email,
        'appTitle': app_config.app_title,
    }


class MailerCommand(abc.ABC):

    FUNCTION_NAME = 'unknown'
    TEMPLATE_NAME = ''

    @abc.abstractmethod
    def to_context(self) -> dict:
        pass

    @abc.abstractmethod
    def to_request(self, msg_id: str, trigger: str) -> MessageRequest:
        pass

    def prepare(self, db: Database):
        pass

    @classmethod
    def corresponds(cls, cmd: PersistentCommand) -> bool:
        return cls.FUNCTION_NAME == cmd.function

    @staticmethod
    @abc.abstractmethod
    def create_from(cmd: PersistentCommand) -> 'MailerCommand':
        pass


class CmdUser:

    def __init__(self, user_uuid: str, first_name: str, last_name: str,
                 email: str):
        self.uuid = user_uuid
        self.first_name = first_name
        self.last_name = last_name
        self.email = email

    def to_context(self) -> dict:
        return {
            'uuid': self.uuid,
            'firstName': self.first_name,
            'lastName': self.last_name,
            'email': self.email
        }


class CmdOrg:

    def __init__(self, org_id: str, name: str, email: str):
        self.id = org_id
        self.name = name
        self.email = email

    def to_context(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email
        }


class MailerWizardCommand(MailerCommand):

    def __init__(self, app_uuid: str):
        self.app_uuid = app_uuid
        self.app_config = None  # type: Optional[DBAppConfig]

    def prepare(self, db: Database):
        self.app_config = db.get_app_config(
            app_uuid=self.app_uuid,
        )


class _MWRegistrationConfirmation(MailerWizardCommand):

    FUNCTION_NAME = 'sendRegistrationConfirmationMail'
    TEMPLATE_NAME = 'registrationConfirmation'

    def __init__(self, email: str, user: CmdUser, code: str,
                 client_url: str, app_uuid: str):
        super().__init__(app_uuid=app_uuid)
        self.email = email
        self.user = user
        self.code = code
        self.client_url = client_url

    @property
    def activation_link(self):
        return f'{self.client_url}/signup/{self.user.uuid}/{self.code}'

    def to_context(self) -> dict:
        ctx = {
            'user': self.user.to_context(),
            'activationLink': self.activation_link,
            'clientUrl': self.client_url,
            'hash': self.code,
        }
        ctx.update(_app_config_to_context(self.app_config))
        return ctx

    def to_request(self, msg_id: str, trigger: str) -> MessageRequest:
        return MessageRequest(
            message_id=msg_id,
            template_name=self.TEMPLATE_NAME,
            trigger=trigger,
            ctx=self.to_context(),
            recipients=[self.email],
        )

    @classmethod
    def corresponds(cls, cmd: PersistentCommand) -> bool:
        return cls.FUNCTION_NAME == cmd.function and 'userUuid' in cmd.body

    @staticmethod
    def create_from(cmd: PersistentCommand) -> MailerCommand:
        return _MWRegistrationConfirmation(
            email=cmd.body['email'],
            user=CmdUser(
                user_uuid=cmd.body['userUuid'],
                first_name=cmd.body['userFirstName'],
                last_name=cmd.body['userLastName'],
                email=cmd.body['userEmail'],
            ),
            code=cmd.body['hash'],
            client_url=cmd.body['clientUrl'],
            app_uuid=cmd.app_uuid,
        )


class _MWQuestionnaireInvitation(MailerWizardCommand):

    FUNCTION_NAME = 'sendQuestionnaireInvitationMail'
    TEMPLATE_NAME = 'questionnaireInvitation'

    def __init__(self, email: str, invitee: CmdUser, owner: CmdUser,
                 project_uuid: str, project_name: str,
                 client_url: str, app_uuid: str):
        super().__init__(app_uuid=app_uuid)
        self.email = email
        self.invitee = invitee
        self.owner = owner
        self.project_uuid = project_uuid
        self.project_name = project_name
        self.client_url = client_url

    @property
    def project_link(self):
        return f'{self.client_url}/projects/{self.project_uuid}'

    def to_context(self) -> dict:
        ctx = {
            'invitee': self.invitee.to_context(),
            'owner': self.owner.to_context(),
            'project': {
                'uuid': self.project_uuid,
                'name': self.project_name,
                'link': self.project_link,
            },
            'clientUrl': self.client_url,
        }
        ctx.update(_app_config_to_context(self.app_config))
        return ctx

    def to_request(self, msg_id: str, trigger: str) -> MessageRequest:
        return MessageRequest(
            message_id=msg_id,
            template_name=self.TEMPLATE_NAME,
            trigger=trigger,
            ctx=self.to_context(),
            recipients=[self.email],
        )

    @staticmethod
    def create_from(cmd: PersistentCommand) -> MailerCommand:
        return _MWQuestionnaireInvitation(
            email=cmd.body['email'],
            invitee=CmdUser(
                user_uuid=cmd.body['inviteeUuid'],
                first_name=cmd.body['inviteeFirstName'],
                last_name=cmd.body['inviteeLastName'],
                email=cmd.body['inviteeEmail'],
            ),
            owner=CmdUser(
                user_uuid=cmd.body['ownerUuid'],
                first_name=cmd.body['ownerFirstName'],
                last_name=cmd.body['ownerLastName'],
                email=cmd.body['ownerEmail'],
            ),
            project_uuid=cmd.body['questionnaireUuid'],
            project_name=cmd.body['questionnaireName'],
            client_url=cmd.body['clientUrl'],
            app_uuid=cmd.app_uuid,
        )


class _MWRegistrationCreatedAnalytics(MailerWizardCommand):

    FUNCTION_NAME = 'sendRegistrationCreatedAnalyticsMail'
    TEMPLATE_NAME = 'registrationCreatedAnalytics'

    def __init__(self, email: str, user: CmdUser, client_url: str, app_uuid: str):
        super().__init__(app_uuid=app_uuid)
        self.email = email
        self.user = user
        self.client_url = client_url

    def to_context(self) -> dict:
        ctx = {
            'user': self.user.to_context(),
            'clientUrl': self.client_url,
        }
        ctx.update(_app_config_to_context(self.app_config))
        return ctx

    def to_request(self, msg_id: str, trigger: str) -> MessageRequest:
        return MessageRequest(
            message_id=msg_id,
            template_name=self.TEMPLATE_NAME,
            trigger=trigger,
            ctx=self.to_context(),
            recipients=[self.email],
        )

    @classmethod
    def corresponds(cls, cmd: PersistentCommand) -> bool:
        return cls.FUNCTION_NAME == cmd.function and 'userUuid' in cmd.body

    @staticmethod
    def create_from(cmd: PersistentCommand) -> MailerCommand:
        return _MWRegistrationCreatedAnalytics(
            email=cmd.body['email'],
            user=CmdUser(
                user_uuid=cmd.body['userUuid'],
                first_name=cmd.body['userFirstName'],
                last_name=cmd.body['userLastName'],
                email=cmd.body['userEmail'],
            ),
            client_url=cmd.body['clientUrl'],
            app_uuid=cmd.app_uuid,
        )


class _MWResetPassword(MailerWizardCommand):

    FUNCTION_NAME = 'sendResetPasswordMail'
    TEMPLATE_NAME = 'resetPassword'

    def __init__(self, email: str, user: CmdUser, code: str,
                 client_url: str, app_uuid: str):
        super().__init__(app_uuid=app_uuid)
        self.email = email
        self.user = user
        self.code = code
        self.client_url = client_url

    @property
    def reset_link(self):
        return f'{self.client_url}/forgotten-password/{self.user.uuid}/{self.code}'

    def to_context(self) -> dict:
        ctx = {
            'user': self.user.to_context(),
            'resetLink': self.reset_link,
            'clientUrl': self.client_url,
            'hash': self.code,
        }
        ctx.update(_app_config_to_context(self.app_config))
        return ctx

    def to_request(self, msg_id: str, trigger: str) -> MessageRequest:
        return MessageRequest(
            message_id=msg_id,
            template_name=self.TEMPLATE_NAME,
            trigger=trigger,
            ctx=self.to_context(),
            recipients=[self.email],
        )

    @staticmethod
    def create_from(cmd: PersistentCommand) -> MailerCommand:
        return _MWResetPassword(
            email=cmd.body['email'],
            user=CmdUser(
                user_uuid=cmd.body['userUuid'],
                first_name=cmd.body['userFirstName'],
                last_name=cmd.body['userLastName'],
                email=cmd.body['userEmail'],
            ),
            code=cmd.body['hash'],
            client_url=cmd.body['clientUrl'],
            app_uuid=cmd.app_uuid,
        )


class _MWTwoFactorAuth(MailerWizardCommand):

    FUNCTION_NAME = 'sendTwoFactorAuthMail'
    TEMPLATE_NAME = 'twoFactorAuth'

    def __init__(self, email: str, user: CmdUser, code: str,
                 client_url: str, app_uuid: str):
        super().__init__(app_uuid=app_uuid)
        self.email = email
        self.user = user
        self.code = code
        self.client_url = client_url

    def to_context(self) -> dict:
        ctx = {
            'user': self.user.to_context(),
            'code': self.code,
            'clientUrl': self.client_url,
        }
        ctx.update(_app_config_to_context(self.app_config))
        return ctx

    def to_request(self, msg_id: str, trigger: str) -> MessageRequest:
        return MessageRequest(
            message_id=msg_id,
            template_name=self.TEMPLATE_NAME,
            trigger=trigger,
            ctx=self.to_context(),
            recipients=[self.email],
        )

    @staticmethod
    def create_from(cmd: PersistentCommand) -> MailerCommand:
        return _MWTwoFactorAuth(
            email=cmd.body['email'],
            user=CmdUser(
                user_uuid=cmd.body['userUuid'],
                first_name=cmd.body['userFirstName'],
                last_name=cmd.body['userLastName'],
                email=cmd.body['userEmail'],
            ),
            code=cmd.body['code'],
            client_url=cmd.body['clientUrl'],
            app_uuid=cmd.app_uuid,
        )


class _MRRegistrationConfirmation(MailerCommand):

    FUNCTION_NAME = 'sendRegistrationConfirmationMail'
    TEMPLATE_NAME = 'registrationConfirmation'

    def __init__(self, email: str, org: CmdOrg, code: str,
                 client_url: str, callback_url: Optional[str]):
        self.email = email
        self.org = org
        self.code = code
        self.client_url = client_url
        self.callback_url = callback_url

    @property
    def registry_link(self) -> str:
        return f'{self.client_url}/signup/{self.org.id}/{self.code}'

    @property
    def callback_link(self) -> Optional[str]:
        if self.callback_url is None:
            return None
        return f'{self.callback_url}/registry/signup/{self.org.id}/{self.code}'

    @property
    def activation_link(self) -> Optional[str]:
        if self.callback_url is None:
            return self.registry_link
        return self.callback_link

    def to_context(self) -> dict:
        return {
            'organization': self.org.to_context(),
            'hash': self.code,
            'registryLink': self.registry_link,
            'callbackLink': self.callback_link,
            'activationLink': self.activation_link,
            'clientUrl': self.client_url,
        }

    def to_request(self, msg_id: str, trigger: str) -> MessageRequest:
        return MessageRequest(
            message_id=msg_id,
            template_name=self.TEMPLATE_NAME,
            trigger=trigger,
            ctx=self.to_context(),
            recipients=[self.email],
        )

    @classmethod
    def corresponds(cls, cmd: PersistentCommand) -> bool:
        return cls.FUNCTION_NAME == cmd.function and 'organizationId' in cmd.body

    @staticmethod
    def create_from(cmd: PersistentCommand) -> MailerCommand:
        return _MRRegistrationConfirmation(
            email=cmd.body['email'],
            org=CmdOrg(
                org_id=cmd.body['organizationId'],
                name=cmd.body['organizationName'],
                email=cmd.body['organizationEmail'],
            ),
            code=cmd.body['hash'],
            client_url=cmd.body['clientUrl'],
            callback_url=cmd.body.get('callbackUrl', None),
        )


class _MRRegistrationCreatedAnalytics(MailerCommand):

    FUNCTION_NAME = 'sendRegistrationCreatedAnalyticsMail'
    TEMPLATE_NAME = 'registrationCreatedAnalytics'

    def __init__(self, email: str, org: CmdOrg, client_url: str):
        self.email = email
        self.org = org
        self.client_url = client_url

    def to_context(self) -> dict:
        return {
            'organization': self.org.to_context(),
            'clientUrl': self.client_url,
        }

    def to_request(self, msg_id: str, trigger: str) -> MessageRequest:
        return MessageRequest(
            message_id=msg_id,
            template_name=self.TEMPLATE_NAME,
            trigger=trigger,
            ctx=self.to_context(),
            recipients=[self.email],
        )

    @classmethod
    def corresponds(cls, cmd: PersistentCommand) -> bool:
        return cls.FUNCTION_NAME == cmd.function and 'organizationId' in cmd.body

    @staticmethod
    def create_from(cmd: PersistentCommand) -> MailerCommand:
        return _MRRegistrationCreatedAnalytics(
            email=cmd.body['email'],
            org=CmdOrg(
                org_id=cmd.body['organizationId'],
                name=cmd.body['organizationName'],
                email=cmd.body['organizationEmail'],
            ),
            client_url=cmd.body['clientUrl'],
        )


class _MRResetToken(MailerCommand):

    FUNCTION_NAME = 'sendResetTokenMail'
    TEMPLATE_NAME = 'resetToken'

    def __init__(self, email: str, org: CmdOrg, code: str, client_url: str):
        self.email = email
        self.org = org
        self.code = code
        self.client_url = client_url

    @property
    def reset_link(self):
        return f'{self.client_url}/forgotten-token/{self.org.id}/{self.code}'

    def to_context(self) -> dict:
        return {
            'organization': self.org.to_context(),
            'resetLink': self.reset_link,
            'hash': self.code,
            'clientUrl': self.client_url,
        }

    def to_request(self, msg_id: str, trigger: str) -> MessageRequest:
        return MessageRequest(
            message_id=msg_id,
            template_name=self.TEMPLATE_NAME,
            trigger=trigger,
            ctx=self.to_context(),
            recipients=[self.email],
        )

    @staticmethod
    def create_from(cmd: PersistentCommand) -> MailerCommand:
        return _MRResetToken(
            email=cmd.body['email'],
            org=CmdOrg(
                org_id=cmd.body['organizationId'],
                name=cmd.body['organizationName'],
                email=cmd.body['organizationEmail'],
            ),
            code=cmd.body['hash'],
            client_url=cmd.body['clientUrl'],
        )


_MAILER_COMMANDS = [
    _MWRegistrationConfirmation,
    _MWResetPassword,
    _MWQuestionnaireInvitation,
    _MWRegistrationCreatedAnalytics,
    _MWTwoFactorAuth,
    _MRRegistrationConfirmation,
    _MRResetToken,
    _MRRegistrationCreatedAnalytics,
]


def load_mailer_command(cmd: PersistentCommand) -> MailerCommand:
    if cmd.component != CMD_COMPONENT:
        raise RuntimeError('Tried to process non-mailer command')
    for CMD_TYPE in _MAILER_COMMANDS:
        if issubclass(CMD_TYPE, MailerCommand) and CMD_TYPE.corresponds(cmd):
            try:
                return CMD_TYPE.create_from(cmd)
            except KeyError as e:
                raise RuntimeError(f'Cannot parse command: {str(e)}')
    raise RuntimeError('Cannot process such command')
