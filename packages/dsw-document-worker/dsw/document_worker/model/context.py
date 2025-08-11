# pylint: disable=too-many-lines, unused-argument, too-many-arguments,
import abc
import datetime
import typing

import dateutil.parser as dp

from ..consts import NULL_UUID
from ..utils import check_metamodel_version
from .utils import strip_markdown

AnnotationsT = dict[str, str | list[str]]
TODO_LABEL_UUID = "615b9028-5e3f-414f-b245-12d2ae2eeb20"


def _datetime(timestamp: str) -> datetime.datetime:
    return dp.isoparse(timestamp)


def _load_annotations(annotations: list[dict[str, str]]) -> AnnotationsT:
    result: AnnotationsT = {}
    semi_result: dict[str, list[str]] = {}
    for item in annotations:
        key = item.get('key', '')
        value = item.get('value', '')
        if key in semi_result:
            semi_result[key].append(value)
        else:
            semi_result[key] = [value]
    for key, value_list in semi_result.items():
        if len(value_list) == 1:
            result[key] = value_list[0]
        else:
            result[key] = value_list
    return result


class SimpleAuthor:

    def __init__(self, *, uuid: str, first_name: str, last_name: str,
                 image_url: str | None, gravatar_hash: str | None):
        self.uuid = uuid
        self.first_name = first_name
        self.last_name = last_name
        self.image_url = image_url
        self.gravatar_hash = gravatar_hash

    @staticmethod
    def load(data: dict | None, **options):
        if data is None:
            return None
        return SimpleAuthor(
            uuid=data['uuid'],
            first_name=data['firstName'],
            last_name=data['lastName'],
            image_url=data['imageUrl'],
            gravatar_hash=data['gravatarHash'],
        )


class User:

    def __init__(self, *, uuid: str, first_name: str, last_name: str, email: str,
                 role: str, created_at: datetime.datetime, updated_at: datetime.datetime,
                 affiliation: str | None, permissions: list[str], sources: list[str],
                 image_url: str | None):
        self.uuid = uuid
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.role = role
        self.image_url = image_url
        self.affiliation = affiliation
        self.permissions = permissions
        self.sources = sources
        self.created_at = created_at
        self.updated_at = updated_at

    @staticmethod
    def load(data: dict, **options):
        if data is None:
            return None
        return User(
            uuid=data['uuid'],
            first_name=data['firstName'],
            last_name=data['lastName'],
            email=data['email'],
            role=data['role'],
            image_url=data['imageUrl'],
            affiliation=data['affiliation'],
            permissions=data['permissions'],
            sources=data['sources'],
            created_at=_datetime(data['createdAt']),
            updated_at=_datetime(data['updatedAt']),
        )


class Organization:

    def __init__(self, *, org_id: str, name: str, description: str | None,
                 affiliations: list[str]):
        self.id = org_id
        self.name = name
        self.description = description
        self.affiliations = affiliations

    @staticmethod
    def load(data: dict, **options):
        return Organization(
            org_id=data['organizationId'],
            name=data['name'],
            description=data['description'],
            affiliations=data['affiliations'],
        )


class Tag:

    def __init__(self, *, uuid: str, name: str, description: str | None,
                 color: str, annotations: AnnotationsT):
        self.uuid = uuid
        self.name = name
        self.description = description
        self.color = color
        self.annotations = annotations

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Tag):
            return False
        return other.uuid == self.uuid

    @staticmethod
    def load(data: dict, **options):
        return Tag(
            uuid=data['uuid'],
            name=data['name'],
            description=data['description'],
            color=data['color'],
            annotations=_load_annotations(data['annotations']),
        )


class ResourceCollection:

    def __init__(self, *, uuid: str, title: str, page_uuids: list[str],
                 annotations: AnnotationsT):
        self.uuid = uuid
        self.title = title
        self.page_uuids = page_uuids
        self.annotations = annotations
        self.pages: list[ResourcePage] = []

    def resolve_links(self, ctx):
        self.pages = [ctx.e.resource_pages[key]
                      for key in self.page_uuids
                      if key in ctx.e.resource_pages]
        for page in self.pages:
            page.collection = self

    @property
    def a(self):
        return self.annotations

    @staticmethod
    def load(data: dict, **options):
        return ResourceCollection(
            uuid=data['uuid'],
            title=data['title'],
            page_uuids=data['resourcePageUuids'],
            annotations=_load_annotations(data['annotations']),
        )


class ResourcePage:

    def __init__(self, *, uuid: str, title: str, content: str,
                 annotations: AnnotationsT):
        self.uuid = uuid
        self.title = title
        self.content = content
        self.annotations = annotations

        self.collection: ResourceCollection | None = None

    @property
    def a(self):
        return self.annotations

    @staticmethod
    def load(data: dict, **options):
        return ResourcePage(
            uuid=data['uuid'],
            title=data['title'],
            content=data['content'],
            annotations=_load_annotations(data['annotations']),
        )


class Integration(abc.ABC):

    def __init__(self, *, uuid: str, name: str, variables: list[str],
                 integration_type: str, annotations: AnnotationsT):
        self.uuid = uuid
        self.name = name
        self.variables = variables
        self.type = integration_type
        self.annotations = annotations

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Integration):
            return False
        return other.uuid == self.uuid

    @staticmethod
    @abc.abstractmethod
    def load(data: dict, **options):
        pass


class ApiIntegration(Integration):

    def __init__(self, *, uuid: str, name: str, variables: list[str],
                 request_method: str, request_url: str, request_headers: dict[str, str],
                 request_body: str | None,  request_allow_empty_search: bool,
                 response_list_field: str | None, response_item_template: str,
                 response_item_template_for_selection: str | None,
                 annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            name=name,
            variables=variables,
            annotations=annotations,
            integration_type='ApiIntegration',
        )
        self.request_method = request_method
        self.request_url = request_url
        self.request_headers = request_headers
        self.request_body = request_body
        self.request_allow_empty_search = request_allow_empty_search
        self.response_list_field = response_list_field
        self.response_item_template = response_item_template
        self.response_item_template_for_selection = response_item_template_for_selection

    @staticmethod
    def default():
        return ApiIntegration(
            uuid=NULL_UUID,
            name='',
            variables=[],
            request_method='GET',
            request_url='',
            request_headers={},
            request_body=None,
            request_allow_empty_search=False,
            response_list_field=None,
            response_item_template='',
            response_item_template_for_selection=None,
            annotations={},
        )

    @staticmethod
    def load(data: dict, **options):
        return ApiIntegration(
            uuid=data['uuid'],
            name=data['name'],
            variables=data['variables'],
            request_method=data['requestMethod'],
            request_url=data['requestUrl'],
            request_headers=data['requestHeaders'],
            request_body=data.get('requestBody', None),
            request_allow_empty_search=data.get('requestAllowEmptySearch', False),
            response_list_field=data.get('responseListField', None),
            response_item_template=data['responseItemTemplate'],
            response_item_template_for_selection=data.get('responseItemTemplateForSelection', None),
            annotations=_load_annotations(data['annotations']),
        )


