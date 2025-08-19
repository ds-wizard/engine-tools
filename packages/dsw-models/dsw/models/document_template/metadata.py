import pydantic


class PackagePattern(pydantic.BaseModel):
    organization_id: str | None = None  # TODO: regex
    km_id: str | None = None  # TODO: regex
    min_version: str | None = None  # TODO: semver
    max_version: str | None = None  # TODO: semver


class DocumentTemplateStep(pydantic.BaseModel):
    name: str
    options: dict[str, str] = pydantic.Field(default_factory=dict)


class DocumentTemplateFormat(pydantic.BaseModel):
    uuid: str | None = None  # TODO: derive
    name: str
    icon: str = ""
    steps: list[DocumentTemplateStep] = pydantic.Field(default_factory=list)


class DocumentTemplateTDK(pydantic.BaseModel):
    version: str  # TODO: semver
    readme_file: str | None = pydantic.Field(default=None, alias='readmeFile')
    files: list[str] = pydantic.Field(default_factory=list)


class DocumentTemplateMetadata(pydantic.BaseModel):
    id: str | None = None  # TODO: derive
    organizationId: str  # TODO: regex
    templateId: str  # TODO: regex
    version: str  # TODO: semver
    name: str
    description: str
    metamodelVersion: str  # TODO: \d.\d
    license: str
    readme: str = ""
    allowed_packages: list = pydantic.Field(default_factory=list, alias='allowedPackages')
    formats: list[DocumentTemplateFormat] = pydantic.Field(default_factory=list)
    tdk: DocumentTemplateTDK | None = pydantic.Field(default=None, alias='_tdk')
