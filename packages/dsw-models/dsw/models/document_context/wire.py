"""Document context as the backend puts it into the ``generateDocument`` persistent command.

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
from ..project.report import Report
from ..project.versions import ProjectVersion
from ..versions import MetamodelVersion


class Config(BaseModel):
    client_url: str
    app_title: str | None = None
    app_title_short: str | None = None
    illustrations_color: str | None = None
    primary_color: str | None = None
    logo_url: str | None = None


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


class DocumentTemplateLocale(BaseModel):
    uuid: UUID
    name: str
    code: str
    created_at: Timestamp
    updated_at: Timestamp


class Document(BaseModel):
    uuid: UUID
    name: str
    document_template_uuid: UUID
    format_uuid: UUID
    language: str | None = None
    locale: DocumentTemplateLocale | None = None
    created_by: User | None = None
    created_at: Timestamp


class Project(BaseModel):
    uuid: UUID
    name: str
    description: str | None = None
    replies: dict[str, Reply]
    phase_uuid: UUID | None = None
    labels: dict[str, list[UUID]]
    version_uuid: UUID | None = None
    versions: list[ProjectVersion]
    project_tags: list[str]
    files: list[ProjectFile]
    language: str | None = None
    created_by: User | None = None
    created_at: Timestamp
    updated_at: Timestamp


class RegistryOrganization(BaseModel):
    organization_id: str
    name: str
    logo: str | None = None
    created_at: Timestamp


class KnowledgeModelPackage(BaseModel):
    uuid: UUID
    name: str
    organization_id: str
    km_id: str
    version: str
    versions: list[str]
    remote_latest_version: str | None = None
    description: str
    organization: RegistryOrganization | None = None
    language: str
    created_at: Timestamp


class Organization(BaseModel):
    tenant_uuid: UUID
    name: str
    description: str
    organization_id: str
    affiliations: list[str]
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
    users: list[UserGroupMember]
    created_at: Timestamp
    updated_at: Timestamp


class UserGroupPermission(BaseModel):
    group: UserGroup
    perms: list[str]


class DocumentContext(BaseModel):
    config: Config
    document: Document
    project: Project
    knowledge_model: flat.KnowledgeModel
    report: Report
    knowledge_model_package: KnowledgeModelPackage
    organization: Organization
    metamodel_version: MetamodelVersionString
    users: list[UserPermission] = pydantic.Field(default_factory=list)
    groups: list[UserGroupPermission] = pydantic.Field(default_factory=list)

    @property
    def parsed_metamodel_version(self) -> MetamodelVersion:
        return MetamodelVersion.parse(self.metamodel_version)
