import io
import logging

import minio  # type: ignore
import tenacity

from ..config import S3Config
from ..context import Context

S3_SERVICE_NAME = 's3'

RETRY_S3_MULTIPLIER = 0.5
RETRY_S3_TRIES = 3


class S3Storage:

    @staticmethod
    def _get_endpoint(url: str):
        parts = url.split('://', maxsplit=1)
        return parts[0] if len(parts) == 1 else parts[1]

    def __init__(self, cfg: S3Config):
        self.cfg = cfg
        endpoint = self._get_endpoint(self.cfg.url)
        self.client = minio.Minio(
            endpoint=endpoint,
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
        before=tenacity.before_log(Context.logger, logging.DEBUG),
        after=tenacity.after_log(Context.logger, logging.DEBUG),
    )
    def store_object(self, app_uuid: str, object_name: str,
                     content_type: str, data: bytes):
        if Context.get().app.cfg.cloud.multi_tenant:
            object_name = f'{app_uuid}/{object_name}'
        with io.BytesIO(data) as file:
            self.client.put_object(
                bucket_name=self.cfg.bucket,
                object_name=object_name,
                data=file,
                length=len(data),
                content_type=content_type,
            )
