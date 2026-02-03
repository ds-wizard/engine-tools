from .context import Context
from .exceptions import JobError
from .utils import byte_size_format


class LimitsEnforcer:

    @staticmethod
    def check_doc_size(job_id: str, doc_size: int):
        max_size = Context.get().app.cfg.experimental.max_doc_size
        if max_size is None or doc_size <= max_size:
            return
        raise JobError(
            job_id=job_id,
            msg=f'Document exceeded size limit ({byte_size_format(max_size)}): '
                f'{byte_size_format(doc_size)}.',
        )

    @staticmethod
    def check_size_usage(job_id: str, doc_size: int,
                         used_size: int, limit_size: int | None):
        limit_size = abs(limit_size) if limit_size is not None else None

        if limit_size is None or doc_size + used_size < limit_size:
            return
        remains = limit_size - used_size
        raise JobError(
            job_id=job_id,
            msg=f'No space left for this document: '
                f'required {byte_size_format(doc_size)} but '
                f'only {byte_size_format(remains)} remains.',
        )
