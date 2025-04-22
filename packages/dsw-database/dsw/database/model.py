import dataclasses
import datetime
import enum
import json


NULL_UUID = '00000000-0000-0000-0000-000000000000'


class DocumentState(enum.Enum):
    QUEUED = 'QueuedDocumentState'
    PROCESSING = 'InProgressDocumentState'
    FAILED = 'ErrorDocumentState'
    FINISHED = 'DoneDocumentState'


class DocumentTemplatePhase(enum.Enum):
    RELEASED = 'ReleasedTemplatePhase'
    DEPRECATED = 'DeprecatedTemplatePhase'
    DRAFT = 'DraftTemplatePhase'


@dataclasses.dataclass
class DBComponent:
    name: str
    version: str
    built_at: datetime.datetime
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @staticmethod
    def from_dict_row(data: dict):
        return DBComponent(
            name=data['name'],
            version=data['version'],
            built_at=data['built_at'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
        )


@dataclasses.dataclass
class DBDocument:
    uuid: str
    name: str
    state: str
    durability: str
    questionnaire_uuid: str
    questionnaire_event_uuid: str
    questionnaire_replies_hash: str
    document_template_id: str
    format_uuid: str
    file_name: str
    content_type: str
    worker_log: str
    created_by: str
    retrieved_at: datetime.datetime | None
    finished_at: datetime.datetime | None
    created_at: datetime.datetime
    tenant_uuid: str
    file_size: int

    @staticmethod
    def from_dict_row(data: dict):
        return DBDocument(
            uuid=str(data['uuid']),
            name=data['name'],
            state=data['state'],
            durability=data['durability'],
            questionnaire_uuid=str(data['questionnaire_uuid']),
            questionnaire_event_uuid=str(data['questionnaire_event_uuid']),
            questionnaire_replies_hash=data['questionnaire_replies_hash'],
            document_template_id=data['document_template_id'],
            format_uuid=str(data['format_uuid']),
            created_by=str(data['created_by']),
            retrieved_at=data['retrieved_at'],
            finished_at=data['finished_at'],
            created_at=data['created_at'],
            file_name=data['file_name'],
            content_type=data['content_type'],
            worker_log=data['worker_log'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
            file_size=data['file_size'],
        )


@dataclasses.dataclass
class DBDocumentTemplate:
    id: str
    name: str
    organization_id: str
    template_id: str
    version: str
    metamodel_version: int
    description: str
    readme: str
    license: str
    allowed_packages: dict
    formats: dict
    phase: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    tenant_uuid: str

    @property
    def is_draft(self):
        return self.phase == DocumentTemplatePhase.DRAFT

    @property
    def is_released(self):
        return self.phase == DocumentTemplatePhase.RELEASED

    @property
    def is_deprecated(self):
        return self.phase == DocumentTemplatePhase.DEPRECATED

    @staticmethod
    def from_dict_row(data: dict) -> 'DBDocumentTemplate':
        return DBDocumentTemplate(
            id=data['id'],
            name=data['name'],
            organization_id=data['organization_id'],
            template_id=data['template_id'],
            version=data['version'],
            metamodel_version=data['metamodel_version'],
            description=data['description'],
            readme=data['readme'],
            license=data['license'],
            allowed_packages=data['allowed_packages'],
            formats=data['formats'],
            phase=data['phase'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
        )


@dataclasses.dataclass
class DBDocumentTemplateFile:
    document_template_id: str
    uuid: str
    file_name: str
    content: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    tenant_uuid: str

    @staticmethod
    def from_dict_row(data: dict) -> 'DBDocumentTemplateFile':
        return DBDocumentTemplateFile(
            document_template_id=data['document_template_id'],
            uuid=str(data['uuid']),
            file_name=data['file_name'],
            content=data['content'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
        )


@dataclasses.dataclass
class DBDocumentTemplateAsset:
    document_template_id: str
    uuid: str
    file_name: str
    content_type: str
    file_size: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    tenant_uuid: str

    @staticmethod
    def from_dict_row(data: dict) -> 'DBDocumentTemplateAsset':
        return DBDocumentTemplateAsset(
            document_template_id=data['document_template_id'],
            uuid=str(data['uuid']),
            file_name=data['file_name'],
            content_type=data['content_type'],
            file_size=data['file_size'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
        )


@dataclasses.dataclass
class PersistentCommand:
    uuid: str
    state: str
    component: str
    function: str
    body: dict
    last_error_message: str | None
    attempts: int
    max_attempts: int
    tenant_uuid: str
    created_by: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @staticmethod
    def from_dict_row(data: dict):
        return PersistentCommand(
            uuid=str(data['uuid']),
            state=data['state'],
            component=data['component'],
            function=data['function'],
            body=json.loads(data['body']),
            last_error_message=data['last_error_message'],
            attempts=data['attempts'],
            max_attempts=data['max_attempts'],
            created_by=str(data['created_by']),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
        )


@dataclasses.dataclass
class DBTenantConfig:
    uuid: str
    organization: dict | None
    authentication: dict | None
    privacy_and_support: dict | None
    dashboard: dict | None
    look_and_feel: dict | None
    registry: dict | None
    knowledge_model: dict | None
    questionnaire: dict | None
    submission: dict | None
    owl: dict | None
    mail_config_uuid: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @property
    def app_title(self) -> str | None:
        if self.look_and_feel is None:
            return None
        return self.look_and_feel.get('appTitle', None)

    @property
    def support_email(self) -> str | None:
        if self.privacy_and_support is None:
            return None
        return self.privacy_and_support.get('supportEmail', None)

    @staticmethod
    def from_dict_row(data: dict):
        return DBTenantConfig(
            uuid=str(data['uuid']),
            organization=data.get('organization', None),
            authentication=data.get('authentication', None),
            privacy_and_support=data.get('privacy_and_support', None),
            dashboard=data.get('dashboard_and_login_screen', None),
            look_and_feel=data.get('look_and_feel', None),
            registry=data.get('registry', None),
            knowledge_model=data.get('knowledge_model', None),
            questionnaire=data.get('questionnaire', None),
            submission=data.get('submission', None),
            owl=data.get('owl', None),
            mail_config_uuid=data.get('mail_config_uuid', None),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
        )


@dataclasses.dataclass
class DBTenantLimits:
    tenant_uuid: str
    storage: int | None

    @staticmethod
    def from_dict_row(data: dict):
        return DBTenantLimits(
            tenant_uuid=str(data['uuid']),
            storage=data['storage'],
        )


@dataclasses.dataclass
class DBSubmission:
    TABLE_NAME = 'submission'

    uuid: str
    state: str
    location: str
    returned_data: str
    service_id: str
    document_uuid: str
    created_by: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    tenant_uuid: str

    @staticmethod
    def from_dict_row(data: dict):
        return DBSubmission(
            uuid=str(data['uuid']),
            state=data['state'],
            location=data['location'],
            returned_data=data['returned_data'],
            service_id=data['service_id'],
            document_uuid=str(data['document_uuid']),
            created_by=str(data['created_by']),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
        )

    def to_dict(self) -> dict:
        return {
            'uuid': self.uuid,
            'state': self.state,
            'location': self.location,
            'returned_data': self.returned_data,
            'service_id': self.service_id,
            'document_uuid': self.document_uuid,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(timespec='milliseconds'),
            'updated_at': self.updated_at.isoformat(timespec='milliseconds'),
            'tenant_uuid': self.tenant_uuid,
        }


@dataclasses.dataclass
class DBQuestionnaireSimple:
    # without: events, answered_questions, unanswered_questions,
    #          squashed, versions, selected_question_tag_uuids
    TABLE_NAME = 'questionnaire'

    uuid: str
    name: str
    visibility: str
    sharing: str
    package_id: str
    document_template_id: str
    format_uuid: str
    created_by: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    description: str
    is_template: bool
    project_tags: list[str]
    tenant_uuid: str

    @staticmethod
    def from_dict_row(data: dict):
        return DBQuestionnaireSimple(
            uuid=str(data['uuid']),
            name=data['name'],
            visibility=data['visibility'],
            sharing=data['sharing'],
            package_id=data['package_id'],
            document_template_id=data['document_template_id'],
            format_uuid=str(data['format_uuid']),
            created_by=str(data['created_by']),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            description=data['description'],
            is_template=data['is_template'],
            project_tags=data['project_tags'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
        )

    def to_dict(self) -> dict:
        return {
            'uuid': self.uuid,
            'name': self.name,
            'visibility': self.visibility,
            'sharing': self.sharing,
            'package_id': self.package_id,
            'document_template_id': self.document_template_id,
            'format_uuid': self.format_uuid,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(timespec='milliseconds'),
            'updated_at': self.updated_at.isoformat(timespec='milliseconds'),
            'description': self.description,
            'is_template': self.is_template,
            'project_tags': self.project_tags,
            'tenant_uuid': self.tenant_uuid,
        }


@dataclasses.dataclass
class DBUserEntity:
    TABLE_NAME = 'user_entity'

    uuid: str
    first_name: str
    last_name: str
    email: str
    locale: str | None

    @staticmethod
    def from_dict_row(data: dict):
        return DBUserEntity(
            uuid=str(data['uuid']),
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            locale=data['locale'],
        )


@dataclasses.dataclass
class DBLocale:
    TABLE_NAME = 'locale'

    id: str
    name: str
    code: str
    default_locale: bool
    enabled: bool

    @staticmethod
    def from_dict_row(data: dict):
        return DBLocale(
            id=str(data['id']),
            name=data['name'],
            code=data['code'],
            default_locale=data['default_locale'],
            enabled=data['enabled'],
        )


@dataclasses.dataclass
class DBInstanceConfigMail:
    TABLE_NAME = 'instance_config_mail'

    uuid: str
    enabled: bool
    provider: str
    sender_name: str | None
    sender_email: str | None
    smtp_host: str | None
    smtp_port: int | None
    smtp_security: str | None
    smtp_username: str | None
    smtp_password: str | None
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    aws_region: str | None
    rate_limit_window: int | None
    rate_limit_count: int | None
    timeout: int | None

    @staticmethod
    def from_dict_row(data: dict):
        return DBInstanceConfigMail(
            uuid=str(data['uuid']),
            enabled=data['enabled'],
            provider=data['provider'],
            sender_name=data['sender_name'],
            sender_email=data['sender_email'],
            smtp_host=data['smtp_host'],
            smtp_port=data['smtp_port'],
            smtp_security=data['smtp_security'],
            smtp_username=data['smtp_username'],
            smtp_password=data['smtp_password'],
            aws_access_key_id=data['aws_access_key_id'],
            aws_secret_access_key=data['aws_secret_access_key'],
            aws_region=data['aws_region'],
            rate_limit_window=data['rate_limit_window'],
            rate_limit_count=data['rate_limit_count'],
            timeout=data['timeout'],
        )
