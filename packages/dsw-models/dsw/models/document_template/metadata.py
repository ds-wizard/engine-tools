from uuid import UUID

import pydantic

from ..common import BaseModel


class PackagePattern(BaseModel):
    organization_id: str | None
    km_id: str | None
    min_version: str | None
    max_version: str | None


class DocumentTemplateStep(BaseModel):
    name: str
    options: dict[str, str]


class DocumentTemplateFormat(BaseModel):
    uuid: UUID
    name: str
    icon: str
    steps: list[DocumentTemplateStep]


class DocumentTemplateTDK(BaseModel):
    version: str
    readme_file: str | None
    files: list[str]


class DocumentTemplateMetadata(BaseModel):
    id: str | None
    organization_id: str
    template_id: str
    version: str
    name: str
    description: str
    metamodel_version: str
    license: str
    readme: str
    allowed_packages: list[PackagePattern]
    formats: list[DocumentTemplateFormat]
    tdk: DocumentTemplateTDK | None = pydantic.Field(default=None, alias='_tdk')
