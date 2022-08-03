import pathlib

from typing import Optional, TYPE_CHECKING

from .logging import LOGGER

if TYPE_CHECKING:
    from .config import DocumentWorkerConfig
    from dsw.database import Database
    from dsw.storage import S3Storage


class ContextNotInitializedError(RuntimeError):

    def __init__(self):
        super().__init__('Context cannot be retrieved, not initialized')


class AppContext:

    def __init__(self, db, s3, cfg, workdir):
        self.db = db  # type: Database
        self.s3 = s3  # type: S3Storage
        self.cfg = cfg  # type: DocumentWorkerConfig
        self.workdir = workdir  # type: pathlib.Path


class JobContext:

    def __init__(self, trace_id: str):
        self.trace_id = trace_id


class _Context:

    def __init__(self, app: AppContext, job: JobContext):
        self.app = app
        self.job = job


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
