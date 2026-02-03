class JobError(Exception):

    def __init__(self, job_id: str, msg: str, exc=None,
                 skip_reporting: bool = False):
        self.job_id = job_id
        self.msg = msg
        self.exc = exc
        self.skip_reporting = skip_reporting

    def __str__(self):
        return self.msg

    def log_message(self):
        if self.exc is None:
            return self.msg
        return f'{self.msg}: [{type(self.exc).__name__}] {str(self.exc)}'

    def db_message(self):
        if self.exc is None:
            return self.msg
        return f'{self.msg}\n\n' \
               f'Caused by: {type(self.exc).__name__}\n' \
               f'{str(self.exc)}'


class DocumentNotFoundError(JobError):
    pass


def create_job_error(job_id: str, message: str, document_found=True, exc=None):
    if not document_found:
        return DocumentNotFoundError(
            job_id=job_id,
            msg=message,
            exc=exc,
        )

    if isinstance(exc, JobError):
        return exc

    return JobError(
        job_id=job_id,
        msg=message,
        exc=exc,
    )
