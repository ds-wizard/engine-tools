"""Row mapping against rows shaped like the Wizard 5.0 schema."""
import datetime
import json
import uuid

from dsw.database.model import (
    DBDocument,
    DBDocumentTemplate,
    DBLocale,
    DBMailTemplateLocale,
    DBProjectSimple,
    DBSubmission,
    DocumentTemplatePhase,
)


NOW = datetime.datetime(2026, 10, 14, 12, 0, tzinfo=datetime.UTC)
TENANT = uuid.UUID('00000000-0000-0000-0000-0000000000aa')
WORKSPACE = uuid.UUID('00000000-0000-0000-0000-0000000000bb')


def document_row(**changes) -> dict:
    return {
        'uuid': uuid.UUID('00000000-0000-0000-0000-000000000001'), 'name': 'Doc',
        'state': 'QueuedDocumentState', 'durability': 'PersistentDocumentDurability',
        'project_uuid': uuid.UUID('00000000-0000-0000-0000-000000000002'),
        'project_event_uuid': None,
        'document_template_uuid': uuid.UUID('00000000-0000-0000-0000-000000000003'),
        'format_uuid': uuid.UUID('00000000-0000-0000-0000-000000000004'),
        'created_by': None, 'retrieved_at': None, 'finished_at': None, 'created_at': NOW,
        'file_name': None, 'content_type': None, 'worker_log': None, 'tenant_uuid': TENANT,
        'file_size': None, 'language': None, 'workspace_uuid': WORKSPACE,
        'context_hash': 'sha256:abc', 'knowledge_model_editor_uuid': None,
        **changes,
    }


def test_document():
    document = DBDocument.from_dict_row(document_row())
    assert document.project_uuid == '00000000-0000-0000-0000-000000000002'
    assert document.created_by is None  # used to be the string 'None'
    assert document.workspace_uuid == str(WORKSPACE)
    assert document.context_hash == 'sha256:abc'
    assert document.knowledge_model_editor_uuid is None


def test_km_editor_preview_document():
    editor = uuid.UUID('00000000-0000-0000-0000-000000000005')
    document = DBDocument.from_dict_row(document_row(project_uuid=None,
                                                     knowledge_model_editor_uuid=editor))
    assert document.project_uuid is None
    assert document.knowledge_model_editor_uuid == str(editor)


def template_row(**changes) -> dict:
    return {
        'uuid': uuid.UUID('00000000-0000-0000-0000-000000000003'), 'name': 'Report',
        'id': 'dsw.questionnaire-report', 'version': '2.4.0', 'metamodel_version': '(19,0)',
        'description': '', 'readme': '', 'license': 'Apache-2.0',
        'allowed_packages': [{'id': None, 'minVersion': None, 'maxVersion': None}],
        'created_at': NOW, 'updated_at': NOW, 'tenant_uuid': TENANT,
        'phase': 'ReleasedDocumentTemplatePhase', 'non_editable': False, 'language': 'en',
        'pot_file_ready': False, 'workspace_uuid': None,
        **changes,
    }


def test_document_template():
    template = DBDocumentTemplate.from_dict_row(template_row())
    assert template.id == 'dsw.questionnaire-report'
    assert template.coordinates == 'dsw.questionnaire-report:2.4.0'
    assert template.metamodel_version == '19.0'
    assert template.allowed_packages == [{'id': None, 'minVersion': None, 'maxVersion': None}]
    assert template.workspace_uuid is None


def test_document_template_phase():
    released = DBDocumentTemplate.from_dict_row(template_row())
    assert (released.is_released, released.is_draft, released.is_deprecated) == (True, False, False)
    draft = DBDocumentTemplate.from_dict_row(template_row(phase=DocumentTemplatePhase.DRAFT.value))
    assert (draft.is_released, draft.is_draft) == (False, True)


def test_document_template_workspace():
    template = DBDocumentTemplate.from_dict_row(template_row(workspace_uuid=WORKSPACE))
    assert template.workspace_uuid == str(WORKSPACE)


def project_row(**changes) -> dict:
    return {
        'uuid': uuid.UUID('00000000-0000-0000-0000-000000000002'), 'name': 'Project',
        'visibility': 'PrivateProjectVisibility', 'sharing': 'RestrictedProjectSharing',
        'knowledge_model_package_uuid': uuid.UUID('00000000-0000-0000-0000-000000000006'),
        'selected_question_tag_uuids': [], 'document_template_uuid': None, 'format_uuid': None,
        'created_by': None, 'created_at': NOW, 'updated_at': NOW, 'description': None,
        'is_template': False, 'squashed': True, 'tenant_uuid': TENANT, 'project_tags': [],
        'language': None, 'document_template_language': None, 'workspace_uuid': WORKSPACE,
        **changes,
    }


def test_project_simple():
    project = DBProjectSimple.from_dict_row(project_row())
    data = project.to_dict()
    # nullable references are null, not the string 'None'
    assert (data['document_template_uuid'], data['format_uuid'], data['created_by']) == (
        None, None, None)
    assert data['workspace_uuid'] == str(WORKSPACE)


def test_project_simple_extras_are_json():
    # extras.project goes into the context, which steps such as `json` serialize
    data = DBProjectSimple.from_dict_row(project_row(
        format_uuid=uuid.UUID('00000000-0000-0000-0000-000000000007'),
        created_by=uuid.UUID('00000000-0000-0000-0000-000000000008'))).to_dict()
    assert json.loads(json.dumps(data)) == data
    assert data['knowledge_model_package_uuid'] == '00000000-0000-0000-0000-000000000006'


def test_submission_extras_with_nullable_columns_are_json():
    data = DBSubmission.from_dict_row({
        'uuid': uuid.UUID('00000000-0000-0000-0000-000000000009'), 'state': 'DoneSubmissionState',
        'location': None, 'returned_data': None, 'service_id': 'repo', 'document_uuid': None,
        'created_by': None, 'created_at': None, 'updated_at': NOW, 'tenant_uuid': TENANT,
    }).to_dict()
    assert json.loads(json.dumps(data)) == data
    assert (data['document_uuid'], data['created_by'], data['created_at']) == (None, None, None)


def locale_row(**changes) -> dict:
    return {
        'uuid': uuid.UUID('00000000-0000-0000-0000-000000000009'), 'tenant_uuid': TENANT,
        'code': 'de', 'name': 'German', 'pot_version': 'fw-mail-templates:5.0.0',
        'enabled': True, 'default_locale': False, 'official': True,
        'created_at': NOW, 'updated_at': NOW, **changes,
    }


def test_locale_tables_share_the_shape():
    ui = DBLocale.from_dict_row(locale_row())
    mail = DBMailTemplateLocale.from_dict_row(locale_row(pot_version=None))
    assert (ui.uuid, ui.tenant_uuid, ui.code, ui.official) == \
        ('00000000-0000-0000-0000-000000000009', str(TENANT), 'de', True)
    assert isinstance(mail, DBMailTemplateLocale)
    assert mail.pot_version is None
    assert mail.updated_at == NOW
    assert (DBLocale.TABLE_NAME, DBMailTemplateLocale.TABLE_NAME) == \
        ('locale', 'mail_template_locale')
