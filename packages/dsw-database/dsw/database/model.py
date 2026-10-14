from __future__ import annotations

import dataclasses
import enum
import json
import typing


if typing.TYPE_CHECKING:
    from datetime import datetime


NULL_UUID = '00000000-0000-0000-0000-000000000000'


def _str_or_none(value) -> str | None:
    return None if value is None else str(value)


def _metamodel_version(value) -> str:
    # a SemVer2Tuple column is read as its text form, e.g. "(19,0)"
    if isinstance(value, str) and value.startswith('('):
        major, minor = value.strip('()').split(',')
        return f'{major.strip()}.{minor.strip()}'
    return str(value)


class DocumentState(enum.Enum):
    QUEUED = 'QueuedDocumentState'
    PROCESSING = 'InProgressDocumentState'
    FAILED = 'ErrorDocumentState'
    FINISHED = 'DoneDocumentState'


class DocumentTemplatePhase(enum.Enum):
    RELEASED = 'ReleasedDocumentTemplatePhase'
    DEPRECATED = 'DeprecatedDocumentTemplatePhase'
    DRAFT = 'DraftDocumentTemplatePhase'


@dataclasses.dataclass
class DBComponent:
    name: str
    version: str
    built_at: datetime
    created_at: datetime
    updated_at: datetime

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
    project_uuid: str | None
    project_event_uuid: str | None
    document_template_uuid: str
    format_uuid: str
    file_name: str
    content_type: str
    worker_log: str
    created_by: str | None
    retrieved_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    tenant_uuid: str
    file_size: int
    workspace_uuid: str | None = None
    #: hash of the document context the document was generated from
    context_hash: str | None = None
    #: set (instead of project_uuid) for a preview of a KM editor
    knowledge_model_editor_uuid: str | None = None

    @staticmethod
    def from_dict_row(data: dict):
        return DBDocument(
            uuid=str(data['uuid']),
            name=data['name'],
            state=data['state'],
            durability=data['durability'],
            project_uuid=_str_or_none(data['project_uuid']),
            project_event_uuid=_str_or_none(data['project_event_uuid']),
            document_template_uuid=data['document_template_uuid'],
            format_uuid=str(data['format_uuid']),
            created_by=_str_or_none(data['created_by']),
            retrieved_at=data['retrieved_at'],
            finished_at=data['finished_at'],
            created_at=data['created_at'],
            file_name=data['file_name'],
            content_type=data['content_type'],
            worker_log=data['worker_log'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
            file_size=data['file_size'],
            workspace_uuid=_str_or_none(data.get('workspace_uuid')),
            context_hash=data.get('context_hash'),
            knowledge_model_editor_uuid=_str_or_none(data.get('knowledge_model_editor_uuid')),
        )


@dataclasses.dataclass
class DBDocumentTemplate:
    uuid: str
    name: str
    #: the single id of Wizard 5.0, e.g. dsw.questionnaire-report
    id: str
    version: str
    #: "major.minor", e.g. "19.0"
    metamodel_version: str
    description: str
    readme: str
    license: str
    #: [{id, minVersion, maxVersion}]
    allowed_packages: list[dict]
    formats: list
    phase: str
    created_at: datetime
    updated_at: datetime
    tenant_uuid: str
    language: str = 'en'
    pot_file_ready: bool = False
    #: None for a template shared by the whole organization (tenant)
    workspace_uuid: str | None = None

    @property
    def is_draft(self):
        return self.phase == DocumentTemplatePhase.DRAFT.value

    @property
    def is_released(self):
        return self.phase == DocumentTemplatePhase.RELEASED.value

    @property
    def is_deprecated(self):
        return self.phase == DocumentTemplatePhase.DEPRECATED.value

    @property
    def coordinates(self) -> str:
        """The reference ``<id>:<version>``."""
        return f'{self.id}:{self.version}'

    @staticmethod
    def from_dict_row(data: dict) -> DBDocumentTemplate:
        return DBDocumentTemplate(
            uuid=data['uuid'],
            name=data['name'],
            id=data['id'],
            version=data['version'],
            metamodel_version=_metamodel_version(data['metamodel_version']),
            description=data['description'],
            readme=data['readme'],
            license=data['license'],
            allowed_packages=data['allowed_packages'],
            formats=[],
            phase=data['phase'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
            language=data.get('language', 'en'),
            pot_file_ready=data.get('pot_file_ready', False),
            workspace_uuid=_str_or_none(data.get('workspace_uuid')),
        )


@dataclasses.dataclass
class DBDocumentTemplateFormat:
    document_template_uuid: str
    uuid: str
    name: str
    icon: str
    created_at: datetime
    updated_at: datetime
    tenant_uuid: str

    @staticmethod
    def from_dict_row(data: dict) -> DBDocumentTemplateFormat:
        return DBDocumentTemplateFormat(
            document_template_uuid=data['document_template_uuid'],
            uuid=str(data['uuid']),
            name=data['name'],
            icon=data['icon'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
        )


@dataclasses.dataclass
class DBDocumentTemplateStep:
    document_template_uuid: str
    format_uuid: str
    position: int
    name: str
    options: dict[str, str]
    created_at: datetime
    updated_at: datetime
    tenant_uuid: str

    @staticmethod
    def from_dict_row(data: dict) -> DBDocumentTemplateStep:
        return DBDocumentTemplateStep(
            document_template_uuid=data['document_template_uuid'],
            format_uuid=str(data['format_uuid']),
            position=data['position'],
            name=data['name'],
            options=data['options'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
        )


@dataclasses.dataclass
class DBDocumentTemplateFile:
    document_template_uuid: str
    uuid: str
    file_name: str
    content: str
    created_at: datetime
    updated_at: datetime
    tenant_uuid: str

    @staticmethod
    def from_dict_row(data: dict) -> DBDocumentTemplateFile:
        return DBDocumentTemplateFile(
            document_template_uuid=data['document_template_uuid'],
            uuid=str(data['uuid']),
            file_name=data['file_name'],
            content=data['content'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
        )


@dataclasses.dataclass
class DBDocumentTemplateAsset:
    document_template_uuid: str
    uuid: str
    file_name: str
    content_type: str
    file_size: int
    created_at: datetime
    updated_at: datetime
    tenant_uuid: str

    @staticmethod
    def from_dict_row(data: dict) -> DBDocumentTemplateAsset:
        return DBDocumentTemplateAsset(
            document_template_uuid=data['document_template_uuid'],
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
    created_at: datetime
    updated_at: datetime

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
            created_by=str(data['created_by']) if data['created_by'] is not None else None,
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
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
    location: str | None
    returned_data: str | None
    service_id: str
    document_uuid: str | None
    created_by: str | None
    created_at: datetime | None
    updated_at: datetime
    tenant_uuid: str

    @staticmethod
    def from_dict_row(data: dict):
        return DBSubmission(
            uuid=str(data['uuid']),
            state=data['state'],
            location=data['location'],
            returned_data=data['returned_data'],
            service_id=data['service_id'],
            document_uuid=_str_or_none(data['document_uuid']),
            created_by=_str_or_none(data['created_by']),
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
            'created_at': (None if self.created_at is None
                           else self.created_at.isoformat(timespec='milliseconds')),
            'updated_at': self.updated_at.isoformat(timespec='milliseconds'),
            'tenant_uuid': self.tenant_uuid,
        }


@dataclasses.dataclass
class DBProjectSimple:
    # without: events, answered_questions, unanswered_questions,
    #          squashed, versions, selected_question_tag_uuids
    TABLE_NAME = 'project'

    uuid: str
    name: str
    visibility: str
    sharing: str
    knowledge_model_package_uuid: str
    document_template_uuid: str | None
    format_uuid: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime
    description: str
    is_template: bool
    project_tags: list[str]
    tenant_uuid: str
    workspace_uuid: str | None = None

    @staticmethod
    def from_dict_row(data: dict):
        return DBProjectSimple(
            uuid=str(data['uuid']),
            name=data['name'],
            visibility=data['visibility'],
            sharing=data['sharing'],
            knowledge_model_package_uuid=str(data['knowledge_model_package_uuid']),
            document_template_uuid=_str_or_none(data['document_template_uuid']),
            format_uuid=_str_or_none(data['format_uuid']),
            created_by=_str_or_none(data['created_by']),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            description=data['description'],
            is_template=data['is_template'],
            project_tags=data['project_tags'],
            tenant_uuid=str(data.get('tenant_uuid', NULL_UUID)),
            workspace_uuid=_str_or_none(data.get('workspace_uuid')),
        )

    def to_dict(self) -> dict:
        return {
            'uuid': self.uuid,
            'name': self.name,
            'visibility': self.visibility,
            'sharing': self.sharing,
            'knowledge_model_package_uuid': self.knowledge_model_package_uuid,
            'document_template_uuid': self.document_template_uuid,
            'format_uuid': self.format_uuid,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(timespec='milliseconds'),
            'updated_at': self.updated_at.isoformat(timespec='milliseconds'),
            'description': self.description,
            'is_template': self.is_template,
            'project_tags': self.project_tags,
            'tenant_uuid': self.tenant_uuid,
            'workspace_uuid': self.workspace_uuid,
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
    """A UI locale (Wizard 5.0, WEP 27): one PO per language code and tenant."""
    TABLE_NAME = 'locale'

    uuid: str
    tenant_uuid: str
    #: BCP 47, normalized by the backend (e.g. ``pt-BR``)
    code: str
    name: str
    #: ``Project-Id-Version`` of the PO, informational only
    pot_version: str | None
    enabled: bool
    #: at most one per tenant, and only an enabled one
    default_locale: bool
    official: bool
    created_at: datetime
    #: bumped whenever the PO is replaced
    updated_at: datetime

    @classmethod
    def from_dict_row(cls, data: dict) -> typing.Self:
        return cls(
            uuid=str(data['uuid']),
            tenant_uuid=str(data['tenant_uuid']),
            code=data['code'],
            name=data['name'],
            pot_version=data.get('pot_version'),
            enabled=data['enabled'],
            default_locale=data['default_locale'],
            official=data.get('official', False),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
        )


@dataclasses.dataclass
class DBMailTemplateLocale(DBLocale):
    """A translation of the mail templates; the same shape as a UI locale (WEP 27, B5)."""
    TABLE_NAME = 'mail_template_locale'


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