class ApiLegacyIntegration(Integration):

    def __init__(self, *, uuid: str, name: str, integration_id: str,
                 item_url: str | None, logo: str | None,
                 variables: list[str], rq_body: str, rq_method: str,
                 rq_headers: dict[str, str], rq_url: str, rs_list_field: str | None,
                 rs_item_id: str | None, rs_item_template: str,
                 annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            name=name,
            variables=variables,
            annotations=annotations,
            integration_type='ApiLegacyIntegration',
        )
        self.id = integration_id
        self.item_url = item_url
        self.logo = logo
        self.rq_body = rq_body
        self.rq_method = rq_method
        self.rq_url = rq_url
        self.rq_headers = rq_headers
        self.rs_list_field = rs_list_field
        self.rs_item_id = rs_item_id
        self.rs_item_template = rs_item_template

    def item(self, item_id: str) -> str | None:
        if self.item_url is None:
            return None
        return self.item_url.replace('${id}', item_id)

    @staticmethod
    def default():
        return ApiLegacyIntegration(
            uuid=NULL_UUID,
            name='',
            logo='',
            integration_id='',
            item_url='',
            variables=[],
            rq_body='',
            rq_method='GET',
            rq_url='',
            rq_headers={},
            rs_list_field='',
            rs_item_id='',
            rs_item_template='',
            annotations={},
        )

    @staticmethod
    def load(data: dict, **options):
        return ApiLegacyIntegration(
            uuid=data['uuid'],
            name=data['name'],
            integration_id=data['id'],
            item_url=data['itemUrl'],
            logo=data['logo'],
            variables=data['variables'],
            rq_body=data['requestBody'],
            rq_headers=data['requestHeaders'],
            rq_method=data['requestMethod'],
            rq_url=data['requestUrl'],
            rs_list_field=data['responseListField'],
            rs_item_id=data['responseItemId'],
            rs_item_template=data['responseItemTemplate'],
            annotations=_load_annotations(data['annotations']),
        )


class WidgetIntegration(Integration):

    def __init__(self, *, uuid: str, name: str, integration_id: str,
                 item_url: str | None, logo: str | None, variables: list[str],
                 widget_url: str, annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            name=name,
            variables=variables,
            annotations=annotations,
            integration_type='WidgetIntegration',
        )
        self.id = integration_id
        self.item_url = item_url
        self.logo = logo
        self.widget_url = widget_url

    def item(self, item_id: str) -> str | None:
        if self.item_url is None:
            return None
        return self.item_url.replace('${id}', item_id)

    @staticmethod
    def load(data: dict, **options):
        return WidgetIntegration(
            uuid=data['uuid'],
            name=data['name'],
            integration_id=data['id'],
            item_url=data['itemUrl'],
            logo=data['logo'],
            variables=data['variables'],
            widget_url=data['widgetUrl'],
            annotations=_load_annotations(data['annotations']),
        )


class Phase:

    def __init__(self, *, uuid: str, title: str, description: str | None,
                 annotations: AnnotationsT, order: int = 0):
        self.uuid = uuid
        self.title = title
        self.description = description
        self.order = order
        self.annotations = annotations

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Phase):
            return False
        return other.uuid == self.uuid

    @staticmethod
    def load(data: dict, **options):
        return Phase(
            uuid=data['uuid'],
            title=data['title'],
            description=data['description'],
            annotations=_load_annotations(data['annotations']),
        )


PHASE_NEVER = Phase(
    uuid=NULL_UUID,
    title='never',
    description=None,
    order=10000000,
    annotations={},
)


class Metric:

    def __init__(self, *, uuid: str, title: str, description: str | None,
                 abbreviation: str, annotations: AnnotationsT):
        self.uuid = uuid
        self.title = title
        self.description = description
        self.abbreviation = abbreviation
        self.annotations = annotations

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Metric):
            return False
        return other.uuid == self.uuid

    @staticmethod
    def load(data: dict, **options):
        return Metric(
            uuid=data['uuid'],
            title=data['title'],
            description=data['description'],
            abbreviation=data['abbreviation'],
            annotations=_load_annotations(data['annotations']),
        )


class MetricMeasure:

    def __init__(self, *, measure: float, weight: float, metric_uuid: str):
        self.measure = measure
        self.weight = weight
        self.metric_uuid = metric_uuid

        self.metric: Metric | None = None

    def resolve_links(self, ctx):
        if self.metric_uuid in ctx.e.metrics:
            self.metric = ctx.e.metrics[self.metric_uuid]

    @staticmethod
    def load(data: dict, **options):
        return MetricMeasure(
            measure=float(data['measure']),
            weight=float(data['weight']),
            metric_uuid=data['metricUuid'],
        )


class Reference(abc.ABC):

    def __init__(self, *, uuid: str, ref_type: str, annotations: AnnotationsT):
        self.uuid = uuid
        self.type = ref_type
        self.annotations = annotations

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Reference):
            return False
        return other.uuid == self.uuid

    def resolve_links(self, ctx):
        pass

    @staticmethod
    @abc.abstractmethod
    def load(data: dict, **options):
        pass


class CrossReference(Reference):

    def __init__(self, *, uuid: str, target_uuid: str, description: str,
                 annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            ref_type='CrossReference',
            annotations=annotations,
        )
        self.target_uuid = target_uuid
        self.description = description

    @staticmethod
    def load(data: dict, **options):
        return CrossReference(
            uuid=data['uuid'],
            target_uuid=data['targetUuid'],
            description=data['description'],
            annotations=_load_annotations(data['annotations']),
        )


class URLReference(Reference):

    def __init__(self, *, uuid: str, label: str, url: str,
                 annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            ref_type='URLReference',
            annotations=annotations,
        )
        self.label = label
        self.url = url

    @staticmethod
    def load(data: dict, **options):
        return URLReference(
            uuid=data['uuid'],
            label=data['label'],
            url=data['url'],
            annotations=_load_annotations(data['annotations']),
        )


class ResourcePageReference(Reference):

    def __init__(self, *, uuid: str, resource_page_uuid: str | None,
                 annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            ref_type='ResourcePageReference',
            annotations=annotations,
        )
        self.resource_page_uuid = resource_page_uuid

        self.resource_page: ResourcePage | None = None

    def resolve_links(self, ctx):
        if self.resource_page_uuid in ctx.e.resource_pages:
            self.resource_page = ctx.e.resource_pages[self.resource_page_uuid]

    @staticmethod
    def load(data: dict, **options):
        return ResourcePageReference(
            uuid=data['uuid'],
            resource_page_uuid=data['resourcePageUuid'],
            annotations=_load_annotations(data['annotations']),
        )


class Expert:

    def __init__(self, *, uuid: str, name: str, email: str,
                 annotations: AnnotationsT):
        self.uuid = uuid
        self.name = name
        self.email = email
        self.annotations = annotations

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Expert):
            return False
        return other.uuid == self.uuid

    @staticmethod
    def load(data: dict, **options):
        return Expert(
            uuid=data['uuid'],
            name=data['name'],
            email=data['email'],
            annotations=_load_annotations(data['annotations']),
        )


class Reply(abc.ABC):

    def __init__(self, *, path: str, created_at: datetime.datetime,
                 created_by: SimpleAuthor | None, reply_type: str):
        self.path = path
        self.created_at = created_at
        self.created_by = created_by
        self.type = reply_type

        self.question: Question | None = None
        self.fragments: list[str] = path.split('.')

    def resolve_links_parent(self, ctx):
        question_uuid = self.fragments[-1]
        if question_uuid in ctx.e.questions:
            self.question = ctx.e.questions.get(question_uuid, None)
            if self.question is not None:
                self.question.replies[self.path] = self

    def resolve_links(self, ctx):
        pass

    @property
    def item_title(self) -> str:
        """Title to be used if is a reply to first question inside a list item"""
        return ''

    @property
    def has_direct_item_title(self) -> bool:
        return True

    @staticmethod
    @abc.abstractmethod
    def load(path: str, data: dict, **options):
        pass


