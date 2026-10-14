"""Document template descriptor (``template.json``).

Two shapes exist: the **local** descriptor maintained next to the template sources (TDK), and
the **bundle** descriptor inside a template ZIP package imported by the backend.

Both are identified by ``id`` + ``version`` (Wizard 5.0). Like the backend's import, the models
also read the older ``organizationId`` + ``templateId`` and ``orgId`` + ``kmId`` package patterns
(see :mod:`dsw.models.coordinate`), and write only the 5.0 shape.
"""
from __future__ import annotations

import typing
from uuid import UUID

import pydantic

from ..common import BaseModel, Timestamp
from ..coordinate import build_reference, join_legacy_id, upgrade_legacy_id
from ..versions import MetamodelVersion


def upgrade_legacy_package_pattern(data: typing.Any) -> typing.Any:
    """Join a pre-5.0 ``orgId`` + ``kmId`` pattern into ``id``.

    A pattern naming only an organization becomes ``id = None`` (any knowledge model).
    """
    if not isinstance(data, dict) or not ({'orgId', 'kmId'} & data.keys()):
        return data
    data = dict(data)
    org_id, km_id = data.pop('orgId', None), data.pop('kmId', None)
    if data.get('id') is None:
        data['id'] = join_legacy_id(org_id, km_id) if org_id and km_id else None
    return data


class PackagePattern(BaseModel):
    """Knowledge model packages a template can be used with; ``None`` matches any."""

    id: str | None = None
    min_version: str | None = None
    max_version: str | None = None
    #: free string pairs for the document worker, not validated
    options: dict[str, str] | None = pydantic.Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @pydantic.model_validator(mode='before')
    @classmethod
    def _upgrade_legacy(cls, data: typing.Any) -> typing.Any:
        return upgrade_legacy_package_pattern(data)


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
    id: str
    version: str
    name: str
    description: str
    license: str
    metamodel_version: MetamodelVersionString
    language: str = 'en'
    allowed_packages: list[PackagePattern] = pydantic.Field(default_factory=list)
    formats: list[Format] = pydantic.Field(default_factory=list)

    @pydantic.model_validator(mode='before')
    @classmethod
    def _upgrade_legacy(cls, data: typing.Any) -> typing.Any:
        if isinstance(data, dict):
            data = dict(data)
            upgrade_legacy_id(data, 'templateId')
        return data

    @property
    def reference(self) -> str:
        return build_reference(self.id, self.version)

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

    readme: str
    files: list[TemplateFile] = pydantic.Field(default_factory=list)
    assets: list[TemplateAsset] = pydantic.Field(default_factory=list)
    created_at: Timestamp
    updated_at: Timestamp | None = pydantic.Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
