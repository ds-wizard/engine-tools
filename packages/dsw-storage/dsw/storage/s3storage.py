from __future__ import annotations

import logging
import typing

import boto3
import botocore.client
import botocore.exceptions
import tenacity


if typing.TYPE_CHECKING:
    from pathlib import Path

    from dsw.config.model import S3Config


LOG = logging.getLogger(__name__)

DOCUMENTS_DIR = 'documents'

RETRY_S3_MULTIPLIER = 0.5
RETRY_S3_TRIES = 3

_NOT_FOUND_CODES = frozenset({'NoSuchKey', 'NoSuchBucket', '404'})


class S3Storage:

    def __init__(self, *, cfg: S3Config, multi_tenant: bool):
        self.cfg = cfg
        self.multi_tenant = multi_tenant
        self.client = boto3.client(
            's3',
            endpoint_url=self.cfg.url,
            aws_access_key_id=self.cfg.username,
            aws_secret_access_key=self.cfg.password,
            region_name=self.cfg.region,
            config=botocore.client.Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'},
            ),
        )

    @property
    def identification(self) -> str:
        return f'{self.cfg.url}/{self.cfg.bucket}'

    def _bucket_exists(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.cfg.bucket)
        except botocore.exceptions.ClientError as e:
            if e.response.get('Error', {}).get('Code') in _NOT_FOUND_CODES:
                return False
            raise
        return True

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def ensure_bucket(self):
        if self._bucket_exists():
            return
        kwargs: dict = {'Bucket': self.cfg.bucket}
        # AWS S3 requires an explicit LocationConstraint for any region other
        # than us-east-1; S3-compatible servers (e.g. MinIO) are region-agnostic
        # and can reject a constraint that doesn't match their configured region.
        is_aws = 'amazonaws.com' in self.cfg.url
        if is_aws and self.cfg.region and self.cfg.region != 'us-east-1':
            kwargs['CreateBucketConfiguration'] = {
                'LocationConstraint': self.cfg.region,
            }
        self.client.create_bucket(**kwargs)

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def store_document(self, *, tenant_uuid: str, file_name: str,
                       content_type: str, data: bytes,
                       metadata: dict | None = None):
        object_name = f'{DOCUMENTS_DIR}/{file_name}'
        if self.multi_tenant:
            object_name = f'{tenant_uuid}/{object_name}'
        self._put_object(
            object_name=object_name,
            content_type=content_type,
            data=data,
            metadata=metadata,
        )

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def download_project_file(self, *, tenant_uuid: str, project_uuid: str,
                              file_uuid: str, target_path: Path) -> bool:
        return self._download_file(
            tenant_uuid=tenant_uuid,
            file_name=f'project-files/{project_uuid}/{file_uuid}',
            target_path=target_path,
        )

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def download_template_asset(self, *, tenant_uuid: str, template_uuid: str,
                                file_name: str, target_path: Path) -> bool:
        return self._download_file(
            tenant_uuid=tenant_uuid,
            file_name=f'document-templates/{template_uuid}/{file_name}',
            target_path=target_path,
        )

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def download_mail_templates(self, *, tenant_uuid: str, target_path: Path) -> bool:
        return self._download_file(
            tenant_uuid=tenant_uuid,
            file_name='mail-templates.zip',
            target_path=target_path,
        )

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def download_locale(self, *, tenant_uuid: str, locale_uuid: str,
                        file_name: str, target_path: Path) -> bool:
        return self._download_file(
            tenant_uuid=tenant_uuid,
            file_name=f'locales/{locale_uuid}/{file_name}',
            target_path=target_path,
        )

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def _download_file(self, *, tenant_uuid: str, file_name: str,
                       target_path: Path) -> bool:
        if self.multi_tenant:
            file_name = f'{tenant_uuid}/{file_name}'
        try:
            self.client.download_file(
                Bucket=self.cfg.bucket,
                Key=file_name,
                Filename=str(target_path),
            )
        except botocore.exceptions.ClientError as e:
            if e.response.get('Error', {}).get('Code') in _NOT_FOUND_CODES:
                return False
            raise
        return True

    @tenacity.retry(
        reraise=True,
        wait=tenacity.wait_exponential(multiplier=RETRY_S3_MULTIPLIER),
        stop=tenacity.stop_after_attempt(RETRY_S3_TRIES),
        before=tenacity.before_log(LOG, logging.DEBUG),
        after=tenacity.after_log(LOG, logging.DEBUG),
    )
    def store_object(self, *, tenant_uuid: str, object_name: str,
                     content_type: str, data: bytes,
                     metadata: dict | None = None):
        if self.multi_tenant:
            object_name = f'{tenant_uuid}/{object_name}'
        self._put_object(
            object_name=object_name,
            content_type=content_type,
            data=data,
            metadata=metadata,
        )

    def _put_object(self, *, object_name: str, content_type: str,
                    data: bytes, metadata: dict | None):
        kwargs: dict = {
            'Bucket': self.cfg.bucket,
            'Key': object_name,
            'Body': data,
            'ContentType': content_type,
        }
        if metadata:
            kwargs['Metadata'] = {str(k): str(v) for k, v in metadata.items()}
        self.client.put_object(**kwargs)

    def make_path(self, fragments: list[str], tenant_uuid: str) -> str:
        lst = []
        if self.multi_tenant:
            lst.append(tenant_uuid)
        lst.extend(fragments)
        return '/'.join(lst)
