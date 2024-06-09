from .context import Context
from .exceptions import JobException
from .utils import byte_size_format

from typing import Optional


class LimitsEnforcer:

    @staticmethod
    def check_doc_size(job_id: str, doc_size: int):
        max_size = Context.get().app.cfg.experimental.max_doc_size
        if max_size is None or doc_size <= max_size:
            return
        raise JobException(
            job_id=job_id,
            msg=f'Document exceeded size limit ({byte_size_format(max_size)}): '
                f'{byte_size_format(doc_size)}.'
        )

    @staticmethod
    def check_size_usage(job_id: str, doc_size: int,
                         used_size: int, limit_size: Optional[int]):
        if limit_size is None or doc_size + used_size < limit_size:
            return
        remains = limit_size - used_size
        raise JobException(
            job_id=job_id,
            msg=f'No space left for this document: '
                f'required {byte_size_format(doc_size)} but '
                f'only {byte_size_format(remains)} remains.'
        )

    @staticmethod
    def timeout_exceeded(job_id: str):
        job_timeout = Context.get().app.cfg.experimental.job_timeout
        if job_timeout is None:
            return
        raise JobException(
            job_id=job_id,
            msg=f'Document generation exceeded time limit '
                f'({job_timeout} seconds).'
        )