class AnswerReply(Reply):

    def __init__(self, *, path: str, created_at: datetime.datetime,
                 created_by: SimpleAuthor | None, answer_uuid: str):
        super().__init__(
            path=path,
            created_at=created_at,
            created_by=created_by,
            reply_type='AnswerReply',
        )
        self.answer_uuid = answer_uuid

        self.answer: Answer | None = None

    @property
    def value(self) -> str | None:
        return self.answer_uuid

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)
        self.answer = ctx.e.answers.get(self.answer_uuid, None)

    @property
    def item_title(self) -> str:
        if self.answer is not None:
            return self.answer.label
        return super().item_title

    @staticmethod
    def load(path: str, data: dict, **options):
        return AnswerReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            answer_uuid=data['value']['value'],
        )


class StringReply(Reply):

    def __init__(self, *, path: str, created_at: datetime.datetime,
                 created_by: SimpleAuthor | None, value: str):
        super().__init__(
            path=path,
            created_at=created_at,
            created_by=created_by,
            reply_type='StringReply',
        )
        self.value = value

    @property
    def as_number(self) -> float | None:
        try:
            return float(self.value)
        except Exception:
            return None

    @property
    def as_datetime(self) -> datetime.datetime | None:
        try:
            return dp.parse(self.value)
        except Exception:
            return None

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)

    @property
    def item_title(self) -> str:
        return self.value

    @staticmethod
    def load(path: str, data: dict, **options):
        return StringReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            value=data['value']['value'],
        )


class ItemListReply(Reply):

    def __init__(self, *, path: str, created_at: datetime.datetime,
                 created_by: SimpleAuthor | None, items: list[str]):
        super().__init__(
            path=path,
            created_at=created_at,
            created_by=created_by,
            reply_type='ItemListReply',
        )
        self.items = items

    @property
    def value(self) -> list[str]:
        return self.items

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)

    @property
    def has_direct_item_title(self) -> bool:
        return False

    @staticmethod
    def load(path: str, data: dict, **options):
        return ItemListReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            items=data['value']['value'],
        )


class MultiChoiceReply(Reply):

    def __init__(self, *, path: str, created_at: datetime.datetime,
                 created_by: SimpleAuthor | None, choice_uuids: list[str]):
        super().__init__(
            path=path,
            created_at=created_at,
            created_by=created_by,
            reply_type='MultiChoiceReply',
        )
        self.choice_uuids = choice_uuids

        self.choices: list[Choice] = []

    @property
    def value(self) -> list[str]:
        return self.choice_uuids

    def __iter__(self):
        return iter(self.choices)

    def __len__(self):
        return len(self.choices)

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)
        self.choices = [ctx.e.choices[key]
                        for key in self.choice_uuids
                        if key in ctx.e.choices]

    @property
    def item_title(self) -> str:
        return ', '.join((choice.label for choice in self.choices))

    @staticmethod
    def load(path: str, data: dict, **options):
        return MultiChoiceReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            choice_uuids=data['value']['value'],
        )


class IntegrationReply(Reply):

    def __init__(self, *, path: str, created_at: datetime.datetime,
                 created_by: SimpleAuthor | None,  value: str, value_type: str,
                 item_id: str | None, raw: typing.Any | None = None):
        super().__init__(
            path=path,
            created_at=created_at,
            created_by=created_by,
            reply_type='IntegrationReply',
        )
        self.type = value_type
        self.item_id = item_id
        self.raw = raw
        self.value = value

    @property
    def id(self) -> str | None:
        return self.item_id

    @property
    def is_plain(self) -> bool:
        return self.type == 'PlainType'

    @property
    def is_legacy_integration(self) -> bool:
        return self.type == 'IntegrationLegacyType'

    @property
    def is_integration(self) -> bool:
        return self.type == 'IntegrationType'

    @property
    def url(self) -> str | None:
        if not self.is_integration or self.item_id is None:
            return None
        if isinstance(self.question, IntegrationQuestion) \
                and isinstance(self.question.integration, ApiLegacyIntegration):
            return self.question.integration.item(self.item_id)
        return None

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)

    @property
    def item_title(self) -> str:
        non_empty_lines = list(filter(
            lambda line: len(line) > 0,
            strip_markdown(self.value).splitlines(),
        ))
        if len(non_empty_lines) > 0:
            return non_empty_lines[0]
        return super().item_title

    @staticmethod
    def load(path: str, data: dict, **options):
        return IntegrationReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            value_type=data['value']['type'],
            value=data['value']['value'].get('value', ''),
            item_id=data['value']['value'].get('id', None),
            raw=data['value']['value'].get('raw', None),
        )


class ItemSelectReply(Reply):

    def __init__(self, *, path: str, created_at: datetime.datetime,
                 created_by: SimpleAuthor | None, item_uuid: str):
        super().__init__(
            path=path,
            created_at=created_at,
            created_by=created_by,
            reply_type='ItemSelectReply',
        )
        self.item_uuid = item_uuid
        self._item_title: str = 'Item'

    @property
    def value(self) -> str:
        return self.item_uuid

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)

    @property
    def item_title(self) -> str:
        return self._item_title

    @item_title.setter
    def item_title(self, value: str):
        self._item_title = value

    @property
    def has_direct_item_title(self) -> bool:
        return False

    @staticmethod
    def load(path: str, data: dict, **options):
        return ItemSelectReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            item_uuid=data['value']['value'],
        )


class FileReply(Reply):

    def __init__(self, *, path: str, created_at: datetime.datetime,
                 created_by: SimpleAuthor | None, file_uuid: str):
        super().__init__(
            path=path,
            created_at=created_at,
            created_by=created_by,
            reply_type='FileReply',
        )
        self.file_uuid = file_uuid
        self.file: QuestionnaireFile | None = None

    @property
    def value(self) -> str:
        return self.file_uuid

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)
        self.file = ctx.questionnaire.files.get(self.file_uuid, None)
        if self.file is not None:
            self.file.reply = self

    @property
    def item_title(self) -> str:
        if self.file is not None:
            return self.file.name
        return super().item_title

    @staticmethod
    def load(path: str, data: dict, **options):
        return FileReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            file_uuid=data['value']['value'],
        )


class Answer:

    def __init__(self, *, uuid: str, label: str, advice: str | None,
                 metric_measures: list[MetricMeasure], followup_uuids: list[str],
                 annotations: AnnotationsT):
        self.uuid = uuid
        self.label = label
        self.advice = advice
        self.metric_measures = metric_measures
        self.followup_uuids = followup_uuids
        self.annotations = annotations

        self.followups: list[Question] = []
        self.parent: OptionsQuestion | None = None

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Answer):
            return False
        return other.uuid == self.uuid

    def resolve_links(self, ctx):
        self.followups = [ctx.e.questions[key]
                          for key in self.followup_uuids
                          if key in ctx.e.questions]
        for followup in self.followups:
            followup.parent = self
            followup.resolve_links(ctx)
        for mm in self.metric_measures:
            mm.resolve_links(ctx)

    @staticmethod
    def load(data: dict, **options):
        mm = [MetricMeasure.load(d, **options)
              for d in data['metricMeasures']]
        return Answer(
            uuid=data['uuid'],
            label=data['label'],
            advice=data['advice'],
            metric_measures=mm,
            followup_uuids=data['followUpUuids'],
            annotations=_load_annotations(data['annotations']),
        )


class Choice:

    def __init__(self, *, uuid: str, label: str, annotations: AnnotationsT):
        self.uuid = uuid
        self.label = label
        self.annotations = annotations

        self.parent: MultiChoiceQuestion | None = None

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Choice):
            return False
        return other.uuid == self.uuid

    @staticmethod
    def load(data: dict, **options):
        return Choice(
            uuid=data['uuid'],
            label=data['label'],
            annotations=_load_annotations(data['annotations']),
        )


