import contextlib
import io
import logging
import minio  # type: ignore
import minio.error  # type: ignore
import pathlib
import tempfile
import tenacity

from dsw.config.model import S3Config

LOG = logging.getLogger(__name__)

DOCUMENTS_DIR = 'documents'

RETRY_S3_MULTIPLIER = 0.5
RETRY_S3_TRIES = 3


@contextlib.contextmanager
def temp_binary_file(data: bytes):
    file = tempfile.TemporaryFile()
    file.write(data)
    file.seek(0)
    yield file
    file.close()


class S3Storage:

    @staticmethod
    def _get_endpoint(url: str):
        parts = url.split('://', maxsplit=1)
        return parts[0] if len(parts) == 1 else parts[1]

    def __init__(self, cfg: S3Config, multi_tenant: bool):
        self.cfg = cfg
        self.multi_tenant = multi_tenant
        self.client = minio.Minio(
            endpoint=self._get_endpoint(self.cfg.url),
            access_key=self.cfg.username,
            secret_key=self.cfg.password,
            secure=self.cfg.url.startswith('https://'),
            region=self.cfg.region,
        )

    @property
    def identification(self) -> str:
        return f'{self.cfg.url}/{self.cfg.bucket}'

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def ensure_bucket(self):
        found = self.client.bucket_exists(self.cfg.bucket)
        if not found:
            self.client.make_bucket(self.cfg.bucket)

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def store_document(self, app_uuid: str, file_name: str,
                       content_type: str, data: bytes):
        object_name = f'{DOCUMENTS_DIR}/{file_name}'
        if self.multi_tenant:
            object_name = f'{app_uuid}/{object_name}'
        with temp_binary_file(data=data) as file:
            self.client.put_object(
                bucket_name=self.cfg.bucket,
                object_name=object_name,
                data=file,
                length=len(data),
                content_type=content_type,
            )

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def download_file(self, file_name: str, target_path: pathlib.Path) -> bool:
        try:
            self.client.fget_object(
                bucket_name=self.cfg.bucket,
                object_name=file_name,
                file_path=str(target_path),
            )
        except minio.error.S3Error as e:
            if e.code != 'NoSuchKey':
                raise e
            return False
        return True

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def store_object(self, app_uuid: str, object_name: str,
                     content_type: str, data: bytes):
        if self.multi_tenant:
            object_name = f'{app_uuid}/{object_name}'
        with io.BytesIO(data) as file:
            self.client.put_object(
                bucket_name=self.cfg.bucket,
                object_name=object_name,
                data=file,
                length=len(data),
                content_type=content_type,
            )
