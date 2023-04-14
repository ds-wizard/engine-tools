import pathlib

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import SeederConfig
    from dsw.database import Database
    from dsw.storage import S3Storage


class ContextNotInitializedError(RuntimeError):

    def __init__(self):
        super().__init__('Context cannot be retrieved, not initialized')


class AppContext:

    def __init__(self, db, s3, cfg, workdir):
        self.db = db  # type: Database
        self.s3 = s3  # type: S3Storage
        self.cfg = cfg  # type: SeederConfig
        self.workdir = workdir  # type: pathlib.Path


class JobContext:

    def __init__(self, trace_id: str):
        self.trace_id = trace_id


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

    _instance = None  # type: Optional[_Context]

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