class Question(abc.ABC):

    def __init__(self, *, uuid: str, q_type: str, title: str, text: str | None,
                 tag_uuids: list[str], reference_uuids: list[str],
                 expert_uuids: list[str], required_phase_uuid: str | None,
                 annotations: AnnotationsT):
        self.uuid = uuid
        self.type = q_type
        self.title = title
        self.text = text
        self.tag_uuids = tag_uuids
        self.reference_uuids = reference_uuids
        self.expert_uuids = expert_uuids
        self.required_phase_uuid = required_phase_uuid
        self.annotations = annotations

        self.is_required: bool | None = None
        self.parent: Chapter | ListQuestion | Answer | None = None
        self.replies: dict[str, Reply] = {}
        self.tags: list[Tag] = []
        self.references: list[Reference] = []
        self.experts: list[Expert] = []
        self.required_phase: Phase = PHASE_NEVER

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Question):
            return False
        return other.uuid == self.uuid

    def resolve_links_parent(self, ctx):
        self.tags = [ctx.e.tags[key]
                     for key in self.tag_uuids
                     if key in ctx.e.tags]
        self.experts = [ctx.e.experts[key]
                        for key in self.expert_uuids
                        if key in ctx.e.experts]
        self.references = [ctx.e.references[key]
                           for key in self.reference_uuids
                           if key in ctx.e.references]
        for ref in self.references:
            ref.resolve_links(ctx)
        if self.required_phase_uuid is None or ctx.current_phase is None:
            self.is_required = False
        else:
            self.required_phase = ctx.e.phases.get(self.required_phase_uuid, PHASE_NEVER)
            self.is_required = ctx.current_phase.order >= self.required_phase.order

    def resolve_links(self, ctx):
        pass

    @property
    def url_references(self) -> list[URLReference]:
        return [r for r in self.references if isinstance(r, URLReference)]

    @property
    def resource_page_references(self) -> list[ResourcePageReference]:
        return [r for r in self.references if isinstance(r, ResourcePageReference)]

    @property
    def cross_references(self) -> list[CrossReference]:
        return [r for r in self.references if isinstance(r, CrossReference)]

    @staticmethod
    @abc.abstractmethod
    def load(data: dict, **options):
        pass


class ValueQuestionValidation:
    SHORT_TYPE: dict[str, str] = {
        'MinLengthQuestionValidation': 'min-length',
        'MaxLengthQuestionValidation': 'max-length',
        'RegexQuestionValidation': 'regex',
        'OrcidQuestionValidation': 'orcid',
        'DoiQuestionValidation': 'doi',
        'MinNumberQuestionValidation': 'min',
        'MaxNumberQuestionValidation': 'max',
        'FromDateQuestionValidation': 'from-date',
        'ToDateQuestionValidation': 'to-date',
        'FromDateTimeQuestionValidation': 'from-datetime',
        'ToDateTimeQuestionValidation': 'to-datetime',
        'FromTimeQuestionValidation': 'from-time',
        'ToTimeQuestionValidation': 'to-time',
        'DomainQuestionValidation': 'domain',
    }
    VALUE_TYPE: dict[str, type | None] = {
        'MinLengthQuestionValidation': int,
        'MaxLengthQuestionValidation': int,
        'RegexQuestionValidation': str,
        'OrcidQuestionValidation': None,
        'DoiQuestionValidation': None,
        'MinNumberQuestionValidation': float,
        'MaxNumberQuestionValidation': float,
        'FromDateQuestionValidation': str,
        'ToDateQuestionValidation': str,
        'FromDateTimeQuestionValidation': str,
        'ToDateTimeQuestionValidation': str,
        'FromTimeQuestionValidation': str,
        'ToTimeQuestionValidation': str,
        'DomainQuestionValidation': str,
    }

    def __init__(self, *, validation_type: str, value: str | int | float | None = None):
        self.type = self.SHORT_TYPE.get(validation_type, 'unknown')
        self.full_type = validation_type
        self.value = value

    @staticmethod
    def load(data: dict, **options):
        return ValueQuestionValidation(
            validation_type=data['type'],
            value=data.get('value', None),
        )


class ValueQuestion(Question):

    def __init__(self, *, uuid: str, title: str, text: str | None,
                 tag_uuids: list[str], reference_uuids: list[str],
                 expert_uuids: list[str], required_phase_uuid: str | None,
                 value_type: str, annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            q_type='ValueQuestion',
            title=title,
            text=text,
            tag_uuids=tag_uuids,
            reference_uuids=reference_uuids,
            expert_uuids=expert_uuids,
            required_phase_uuid=required_phase_uuid,
            annotations=annotations,
        )
        self.value_type = value_type
        self.validations: list[ValueQuestionValidation] = []

    @property
    def a(self):
        return self.annotations

    @property
    def is_string(self):
        return self.value_type == 'StringQuestionValueType'

    @property
    def is_text(self):
        return self.value_type == 'TextQuestionValueType'

    @property
    def is_number(self):
        return self.value_type == 'NumberQuestionValueType'

    @property
    def is_email(self):
        return self.value_type == 'EmailQuestionValueType'

    @property
    def is_url(self):
        return self.value_type == 'UrlQuestionValueType'

    @property
    def is_color(self):
        return self.value_type == 'ColorQuestionValueType'

    @property
    def is_time(self):
        return self.value_type == 'TimeQuestionValueType'

    @property
    def is_datetime(self):
        return self.value_type == 'DateTimeQuestionValueType'

    @property
    def is_date(self):
        return self.value_type == 'DateQuestionValueType'

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)

    @staticmethod
    def load(data: dict, **options):
        question = ValueQuestion(
            uuid=data['uuid'],
            title=data['title'],
            text=data['text'],
            tag_uuids=data['tagUuids'],
            reference_uuids=data['referenceUuids'],
            expert_uuids=data['expertUuids'],
            required_phase_uuid=data['requiredPhaseUuid'],
            value_type=data['valueType'],
            annotations=_load_annotations(data['annotations']),
        )
        question.validations = [ValueQuestionValidation.load(d, **options)
                                for d in data['validations']]
        return question


class OptionsQuestion(Question):

    def __init__(self, *, uuid: str, title: str, text: str | None,
                 tag_uuids: list[str], reference_uuids: list[str],
                 expert_uuids: list[str], required_phase_uuid: str | None,
                 answer_uuids: list[str], annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            q_type='OptionsQuestion',
            title=title,
            text=text,
            tag_uuids=tag_uuids,
            reference_uuids=reference_uuids,
            expert_uuids=expert_uuids,
            required_phase_uuid=required_phase_uuid,
            annotations=annotations,
        )
        self.answer_uuids = answer_uuids

        self.answers: list[Answer] = []

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)
        self.answers = [ctx.e.answers[key]
                        for key in self.answer_uuids
                        if key in ctx.e.answers]
        for answer in self.answers:
            answer.parent = self
            answer.resolve_links(ctx)

    @staticmethod
    def load(data: dict, **options):
        return OptionsQuestion(
            uuid=data['uuid'],
            title=data['title'],
            text=data['text'],
            tag_uuids=data['tagUuids'],
            reference_uuids=data['referenceUuids'],
            expert_uuids=data['expertUuids'],
            required_phase_uuid=data['requiredPhaseUuid'],
            answer_uuids=data['answerUuids'],
            annotations=_load_annotations(data['annotations']),
        )


