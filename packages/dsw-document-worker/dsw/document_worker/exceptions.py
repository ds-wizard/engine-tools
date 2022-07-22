class JobException(Exception):

    def __init__(self, job_id: str, msg: str, exc=None):
        self.job_id = job_id
        self.msg = msg
        self.exc = exc

    def log_message(self):
        if self.exc is None:
            return self.msg
        else:
            return f'{self.msg}: [{type(self.exc).__name__}] {str(self.exc)}'

    def db_message(self):
        if self.exc is None:
            return self.msg
        return f'{self.msg}\n\n' \
               f'Caused by: {type(self.exc).__name__}\n' \
               f'{str(self.exc)}'


def create_job_exception(job_id: str, message: str, exc=None):
    if isinstance(exc, JobException):
        return exc

    return JobException(
        job_id=job_id,
        msg=message,
        exc=exc,
    )
