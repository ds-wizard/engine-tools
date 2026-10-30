from __future__ import annotations

from dsw.templating.utils import byte_size_format

from .context import Context
from .exceptions import JobError


# Key of the generateDocument command body with the tenant limits resolved by
# the backend, e.g. {"storage": 3000000}; without it (or with a null storage)
# there is no storage limit. It is not part of the document context, so it is
# removed before rendering and never reaches templates
COMMAND_LIMITS_KEY = 'limits'


class LimitsEnforcer:

    @staticmethod
    def take_storage_limit(doc_context: dict) -> int | None:
        limits = doc_context.pop(COMMAND_LIMITS_KEY, None)
        if not isinstance(limits, dict):
            return None
        return limits.get('storage')

    @staticmethod
    def check_doc_size(job_id: str, doc_size: int):
        max_size = Context.get().app.cfg.doc.max_size
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