class MultiChoiceQuestion(Question):

    def __init__(self, *, uuid: str, title: str, text: str | None,
                 tag_uuids: list[str], reference_uuids: list[str],
                 expert_uuids: list[str], required_phase_uuid: str | None,
                 choice_uuids: list[str], annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            q_type='MultiChoiceQuestion',
            title=title,
            text=text,
            tag_uuids=tag_uuids,
            reference_uuids=reference_uuids,
            expert_uuids=expert_uuids,
            required_phase_uuid=required_phase_uuid,
            annotations=annotations,
        )
        self.choice_uuids = choice_uuids

        self.choices: list[Choice] = []

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)
        self.choices = [ctx.e.choices[key]
                        for key in self.choice_uuids
                        if key in ctx.e.choices]
        for choice in self.choices:
            choice.parent = self

    @staticmethod
    def load(data: dict, **options):
        return MultiChoiceQuestion(
            uuid=data['uuid'],
            title=data['title'],
            text=data['text'],
            tag_uuids=data['tagUuids'],
            reference_uuids=data['referenceUuids'],
            expert_uuids=data['expertUuids'],
            required_phase_uuid=data['requiredPhaseUuid'],
            choice_uuids=data['choiceUuids'],
            annotations=_load_annotations(data['annotations']),
        )


class ListQuestion(Question):

    def __init__(self, *, uuid: str, title: str, text: str,
                 tag_uuids: list[str], reference_uuids: list[str],
                 expert_uuids: list[str], required_phase_uuid: str | None,
                 followup_uuids: list[str], annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            q_type='ListQuestion',
            title=title,
            text=text,
            tag_uuids=tag_uuids,
            reference_uuids=reference_uuids,
            expert_uuids=expert_uuids,
            required_phase_uuid=required_phase_uuid,
            annotations=annotations,
        )
        self.followup_uuids = followup_uuids

        self.followups: list[Question] = []

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)
        self.followups = [ctx.e.questions[key]
                          for key in self.followup_uuids
                          if key in ctx.e.questions]
        for followup in self.followups:
            followup.parent = self
            followup.resolve_links(ctx)

    @staticmethod
    def load(data: dict, **options):
        return ListQuestion(
            uuid=data['uuid'],
            title=data['title'],
            text=data['text'],
            tag_uuids=data['tagUuids'],
            reference_uuids=data['referenceUuids'],
            expert_uuids=data['expertUuids'],
            required_phase_uuid=data['requiredPhaseUuid'],
            followup_uuids=data['itemTemplateQuestionUuids'],
            annotations=_load_annotations(data['annotations']),
        )


class IntegrationQuestion(Question):

    def __init__(self, *, uuid: str, title: str, text: str | None,
                 tag_uuids: list[str], reference_uuids: list[str],
                 expert_uuids: list[str], required_phase_uuid: str | None,
                 integration_uuid: str | None, variables: dict[str, str],
                 annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            q_type='IntegrationQuestion',
            title=title,
            text=text,
            tag_uuids=tag_uuids,
            reference_uuids=reference_uuids,
            expert_uuids=expert_uuids,
            required_phase_uuid=required_phase_uuid,
            annotations=annotations,
        )
        self.variables = variables
        self.integration_uuid = integration_uuid

        self.integration: Integration | None = None

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)
        self.integration = ctx.e.integrations.get(
            self.integration_uuid,
            None
        )

    @staticmethod
    def load(data: dict, **options):
        return IntegrationQuestion(
            uuid=data['uuid'],
            title=data['title'],
            text=data['text'],
            tag_uuids=data['tagUuids'],
            reference_uuids=data['referenceUuids'],
            expert_uuids=data['expertUuids'],
            required_phase_uuid=data['requiredPhaseUuid'],
            integration_uuid=data['integrationUuid'],
            variables=data['variables'],
            annotations=_load_annotations(data['annotations']),
        )


class ItemSelectQuestion(Question):

    def __init__(self, *, uuid: str, title: str, text: str | None,
                 tag_uuids: list[str], reference_uuids: list[str],
                 expert_uuids: list[str], required_phase_uuid: str | None,
                 list_question_uuid: str | None, annotations: AnnotationsT):
        super().__init__(
            uuid=uuid,
            q_type='ItemSelectQuestion',
            title=title,
            text=text,
            tag_uuids=tag_uuids,
            reference_uuids=reference_uuids,
            expert_uuids=expert_uuids,
            required_phase_uuid=required_phase_uuid,
            annotations=annotations,
        )
        self.list_question_uuid = list_question_uuid
        self.list_question = None

    def resolve_links(self, ctx):
        super().resolve_links_parent(ctx)
        self.list_question = ctx.e.questions.get(self.list_question_uuid, None)

    @staticmethod
    def load(data: dict, **options):
        return ItemSelectQuestion(
            uuid=data['uuid'],
            title=data['title'],
            text=data['text'],
            tag_uuids=data['tagUuids'],
            reference_uuids=data['referenceUuids'],
            expert_uuids=data['expertUuids'],
            required_phase_uuid=data['requiredPhaseUuid'],
            list_question_uuid=data['listQuestionUuid'],
            annotations=_load_annotations(data['annotations']),
        )


class FileQuestion(Question):

    def __init__(self, *, uuid, title, text, tag_uuids, reference_uuids,
                 expert_uuids, required_phase_uuid, max_size, file_types,
                 annotations):
        super().__init__(
            uuid=uuid,
            q_type='FileQuestion',
            title=title,
            text=text,
            tag_uuids=tag_uuids,
            reference_uuids=reference_uuids,
            expert_uuids=expert_uuids,
            required_phase_uuid=required_phase_uuid,
            annotations=annotations,
        )
        self.max_size = max_size
        self.file_types = file_types

    @staticmethod
    def load(data: dict, **options):
        return FileQuestion(
            uuid=data['uuid'],
            title=data['title'],
            text=data['text'],
            tag_uuids=data['tagUuids'],
            reference_uuids=data['referenceUuids'],
            expert_uuids=data['expertUuids'],
            required_phase_uuid=data['requiredPhaseUuid'],
            max_size=data['maxSize'],
            file_types=data['fileTypes'],
            annotations=_load_annotations(data['annotations']),
        )


class Chapter:

    def __init__(self, *, uuid: str, title: str, text: str | None,
                 question_uuids: list[str], annotations: AnnotationsT):
        self.uuid = uuid
        self.title = title
        self.text = text
        self.question_uuids = question_uuids
        self.annotations = annotations

        self.questions: list[Question] = []
        self.reports: list[ReportItem] = []

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Chapter):
            return False
        return other.uuid == self.uuid

    def resolve_links(self, ctx):
        self.questions = [ctx.e.questions[key]
                          for key in self.question_uuids
                          if key in ctx.e.questions]
        for question in self.questions:
            question.parent = self
            question.resolve_links(ctx)

    @staticmethod
    def load(data: dict, **options):
        return Chapter(
            uuid=data['uuid'],
            title=data['title'],
            text=data['text'],
            question_uuids=data['questionUuids'],
            annotations=_load_annotations(data['annotations']),
        )


_QUESTION_TYPES: dict[str, type[Question]] = {
    'OptionsQuestion': OptionsQuestion,
    'ListQuestion': ListQuestion,
    'ValueQuestion': ValueQuestion,
    'MultiChoiceQuestion': MultiChoiceQuestion,
    'IntegrationQuestion': IntegrationQuestion,
    'ItemSelectQuestion': ItemSelectQuestion,
    'FileQuestion': FileQuestion,
}


_REFERENCE_TYPES: dict[str, type[Reference]] = {
    'URLReference': URLReference,
    'ResourcePageReference': ResourcePageReference,
    'CrossReference': CrossReference,
}


