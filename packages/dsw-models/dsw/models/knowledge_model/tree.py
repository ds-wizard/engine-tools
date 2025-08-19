import uuid

import pydantic


class Answer(pydantic.BaseModel):
    uuid: uuid.UUID


class Choice(pydantic.BaseModel):
    uuid: uuid.UUID


class Expert(pydantic.BaseModel):
    uuid: uuid.UUID


class Question(pydantic.BaseModel):
    uuid: uuid.UUID
    title: str
    text: str


class Chapter(pydantic.BaseModel):
    uuid: uuid.UUID
    title: str
    description: str
    questions: list[Question] = pydantic.Field(default_factory=list)


class Tag(pydantic.BaseModel):
    uuid: uuid.UUID


class Phase(pydantic.BaseModel):
    uuid: uuid.UUID


class Metric(pydantic.BaseModel):
    uuid: uuid.UUID


class Integration(pydantic.BaseModel):
    uuid: uuid.UUID


class ResourcePage(pydantic.BaseModel):
    uuid: uuid.UUID


class ResourceCollection(pydantic.BaseModel):
    uuid: uuid.UUID


class KnowledgeModel(pydantic.BaseModel):
    uuid: uuid.UUID
    chapters: list[Chapter] = pydantic.Field(default_factory=list)
    tags: list[Tag] = pydantic.Field(default_factory=list)
    phases: list[Phase] = pydantic.Field(default_factory=list)
    metrics: list[Metric] = pydantic.Field(default_factory=list)
    integrations: list[Integration] = pydantic.Field(default_factory=list)
    resource_collections: list[ResourceCollection] = pydantic.Field(alias='resourceCollections', default_factory=list)
