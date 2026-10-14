"""Document context (metamodel 19.0) as the backend sends it.

The same shape is the body of the ``generateDocument`` persistent command (with ``document``) and
the response of the document context endpoints (``document`` is ``null``). Exactly one of
``project`` and ``knowledgeModelEditor`` is set.

This is the backend payload only. The document worker adds keys before rendering (``extras``,
``config.serviceName`` …); validate the original command body, not the enriched dictionary.
"""
from __future__ import annotations

import typing
from uuid import UUID

import pydantic

from ..common import BaseModel, Timestamp, UserSuggestion
from ..document_template.metadata import MetamodelVersionString
from ..knowledge_model import flat
from ..project.files import ProjectFile
from ..project.replies import Reply
from ..project.report import ChapterReport, TotalReport
from ..project.versions import ProjectVersion
from ..versions import MetamodelVersion


ProjectVisibility = typing.Literal[
    'PrivateProjectVisibility', 'VisibleViewProjectVisibility',
    'VisibleCommentProjectVisibility', 'VisibleEditProjectVisibility',
]
ProjectSharing = typing.Literal[
    'RestrictedProjectSharing', 'AnyoneWithLinkViewProjectSharing',
    'AnyoneWithLinkCommentProjectSharing', 'AnyoneWithLinkEditProjectSharing',
]


class Config(BaseModel):
    """Effective look and feel of the workspace."""

    client_url: str
    app_title: str | None = None
    primary_color: str | None = None
    logo_url: str | None = None


class Workspace(BaseModel):
    uuid: UUID
    name: str
    description: str | None = None


class User(BaseModel):
    uuid: UUID
    first_name: str
    last_name: str
    email: str
    affiliation: str | None = None
    active: bool
    image_url: str | None = None
    created_at: Timestamp
    updated_at: Timestamp


class UserPermission(BaseModel):
    user: User
    perms: list[str]


class UserGroupMember(UserSuggestion):
    membership_type: typing.Literal['OwnerUserGroupMembershipType', 'MemberUserGroupMembershipType']


class UserGroup(BaseModel):
    uuid: UUID
    name: str
    description: str | None = None
    private: bool
    members: list[UserGroupMember]
    created_at: Timestamp
    updated_at: Timestamp


class UserGroupPermission(BaseModel):
    group: UserGroup
    perms: list[str]


class Project(BaseModel):
    """Metadata of the project; its content is in :class:`Questionnaire`."""

    uuid: UUID
    name: str
    description: str | None = None
    created_by: User | None = None
    created_at: Timestamp
    updated_at: Timestamp
    visibility: ProjectVisibility
    sharing: ProjectSharing
    is_template: bool
    knowledge_model_package_uuid: UUID
    selected_question_tag_uuids: list[UUID]
    project_tags: list[str]
    document_template_uuid: UUID | None = None
    format_uuid: UUID | None = None
    #: sorted by user uuid
    users: list[UserPermission]
    #: sorted by group uuid
    groups: list[UserGroupPermission]


class KnowledgeModelEditor(BaseModel):
    uuid: UUID
    name: str
    description: str
    created_by: User | None = None
    created_at: Timestamp
    updated_at: Timestamp
    id: str
    version: str
    license: str
    readme: str
    previous_package_uuid: UUID | None = None
    previous_package_id: str | None = None
    previous_package_version: str | None = None
    knowledge_model_metamodel_version: int


class QuestionnaireReport(BaseModel):
    """The project report without its generated uuid and timestamps, which would break the hash."""

    total_report: TotalReport
    chapter_reports: list[ChapterReport]
    chapters: list[flat.Chapter]
    metrics: list[flat.Metric]


class Questionnaire(BaseModel):
    """Content of the project, or of the preview questionnaire of a KM editor."""

    replies: dict[str, Reply]
    labels: dict[str, list[UUID]]
    phase_uuid: UUID | None = None
    version_uuid: UUID | None = None
    #: sorted by createdAt, then uuid
    versions: list[ProjectVersion]
    #: sorted by uuid
    files: list[ProjectFile]
    report: QuestionnaireReport
    language: str | None = None


class KnowledgeModelPackage(BaseModel):
    uuid: UUID
    id: str
    version: str
    name: str
    description: str
    language: str
    created_at: Timestamp
    workspace_uuid: UUID | None = None


class DocumentTemplate(BaseModel):
    uuid: UUID
    id: str
    version: str
    workspace_uuid: UUID | None = None


class DocumentFormat(BaseModel):
    uuid: UUID
    name: str


class DocumentTemplateLocale(BaseModel):
    uuid: UUID
    name: str
    code: str
    created_at: Timestamp
    updated_at: Timestamp


class Document(BaseModel):
    uuid: UUID
    name: str
    document_template: DocumentTemplate
    format: DocumentFormat
    language: str | None = None
    locale: DocumentTemplateLocale | None = None
    #: a temporary document (preview), not a stored one
    preview: bool
    event_uuid: UUID | None = None
    created_by: User | None = None
    created_at: Timestamp


class DocumentContext(BaseModel):
    metamodel_version: MetamodelVersionString
    #: see :mod:`dsw.models.document_context.hash`
    hash: str
    workspace: Workspace
    project: Project | None = None
    knowledge_model_editor: KnowledgeModelEditor | None = None
    questionnaire: Questionnaire
    knowledge_model: flat.KnowledgeModel
    knowledge_model_package: KnowledgeModelPackage | None = None
    #: ``None`` outside of the document worker
    document: Document | None = None
    config: Config

    @pydantic.model_validator(mode='after')
    def _check_source(self) -> typing.Self:
        if (self.project is None) == (self.knowledge_model_editor is None):
            raise ValueError('Exactly one of project and knowledgeModelEditor must be set')
        return self

    @property
    def parsed_metamodel_version(self) -> MetamodelVersion:
        return MetamodelVersion.parse(self.metamodel_version)
