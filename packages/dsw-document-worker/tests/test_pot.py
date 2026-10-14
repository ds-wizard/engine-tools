import types

import pytest

from dsw.command_queue import CommandJobError
from dsw.document_worker.pot import PotFileRequest


def make_command(**body):
    return types.SimpleNamespace(
        uuid='11111111-1111-1111-1111-111111111111',
        tenant_uuid='22222222-2222-2222-2222-222222222222',
        function='generatePotFile',
        body=body,
    )


def test_request_load_ok():
    rq = PotFileRequest.load(make_command(
        documentTemplateUuid='33333333-3333-3333-3333-333333333333',
        id='org.tid',
        version='1.0.0',
        language='cs',
    ))
    assert rq.coordinates == 'org.tid:1.0.0'
    # the name the backend reads: DocumentTemplateS3.potFileName
    assert rq.file_name == 'org.tid_1.0.0.pot'
    assert rq.language == 'cs'


def test_request_load_pre_5_0_body():
    # queued by a backend before the upgrade; the migration gave the template the joined id
    rq = PotFileRequest.load(make_command(
        documentTemplateUuid='33333333-3333-3333-3333-333333333333',
        organizationId='org',
        templateId='tid',
        version='1.0.0',
        language='en',
    ))
    assert rq.coordinates == 'org.tid:1.0.0'
    assert rq.file_name == 'org.tid_1.0.0.pot'


def test_request_load_without_language():
    rq = PotFileRequest.load(make_command(
        documentTemplateUuid='33333333-3333-3333-3333-333333333333',
        id='org.tid',
        version='1.0.0',
        language=None,
    ))
    assert rq.language == 'en'


def test_request_load_rejects_bad_uuid():
    with pytest.raises(CommandJobError) as e:
        PotFileRequest.load(make_command(
            documentTemplateUuid='not-a-uuid',
            id='org.tid',
            version='1.0.0',
        ))
    assert not e.value.try_again


@pytest.mark.parametrize('field', ['id', 'version'])
def test_request_load_rejects_traversal(field):
    body = {
        'documentTemplateUuid': '33333333-3333-3333-3333-333333333333',
        'id': 'org.tid',
        'version': '1.0.0',
    }
    body[field] = '../../etc/passwd'
    with pytest.raises(CommandJobError, match=f'Invalid value of "{field}"') as e:
        PotFileRequest.load(make_command(**body))
    assert not e.value.try_again


@pytest.mark.parametrize('field', ['organizationId', 'templateId'])
def test_request_load_rejects_traversal_in_pre_5_0_body(field):
    body = {
        'documentTemplateUuid': '33333333-3333-3333-3333-333333333333',
        'organizationId': 'org',
        'templateId': 'tid',
        'version': '1.0.0',
    }
    body[field] = '../../etc/passwd'
    with pytest.raises(CommandJobError, match='Invalid value of "id"'):
        PotFileRequest.load(make_command(**body))


def test_request_load_requires_id():
    with pytest.raises(CommandJobError, match='Invalid value of "id"'):
        PotFileRequest.load(make_command(
            documentTemplateUuid='33333333-3333-3333-3333-333333333333', version='1.0.0'))
