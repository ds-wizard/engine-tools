import dataclasses
import datetime
import json

from typing import Optional


NULL_UUID = '00000000-0000-0000-0000-000000000000'


class DocumentState:
    QUEUED = 'QueuedDocumentState'
    PROCESSING = 'InProgressDocumentState'
    FAILED = 'ErrorDocumentState'
    FINISHED = 'DoneDocumentState'


@dataclasses.dataclass
class DBDocument:
    uuid: str
    name: str
    state: str
    durability: str
    questionnaire_uuid: str
    questionnaire_event_uuid: str
    questionnaire_replies_hash: str
    template_id: str
    format_uuid: str
    file_name: str
    content_type: str
    worker_log: str
    creator_uuid: str
    retrieved_at: Optional[datetime.datetime]
    finished_at: Optional[datetime.datetime]
    created_at: datetime.datetime
    app_uuid: str
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
            template_id=data['template_id'],
            format_uuid=str(data['format_uuid']),
            creator_uuid=str(data['creator_uuid']),
            retrieved_at=data['retrieved_at'],
            finished_at=data['finished_at'],
            created_at=data['created_at'],
            file_name=data['file_name'],
            content_type=data['content_type'],
            worker_log=data['worker_log'],
            app_uuid=str(data.get('app_uuid', NULL_UUID)),
            file_size=data['file_size'],
        )


@dataclasses.dataclass
class DBTemplate:
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
    recommended_package_id: str
    formats: dict
    created_at: datetime.datetime
    app_uuid: str

    @staticmethod
    def from_dict_row(data: dict):
        return DBTemplate(
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
            recommended_package_id=data['recommended_package_id'],
            formats=data['formats'],
            created_at=data['created_at'],
            app_uuid=str(data.get('app_uuid', NULL_UUID)),
        )


@dataclasses.dataclass
class DBTemplateFile:
    template_id: str
    uuid: str
    file_name: str
    content: str
    app_uuid: str

    @staticmethod
    def from_dict_row(data: dict):
        return DBTemplateFile(
            template_id=data['template_id'],
            uuid=str(data['uuid']),
            file_name=data['file_name'],
            content=data['content'],
            app_uuid=str(data.get('app_uuid', NULL_UUID)),
        )


@dataclasses.dataclass
class DBTemplateAsset:
    template_id: str
    uuid: str
    file_name: str
    content_type: str
    app_uuid: str
    file_size: int

    @staticmethod
    def from_dict_row(data: dict):
        return DBTemplateAsset(
            template_id=data['template_id'],
            uuid=str(data['uuid']),
            file_name=data['file_name'],
            content_type=data['content_type'],
            app_uuid=str(data.get('app_uuid', NULL_UUID)),
            file_size=data['file_size'],
        )


@dataclasses.dataclass
class PersistentCommand:
    uuid: str
    state: str
    component: str
    function: str
    body: dict
    last_error_message: Optional[str]
    attempts: int
    max_attempts: int
    app_uuid: str
    created_by: Optional[str]
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
            app_uuid=str(data.get('app_uuid', NULL_UUID)),
        )


@dataclasses.dataclass
class DBAppConfig:
    uuid: str
    organization: dict
    authentication: dict
    privacy_and_support: dict
    dashboard: dict
    look_and_feel: dict
    registry: dict
    knowledge_model: dict
    questionnaire: dict
    template: dict
    submission: dict
    feature: dict
    owl: dict
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @property
    def feature_pdf_only(self) -> bool:
        return self.feature.get('pdfOnlyEnabled', False)

    @property
    def feature_pdf_watermark(self) -> bool:
        return self.feature.get('pdfWatermarkEnabled', False)

    @property
    def app_title(self) -> Optional[str]:
        return self.look_and_feel.get('appTitle', None)

    @property
    def support_email(self) -> Optional[str]:
        return self.privacy_and_support.get('supportEmail', None)

    @staticmethod
    def from_dict_row(data: dict):
        return DBAppConfig(
            uuid=str(data['uuid']),
            organization=data['organization'],
            authentication=data['authentication'],
            privacy_and_support=data['privacy_and_support'],
            dashboard=data['dashboard'],
            look_and_feel=data['look_and_feel'],
            registry=data['registry'],
            knowledge_model=data['knowledge_model'],
            questionnaire=data['questionnaire'],
            template=data['template'],
            submission=data['submission'],
            feature=data['feature'],
            owl=data['owl'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
        )


@dataclasses.dataclass
class DBAppLimits:
    app_uuid: str
    storage: Optional[int]

    @staticmethod
    def from_dict_row(data: dict):
        return DBAppLimits(
            app_uuid=str(data['uuid']),
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
    app_uuid: str

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
            app_uuid=str(data.get('app_uuid', NULL_UUID)),
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
            'app_uuid': self.app_uuid,
        }
