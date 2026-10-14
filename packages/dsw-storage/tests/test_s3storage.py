import pathlib

import pytest
from botocore.stub import ANY, Stubber

from dsw.config.model import S3Config
from dsw.storage import ObjectInfo, S3Storage


TENANT = '11111111-0000-0000-0000-000000000001'
LOCALE = '22222222-0000-0000-0000-000000000001'


def make_storage(*, multi_tenant: bool) -> S3Storage:
    return S3Storage(cfg=S3Config(url='http://s3.example.org', username='key', password='secret',
                                  bucket='wizard', region='eu-central-1'),
                     multi_tenant=multi_tenant)


@pytest.fixture
def storage() -> S3Storage:
    return make_storage(multi_tenant=True)


def test_store_mail_template_locale_is_tenant_prefixed(storage: S3Storage):
    with Stubber(storage.client) as stub:
        stub.add_response('put_object', {}, {
            'Bucket': 'wizard', 'Key': f'{TENANT}/mail-template-locales/{LOCALE}/mail.mo',
            'Body': b'mo', 'ContentType': 'application/octet-stream',
        })
        storage.store_mail_template_locale(tenant_uuid=TENANT, locale_uuid=LOCALE,
                                           file_name='mail.mo',
                                           content_type='application/octet-stream', data=b'mo')
        stub.assert_no_pending_responses()


def test_download_missing_mail_template_locale(storage: S3Storage, tmp_path: pathlib.Path):
    with Stubber(storage.client) as stub:
        stub.add_client_error('head_object', service_error_code='404', http_status_code=404,
                              expected_params={
                                  'Bucket': 'wizard',
                                  'Key': f'{TENANT}/mail-template-locales/{LOCALE}/mail.mo',
                              })
        assert not storage.download_mail_template_locale(
            tenant_uuid=TENANT, locale_uuid=LOCALE, file_name='mail.mo',
            target_path=tmp_path / 'mail.mo')


@pytest.mark.parametrize('multi_tenant', [True, False])
def test_instance_objects_are_never_prefixed(multi_tenant: bool):
    storage = make_storage(multi_tenant=multi_tenant)
    with Stubber(storage.client) as stub:
        stub.add_response('head_object', {'ETag': '"abc123"', 'Metadata': {'version': '5.0.0'}},
                          {'Bucket': 'wizard', 'Key': 'mail-templates/mail.pot'})
        stub.add_response('put_object', {}, {
            'Bucket': 'wizard', 'Key': 'mail-templates/mail.pot', 'Body': b'pot',
            'ContentType': 'text/x-gettext-translation', 'Metadata': {'version': '5.0.1'},
        })
        assert storage.head_instance_object(object_name='mail-templates/mail.pot') == \
            ObjectInfo(metadata={'version': '5.0.0'}, etag='abc123')
        storage.store_instance_object(object_name='mail-templates/mail.pot',
                                      content_type='text/x-gettext-translation', data=b'pot',
                                      metadata={'version': '5.0.1'})
        stub.assert_no_pending_responses()


def test_head_missing_instance_object(storage: S3Storage):
    with Stubber(storage.client) as stub:
        stub.add_client_error('head_object', service_error_code='404', http_status_code=404,
                              expected_params={'Bucket': 'wizard', 'Key': ANY})
        assert storage.head_instance_object(object_name='mail-templates/mail.pot') is None
