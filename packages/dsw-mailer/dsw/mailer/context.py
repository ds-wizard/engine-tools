import pathlib

from typing import Optional, TYPE_CHECKING

from .templates import TemplateRegistry

if TYPE_CHECKING:
    from .config import MailerConfig
    from .connection import SMTPSender
    from dsw.database import Database


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
                 templates: TemplateRegistry):
        self.app = app
        self.job = job
        self.templates = templates

    def update_trace_id(self, trace_id: str):
        self.app.cfg.log.set_logging_extra('traceId', trace_id)
        self.job.trace_id = trace_id

    def reset_ids(self):
        self.update_trace_id('-')


class Context:

    _instance = None  # type: Optional[_Context]

    @classmethod
    def get(cls) -> _Context:
        if cls._instance is None:
            raise ContextNotInitializedError()
        return cls._instance

    @classmethod
    def initialize(cls, db, config, sender, workdir):
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
            ),
        )
