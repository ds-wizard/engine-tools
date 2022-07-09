import pathlib

from typing import Optional, TYPE_CHECKING

from .logging import LOGGER
from .templates import TemplateRegistry

if TYPE_CHECKING:
    from .config import MailerConfig
    from .connection import Database, SMTPSender


class ContextNotInitializedError(RuntimeError):

    def __init__(self):
        super().__init__('Context cannot be retrieved, not initialized')


class AppContext:

    def __init__(self, db, cfg, sender, workdir):
        self.db = db  # type: Database
        self.cfg = cfg  # type: MailerConfig
        self.sender = sender  # type: SMTPSender
        self.workdir = workdir  # type: pathlib.Path


class JobContext:

    def __init__(self, trace_id: str):
        self.trace_id = trace_id


class _Context:

    def __init__(self, app: AppContext, job: JobContext,
                 templates: TemplateRegistry, mode: str):
        self.app = app
        self.job = job
        self.templates = templates
        self.mode = mode


class Context:

    _instance = None  # type: Optional[_Context]
    logger = LOGGER

    @classmethod
    def get(cls) -> _Context:
        if cls._instance is None:
            raise ContextNotInitializedError()
        return cls._instance

    @classmethod
    def update_trace_id(cls, trace_id: str):
        cls.logger.trace_id = trace_id
        cls.get().job.trace_id = trace_id

    @classmethod
    def update_document_id(cls, document_id: str):
        cls.logger.document_id = document_id

    @classmethod
    def reset(cls):
        cls.update_trace_id('-')
        cls.update_document_id('-')

    @classmethod
    def is_registry_mode(cls):
        return cls.get().mode == 'registry'

    @classmethod
    def is_wizard_mode(cls):
        return cls.get().mode == 'wizard'

    @classmethod
    def initialize(cls, db, config, sender, workdir, mode):
        cls._instance = _Context(
            app=AppContext(
                db=db,
                cfg=config,
                workdir=workdir,
                sender=sender,
            ),
            job=JobContext(
                trace_id='-',
            ),
            templates=TemplateRegistry(
                cfg=config,
                workdir=workdir,
                mode=mode,
            ),
            mode=mode,
        )
        if cls.get().app.cfg.mail.name == '':
            if cls.is_registry_mode():
                cls.get().app.cfg.mail.name = 'DSW Registry'
            elif cls.is_wizard_mode():
                cls.get().app.cfg.mail.name = 'DSW'