_INTEGRATION_TYPES: dict[str, type[Integration]] = {
    'ApiIntegration': ApiIntegration,
    'ApiLegacyIntegration': ApiLegacyIntegration,
    'WidgetIntegration': WidgetIntegration,
}


_REPLY_TYPES: dict[str, type[Reply]] = {
    'AnswerReply': AnswerReply,
    'StringReply': StringReply,
    'ItemListReply': ItemListReply,
    'MultiChoiceReply': MultiChoiceReply,
    'IntegrationReply': IntegrationReply,
    'ItemSelectReply': ItemSelectReply,
    'FileReply': FileReply,
}


def _load_question(data: dict, **options):
    question_type = data['questionType']
    question_class = _QUESTION_TYPES.get(question_type, None)
    if question_class is None:
        raise ValueError(f'Unknown question type: {question_type}')
    return question_class.load(data, **options)


def _load_reference(data: dict, **options):
    reference_type = data['referenceType']
    reference_class = _REFERENCE_TYPES.get(reference_type, None)
    if reference_class is None:
        raise ValueError(f'Unknown reference type: {reference_type}')
    return reference_class.load(data, **options)


def _load_integration(data: dict, **options):
    integration_type = data['integrationType']
    integration_class = _INTEGRATION_TYPES.get(integration_type, None)
    if integration_class is None:
        raise ValueError(f'Unknown integration type: {integration_type}')
    return integration_class.load(data, **options)


def _load_reply(path: str, data: dict, **options):
    reply_type = data['value']['type']
    reply_class = _REPLY_TYPES.get(reply_type, None)
    if reply_class is None:
        raise ValueError(f'Unknown reply type: {reply_type}')
    return reply_class.load(path, data, **options)


class KnowledgeModelEntities:

    def __init__(self):
        self.chapters: dict[str, Chapter] = {}
        self.questions: dict[str, Question] = {}
        self.answers: dict[str, Answer] = {}
        self.choices: dict[str, Choice] = {}
        self.resource_collections: dict[str, ResourceCollection] = {}
        self.resource_pages: dict[str, ResourcePage] = {}
        self.references: dict[str, Reference] = {}
        self.experts: dict[str, Expert] = {}
        self.tags: dict[str, Tag] = {}
        self.metrics: dict[str, Metric] = {}
        self.phases: dict[str, Phase] = {}
        self.integrations: dict[str, Integration] = {}

    @staticmethod
    def load(data: dict, **options):
        e = KnowledgeModelEntities()
        e.chapters = {key: Chapter.load(d, **options)
                      for key, d in data['chapters'].items()}
        e.questions = {key: _load_question(d, **options)
                       for key, d in data['questions'].items()}
        e.answers = {key: Answer.load(d, **options)
                     for key, d in data['answers'].items()}
        e.choices = {key: Choice.load(d, **options)
                     for key, d in data['choices'].items()}
        e.resource_collections = {key: ResourceCollection.load(d, **options)
                                  for key, d in data['resourceCollections'].items()}
        e.resource_pages = {key: ResourcePage.load(d, **options)
                            for key, d in data['resourcePages'].items()}
        e.references = {key: _load_reference(d, **options)
                        for key, d in data['references'].items()}
        e.experts = {key: Expert.load(d, **options)
                     for key, d in data['experts'].items()}
        e.tags = {key: Tag.load(d, **options)
                  for key, d in data['tags'].items()}
        e.metrics = {key: Metric.load(d, **options)
                     for key, d in data['metrics'].items()}
        e.phases = {key: Phase.load(d, **options)
                    for key, d in data['phases'].items()}
        e.integrations = {key: _load_integration(d, **options)
                          for key, d in data['integrations'].items()}
        return e


class KnowledgeModel:

    def __init__(self, *, uuid: str, chapter_uuids: list[str], tag_uuids: list[str],
                 metric_uuids: list[str], phase_uuids: list[str], integration_uuids: list[str],
                 resource_collection_uuids: list[str], entities: KnowledgeModelEntities,
                 annotations: AnnotationsT):
        self.uuid = uuid
        self.entities = entities
        self.chapter_uuids = chapter_uuids
        self.tag_uuids = tag_uuids
        self.metric_uuids = metric_uuids
        self.phase_uuids = phase_uuids
        self.resource_collection_uuids = resource_collection_uuids
        self.integration_uuids = integration_uuids
        self.annotations = annotations

        self.chapters: list[Chapter] = []
        self.tags: list[Tag] = []
        self.metrics: list[Metric] = []
        self.phases: list[Phase] = []
        self.resource_collections: list[ResourceCollection] = []
        self.integrations: list[Integration] = []

    @property
    def a(self):
        return self.annotations

    @property
    def e(self):
        return self.entities

    def resolve_links(self, ctx):
        self.chapters = [ctx.e.chapters[key]
                         for key in self.chapter_uuids
                         if key in ctx.e.chapters]
        self.tags = [ctx.e.tags[key]
                     for key in self.tag_uuids
                     if key in ctx.e.tags]
        self.metrics = [ctx.e.metrics[key]
                        for key in self.metric_uuids
                        if key in ctx.e.metrics]
        self.phases = [ctx.e.phases[key]
                       for key in self.phase_uuids
                       if key in ctx.e.phases]
        self.resource_collections = [ctx.e.resource_collections[key]
                                     for key in self.resource_collection_uuids
                                     if key in ctx.e.resource_collections]
        self.integrations = [ctx.e.integrations[key]
                             for key in self.integration_uuids
                             if key in ctx.e.integrations]
        for index, phase in enumerate(self.phases, start=1):
            phase.order = index
        for chapter in self.chapters:
            chapter.resolve_links(ctx)
        for resource_collection in self.resource_collections:
            resource_collection.resolve_links(ctx)

    @staticmethod
    def load(data: dict, **options):
        return KnowledgeModel(
            uuid=data['uuid'],
            chapter_uuids=data['chapterUuids'],
            tag_uuids=data['tagUuids'],
            metric_uuids=data['metricUuids'],
            phase_uuids=data['phaseUuids'],
            integration_uuids=data['integrationUuids'],
            resource_collection_uuids=data['resourceCollectionUuids'],
            entities=KnowledgeModelEntities.load(data['entities'], **options),
            annotations=_load_annotations(data['annotations']),
        )


class ContextConfig:

    def __init__(self, *, client_url: str | None):
        self.client_url = client_url

    @staticmethod
    def load(data: dict, **options):
        return ContextConfig(
            client_url=data.get('clientUrl', None),
        )


class Document:

    def __init__(self, *, uuid: str, name: str, document_template_id: str, format_uuid: str,
                 created_by: User | None, created_at: datetime.datetime):
        self.uuid = uuid
        self.name = name
        self.document_template_id = document_template_id
        self.format_uuid = format_uuid
        self.created_by = created_by
        self.created_at = created_at

    @staticmethod
    def load(data: dict, **options):
        return Document(
            uuid=data['uuid'],
            name=data['name'],
            document_template_id=data['documentTemplateId'],
            format_uuid=data['formatUuid'],
            created_by=User.load(data['createdBy'], **options),
            created_at=_datetime(data['createdAt']),
        )


