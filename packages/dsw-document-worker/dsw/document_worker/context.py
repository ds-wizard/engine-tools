import dataclasses
import pathlib

import pluggy

from dsw.database import Database
from dsw.storage import S3Storage

from .config import DocumentWorkerConfig


class ContextNotInitializedError(RuntimeError):

    def __init__(self):
        super().__init__('Context cannot be retrieved, not initialized')


@dataclasses.dataclass
class AppContext:
    pm: pluggy.PluginManager
    db: Database
    s3: S3Storage
    cfg: DocumentWorkerConfig
    workdir: pathlib.Path


@dataclasses.dataclass
class JobContext:
    trace_id: str


class _Context:

    def __init__(self, app: AppContext, job: JobContext):
        self.app = app
        self.job = job
        self.tenant_uuid = ''

    def update_trace_id(self, trace_id: str):
        self.app.cfg.log.set_logging_extra('traceId', trace_id)
        self.job.trace_id = trace_id

    def update_document_id(self, document_id: str):
        self.app.cfg.log.set_logging_extra('documentId', document_id)

    def reset_ids(self):
        self.update_trace_id('-')
        self.update_document_id('-')


class Context:

    _instance: _Context | None = None

    @classmethod
    def get(cls) -> _Context:
        if cls._instance is None:
            raise ContextNotInitializedError
        return cls._instance

    @classmethod
    def initialize(cls, db, s3, config, workdir):
        # pylint: disable-next=import-outside-toplevel
        from .plugins.manager import create_manager
        cls._instance = _Context(
            app=AppContext(
                pm=create_manager(),
                db=db,
                s3=s3,
                cfg=config,
                workdir=workdir,
            ),
            job=JobContext(
                trace_id='-',
            ),
        )
