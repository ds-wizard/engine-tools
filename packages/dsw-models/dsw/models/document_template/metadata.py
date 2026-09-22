"""Document template descriptor (``template.json``).

Two shapes exist: the **local** descriptor maintained next to the template sources (TDK), and
the **bundle** descriptor inside a template ZIP package imported by the backend.
"""
from __future__ import annotations

import typing
from uuid import UUID

import pydantic

from ..common import BaseModel, Timestamp
from ..versions import MetamodelVersion


class PackagePattern(BaseModel):
    """Knowledge model packages a template can be used with."""

    org_id: str | None = None
    km_id: str | None = None
    min_version: str | None = None
    max_version: str | None = None
    #: free string pairs for the document worker, not validated
    options: dict[str, str] | None = pydantic.Field(
        default=None,
        exclude_if=lambda value: value is None,
    )


class FormatStep(BaseModel):
    name: str
    options: dict[str, str] = pydantic.Field(default_factory=dict)


class Format(BaseModel):
    uuid: UUID
    name: str
    icon: str
    steps: list[FormatStep] = pydantic.Field(default_factory=list)


class TDKConfig(BaseModel):
    """The ``_tdk`` section of a local descriptor."""

    version: str | None = pydantic.Field(default=None, exclude_if=lambda value: value is None)
    readme_file: str | None = pydantic.Field(default=None, exclude_if=lambda value: value is None)
    files: list[str] | None = pydantic.Field(default=None, exclude_if=lambda value: value is None)


class TemplateFile(BaseModel):
    uuid: UUID
    file_name: str
    content: str


class TemplateAsset(BaseModel):
    uuid: UUID
    file_name: str
    content_type: str


MetamodelVersionString = typing.Annotated[str, pydantic.StringConstraints(pattern=r'^\d+(\.\d+)?$')]


class DocumentTemplateDescriptor(BaseModel):
    template_id: str
    organization_id: str
    version: str
    name: str
    description: str
    license: str
    metamodel_version: MetamodelVersionString
    language: str = 'en'
    allowed_packages: list[PackagePattern] = pydantic.Field(default_factory=list)
    formats: list[Format] = pydantic.Field(default_factory=list)

    @property
    def coordinate(self) -> str:
        return f'{self.organization_id}:{self.template_id}:{self.version}'

    @property
    def parsed_metamodel_version(self) -> MetamodelVersion:
        return MetamodelVersion.parse(self.metamodel_version)


class DocumentTemplateMetadata(DocumentTemplateDescriptor):
    """Local ``template.json``; the README lives in its own file."""

    tdk: TDKConfig | None = pydantic.Field(
        default=None,
        alias='_tdk',
        exclude_if=lambda value: value is None,
    )


class DocumentTemplateBundle(DocumentTemplateDescriptor):
    """``template/template.json`` inside a template package."""

    id: str
    readme: str
    files: list[TemplateFile] = pydantic.Field(default_factory=list)
    assets: list[TemplateAsset] = pydantic.Field(default_factory=list)
    created_at: Timestamp
    updated_at: Timestamp | None = pydantic.Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