class QuestionnaireVersion:

    def __init__(self, *, uuid: str, event_uuid: str, name: str, description: str | None,
                 created_at: datetime.datetime, updated_at: datetime.datetime,
                 created_by: SimpleAuthor | None):
        self.uuid = uuid
        self.event_uuid = event_uuid
        self.name = name
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by = created_by

    @staticmethod
    def load(data: dict, **options):
        return QuestionnaireVersion(
            uuid=data['uuid'],
            event_uuid=data['eventUuid'],
            name=data['name'],
            description=data['description'] or '',
            created_at=_datetime(data['createdAt']),
            updated_at=_datetime(data['updatedAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options)
        )


class RepliesContainer:

    def __init__(self, *, replies: dict[str, Reply]):
        self.replies = replies

    def __getitem__(self, path: str) -> Reply | None:
        return self.get(path)

    def __len__(self) -> int:
        return len(self.replies)

    def get(self, path: str, default=None) -> Reply | None:
        return self.replies.get(path, default)

    def iterate_by_prefix(self, path_prefix: str) -> typing.Iterable[Reply]:
        return (r for path, r in self.replies.items() if path.startswith(path_prefix))

    def iterate_by_suffix(self, path_suffix: str) -> typing.Iterable[Reply]:
        return (r for path, r in self.replies.items() if path.endswith(path_suffix))

    def values(self) -> typing.Iterable[Reply]:
        return self.replies.values()

    def keys(self) -> typing.Iterable[str]:
        return self.replies

    def items(self) -> typing.ItemsView[str, Reply]:
        return self.replies.items()


class QuestionnaireFile:

    def __init__(self, *, uuid: str, file_name: str, file_size: int,
                 content_type: str):
        self.uuid = uuid
        self.name = file_name
        self.size = file_size
        self.content_type = content_type

        self.reply: FileReply | None = None
        self.download_url: str = ''
        self.questionnaire_uuid: str | None = None

    def resolve_links(self, ctx):
        self.questionnaire_uuid = ctx.questionnaire.uuid
        client_url = ctx.config.client_url
        self.download_url = (f'{client_url}/projects/{self.questionnaire_uuid}'
                             f'/files/{self.uuid}/download')

    @staticmethod
    def load(data: dict, **options):
        return QuestionnaireFile(
            uuid=data['uuid'],
            file_name=data['fileName'],
            file_size=data['fileSize'],
            content_type=data['contentType'],
        )


class Questionnaire:

    def __init__(self, *, uuid: str, name: str, description: str | None,
                 created_by: User, phase_uuid: str | None,
                 created_at: datetime.datetime, updated_at: datetime.datetime):
        self.uuid = uuid
        self.name = name
        self.description = description
        self.created_by = created_by
        self.phase_uuid = phase_uuid
        self.created_at = created_at
        self.updated_at = updated_at

        self.version: QuestionnaireVersion | None = None
        self.versions: list[QuestionnaireVersion] = []
        self.files: dict[str, QuestionnaireFile] = {}
        self.todos: list[str] = []
        self.project_tags: list[str] = []
        self.phase: Phase = PHASE_NEVER

        self.replies: RepliesContainer = RepliesContainer(replies={})

    def resolve_links(self, ctx):
        for reply in self.replies.values():
            reply.resolve_links(ctx)
        for questionnaire_file in self.files.values():
            questionnaire_file.resolve_links(ctx)

    @staticmethod
    def load(data: dict, **options):
        questionnaire_uuid = data['uuid']
        versions = [QuestionnaireVersion.load(d, **options)
                    for d in data['versions']]
        version = None
        replies = {p: _load_reply(p, d, **options)
                   for p, d in data['replies'].items()}
        files = {d['uuid']: QuestionnaireFile.load(d, **options)
                 for d in data.get('files', [])}
        for v in versions:
            if v.uuid == data['versionUuid']:
                version = v
        qtn = Questionnaire(
            uuid=questionnaire_uuid,
            name=data['name'],
            description=data['description'] or '',
            created_by=User.load(data['createdBy'], **options),
            phase_uuid=data['phaseUuid'],
            created_at=_datetime(data['createdAt']),
            updated_at=_datetime(data['updatedAt']),
        )
        qtn.version = version
        qtn.versions = versions
        qtn.files = files
        qtn.project_tags = data.get('projectTags', [])
        qtn.replies.replies = replies
        qtn.todos = [k for k, v in data.get('labels', {}).items() if TODO_LABEL_UUID in v]
        return qtn


class Package:

    def __init__(self, *, org_id: str, km_id: str, version: str, versions: list[str],
                 name: str, description: str, created_at: datetime.datetime):
        self.organization_id = org_id
        self.km_id = km_id
        self.version = version
        self.versions = versions
        self.name = name
        self.description = description
        self.created_at = created_at

        self.id: str = f'{org_id}:{km_id}:{version}'

    @property
    def org_id(self):
        return self.organization_id

    @staticmethod
    def load(data: dict, **options):
        return Package(
            org_id=data['organizationId'],
            km_id=data['kmId'],
            version=data['version'],
            versions=data['versions'],
            name=data['name'],
            description=data.get('description', ''),
            created_at=_datetime(data['createdAt']),
        )


class ReportIndication:

    def __init__(self, *, indication_type: str, answered: int, unanswered: int):
        self.indication_type = indication_type
        self.answered = answered
        self.unanswered = unanswered

    @property
    def total(self) -> int:
        return self.answered + self.unanswered

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0
        return self.answered / self.total

    @property
    def is_for_phase(self):
        return self.indication_type == 'PhasesAnsweredIndication'

    @property
    def is_overall(self):
        return self.indication_type == 'AnsweredIndication'

    @staticmethod
    def load(data: dict, **options):
        return ReportIndication(
            indication_type=data['indicationType'],
            answered=int(data['answeredQuestions']),
            unanswered=int(data['unansweredQuestions']),
        )


class ReportMetric:

    def __init__(self, *, measure: float, metric_uuid: str):
        self.measure = measure
        self.metric_uuid = metric_uuid

        self.metric: Metric | None = None

    def resolve_links(self, ctx):
        if self.metric_uuid in ctx.e.metrics:
            self.metric = ctx.e.metrics[self.metric_uuid]

    @staticmethod
    def load(data: dict, **options):
        return ReportMetric(
            measure=float(data['measure']),
            metric_uuid=data['metricUuid'],
        )


class ReportItem:

    def __init__(self, *, indications: list[ReportIndication], metrics: list[ReportMetric],
                 chapter_uuid: str | None):
        self.indications = indications
        self.metrics = metrics
        self.chapter_uuid = chapter_uuid

        self.chapter: Chapter | None = None

    def resolve_links(self, ctx):
        for m in self.metrics:
            m.resolve_links(ctx)
        if self.chapter_uuid is not None and self.chapter_uuid in ctx.e.chapters:
            self.chapter = ctx.e.chapters[self.chapter_uuid]
            if self.chapter is not None:
                self.chapter.reports.append(self)

    @staticmethod
    def load(data: dict, **options):
        return ReportItem(
            indications=[ReportIndication.load(d, **options)
                         for d in data['indications']],
            metrics=[ReportMetric.load(d, **options)
                     for d in data['metrics']],
            chapter_uuid=data.get('chapterUuid', None),
        )


class Report:

    def __init__(self, *, uuid: str, created_at: datetime.datetime,
                 updated_at: datetime.datetime, chapter_reports: list[ReportItem],
                 total_report: ReportItem):
        self.uuid = uuid
        self.created_at = created_at
        self.updated_at = updated_at
        self.total_report = total_report
        self.chapter_reports = chapter_reports

    def resolve_links(self, ctx):
        self.total_report.resolve_links(ctx)
        for report in self.chapter_reports:
            report.resolve_links(ctx)

    @staticmethod
    def load(data: dict, **options):
        return Report(
            uuid=data['uuid'],
            created_at=_datetime(data['createdAt']),
            updated_at=_datetime(data['updatedAt']),
            total_report=ReportItem.load(data['totalReport'], **options),
            chapter_reports=[ReportItem.load(d, **options)
                             for d in data['chapterReports']],
        )


class UserGroup:

    def __init__(self, *, uuid: str, name: str, description: str | None, private: bool,
                 created_at: datetime.datetime, updated_at: datetime.datetime):
        self.uuid = uuid
        self.name = name
        self.description = description
        self.private = private
        self.created_at = created_at
        self.updated_at = updated_at

        self.members: list[UserGroupMember] = []

    @staticmethod
    def load(data: dict, **options):
        ug = UserGroup(
            uuid=data['uuid'],
            name=data['name'],
            description=data['description'],
            private=data['private'],
            created_at=_datetime(data['createdAt']),
            updated_at=_datetime(data['updatedAt']),
        )
        ug.members = [UserGroupMember.load(d, **options)
                      for d in data.get('users', [])]
        return ug


class UserGroupMember:

    def __init__(self, *, uuid: str, first_name: str, last_name: str, gravatar_hash: str,
                 image_url: str | None, membership_type: str):
        self.uuid = uuid
        self.first_name = first_name
        self.last_name = last_name
        self.gravatar_hash = gravatar_hash
        self.image_url = image_url
        self.membership_type = membership_type

    @staticmethod
    def load(data: dict, **options):
        membership = 'member'
        if 'owner' in data['membershipType'].lower():
            membership = 'owner'
        return UserGroupMember(
            uuid=data['uuid'],
            first_name=data['firstName'],
            last_name=data['lastName'],
            gravatar_hash=data['gravatarHash'],
            image_url=data['imageUrl'],
            membership_type=membership,
        )


class DocumentContextUserPermission:

    def __init__(self, *, user: User | None, permissions: list[str]):
        self.user = user
        self.permissions = permissions

    @property
    def is_viewer(self):
        return 'VIEW' in self.permissions

    @property
    def is_commenter(self):
        return 'COMMENT' in self.permissions

    @property
    def is_editor(self):
        return 'EDIT' in self.permissions

    @property
    def is_owner(self):
        return 'ADMIN' in self.permissions

    @staticmethod
    def load(data: dict, **options):
        return DocumentContextUserPermission(
            user=User.load(data['user'], **options),
            permissions=data['perms'],
        )


class DocumentContextUserGroupPermission:

    def __init__(self, *, group: UserGroup | None, permissions: list[str]):
        self.group = group
        self.permissions = permissions

    @property
    def is_viewer(self):
        return 'VIEW' in self.permissions

    @property
    def is_commenter(self):
        return 'COMMENT' in self.permissions

    @property
    def is_editor(self):
        return 'EDIT' in self.permissions

    @property
    def is_owner(self):
        return 'ADMIN' in self.permissions

    @staticmethod
    def load(data: dict, **options):
        return DocumentContextUserGroupPermission(
            group=UserGroup.load(data['group'], **options),
            permissions=data['perms'],
        )


class DocumentContext:
    """Document Context smart representation"""

    def __init__(self, *, ctx, **options):
        check_metamodel_version(
            metamodel_version=str(ctx.get('metamodelVersion', '0')),
        )
        self.config = ContextConfig.load(ctx['config'], **options)
        self.km = KnowledgeModel.load(ctx['knowledgeModel'], **options)
        self.questionnaire = Questionnaire.load(ctx['questionnaire'], **options)
        self.report = Report.load(ctx['report'], **options)
        self.document = Document.load(ctx['document'], **options)
        self.package = Package.load(ctx['package'], **options)
        self.organization = Organization.load(ctx['organization'], **options)
        self.current_phase: Phase = PHASE_NEVER

        self.users = [DocumentContextUserPermission.load(d, **options)
                      for d in ctx['users']]
        self.groups = [DocumentContextUserGroupPermission.load(d, **options)
                       for d in ctx['groups']]

    @property
    def e(self) -> KnowledgeModelEntities:
        return self.km.entities

    @property
    def cfg(self) -> ContextConfig:
        return self.config

    @property
    def qtn(self) -> Questionnaire:
        return self.questionnaire

    @property
    def org(self) -> Organization:
        return self.organization

    @property
    def pkg(self) -> Package:
        return self.package

    @property
    def doc(self) -> Document:
        return self.document

    @property
    def replies(self) -> RepliesContainer:
        return self.questionnaire.replies

    def resolve_links(self):
        phase_uuid = self.questionnaire.phase_uuid
        if phase_uuid is not None and phase_uuid in self.e.phases:
            self.current_phase = self.e.phases[phase_uuid]
        self.questionnaire.phase = self.current_phase
        self.km.resolve_links(self)
        self.report.resolve_links(self)
        self.questionnaire.resolve_links(self)

        rv = ReplyVisitor(context=self)
        rv.visit()
        for reply in self.replies.values():
            if isinstance(reply, ItemSelectReply):
                reply.item_title = rv.item_titles.get(reply.item_uuid, 'Item')


class ReplyVisitor:

    def __init__(self, *, context: DocumentContext):
        self.item_titles: dict[str, str] = {}
        self.item_same_as: dict[str, str] = {}
        self._set_also: dict[str, list[str]] = {}
        self.context = context

    def visit(self):
        for chapter in self.context.km.chapters:
            self._visit_chapter(chapter)
        self._post_process_item_titles()

    def _visit_chapter(self, chapter: Chapter):
        for question in chapter.questions:
            self._visit_question(question, path=chapter.uuid)

    def _visit_question(self, question: Question, path: str):
        new_path = f'{path}.{question.uuid}'
        if isinstance(question, ListQuestion):
            self._visit_list_question(question, new_path)
        elif isinstance(question, OptionsQuestion):
            self._visit_options_question(new_path)

    def _visit_list_question(self, question: ListQuestion, path: str):
        reply = self.context.replies.get(path)
        if reply is None or not isinstance(reply, ItemListReply):
            return
        for n, item_uuid in enumerate(reply.items, start=1):
            item_path = f'{path}.{item_uuid}'
            self.item_titles[item_uuid] = f'Item {n}'
            self._prepare_item_title(question, item_uuid, item_path)

            for followup in question.followups:
                self._visit_question(followup, path=item_path)

    def _visit_options_question(self, path: str):
        reply = self.context.replies.get(path)
        if reply is None or not isinstance(reply, AnswerReply) or reply.answer is None:
            return

        new_path = f'{path}.{reply.answer_uuid}'
        for followup in reply.answer.followups:
            self._visit_question(followup, path=new_path)

    def _prepare_item_title(self, question: ListQuestion, item_uuid: str, item_path: str):
        if len(question.followups) == 0:
            return
        followup = question.followups[0]
        followup_path = f'{item_path}.{followup.uuid}'

        reply = self.context.replies.get(followup_path)
        if reply is None:
            return

        if isinstance(reply, ItemListReply) and len(reply.items) > 0:
            self.item_same_as[item_uuid] = reply.items[0]
        elif isinstance(reply, ItemSelectReply) and reply.item_uuid:
            self.item_same_as[item_uuid] = reply.item_uuid
        elif reply.has_direct_item_title:
            self.item_titles[item_uuid] = reply.item_title

    def _post_process_item_titles(self):
        to_process = list(self.item_same_as.keys())
        while len(to_process) > 0:
            item_uuid = to_process.pop()
            visited = set()
            target_item_uuid = item_uuid
            visited.add(target_item_uuid)
            while target_item_uuid in self.item_same_as:
                same_as = self.item_same_as[target_item_uuid]
                if same_as in visited:
                    break
                visited.add(same_as)
                target_item_uuid = same_as
            if target_item_uuid in self.item_titles:
                self.item_titles[item_uuid] = self.item_titles[target_item_uuid]
