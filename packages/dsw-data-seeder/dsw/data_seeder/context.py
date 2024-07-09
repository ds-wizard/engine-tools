import dataclasses
import pathlib

from dsw.database import Database
from dsw.storage import S3Storage

from .config import SeederConfig


class ContextNotInitializedError(RuntimeError):

    def __init__(self):
        super().__init__('Context cannot be retrieved, not initialized')


@dataclasses.dataclass
class AppContext:
    db: Database
    s3: S3Storage
    cfg: SeederConfig
    workdir: pathlib.Path


@dataclasses.dataclass
class JobContext:
    trace_id: str


class _Context:

    def __init__(self, app: AppContext, job: JobContext):
        self.app = app
        self.job = job

    def update_trace_id(self, trace_id: str):
        self.app.cfg.log.set_logging_extra('traceId', trace_id)
        self.job.trace_id = trace_id

    def update_item_id(self, item_id: str):
        self.app.cfg.log.set_logging_extra('itemId', item_id)

    def reset_ids(self):
        self.update_trace_id('-')
        self.update_item_id('-')


class Context:

    _instance: _Context | None = None

    @classmethod
    def get(cls) -> _Context:
        if cls._instance is None:
            raise ContextNotInitializedError()
        return cls._instance

    @classmethod
    def initialize(cls, db, s3, config, workdir):
        cls._instance = _Context(
            app=AppContext(
                db=db,
                s3=s3,
                cfg=config,
                workdir=workdir,
            ),
            job=JobContext(
                trace_id='-',
            )
        )
