# TODO: move to dsw-models
import datetime
import dateutil.parser as dp

from typing import Optional, Iterable, Union, ItemsView

from ..consts import NULL_UUID

AnnotationsT = dict[str, Union[str, list[str]]]
TODO_LABEL_UUID = "615b9028-5e3f-414f-b245-12d2ae2eeb20"


def _datetime(timestamp: str) -> datetime.datetime:
    return dp.isoparse(timestamp)


def _load_annotations(annotations: list[dict[str, str]]) -> AnnotationsT:
    result = {}  # type: AnnotationsT
    semi_result = {}  # type: dict[str, list[str]]
    for item in annotations:
        key = item.get('key', '')
        value = item.get('value', '')
        if key in semi_result.keys():
            semi_result[key].append(value)
        else:
            semi_result[key] = [value]
    for key, value_list in semi_result.items():
        if len(value_list) == 1:
            result[key] = value_list[0]
        else:
            result[key] = value_list
    return result


class Tag:

    def __init__(self, uuid, name, description, color, annotations):
        self.uuid = uuid  # type: str
        self.name = name  # type: str
        self.description = description  # type: Optional[str]
        self.color = color  # type: str
        self.annotations = annotations  # type: AnnotationsT

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

    def __init__(self, uuid, title, page_uuids, annotations):
        self.uuid = uuid  # type: str
        self.title = title  # type: str
        self.page_uuids = page_uuids  # type: list[str]
        self.pages = list()  # type: list[ResourcePage]
        self.annotations = annotations  # type: AnnotationsT

    def _resolve_links(self, ctx):
        self.pages = [ctx.e.resource_pages[key]
                      for key in self.page_uuids
                      if key in ctx.e.resource_pages.keys()]
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

    def __init__(self, uuid, title, content, annotations):
        self.uuid = uuid  # type: str
        self.title = title  # type: str
        self.content = content  # type: str
        self.collection = None  # type: Optional[ResourceCollection]
        self.annotations = annotations  # type: AnnotationsT

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


class Integration:

    def __init__(self, uuid, name, logo, integration_id, item_url, props,
                 integration_type, annotations):
        self.uuid = uuid  # type: str
        self.name = name  # type: str
        self.id = integration_id  # type: str
        self.item_url = item_url  # type: Optional[str]
        self.logo = logo  # type: Optional[str]
        self.props = props  # type: list[str]
        self.type = integration_type  # type: str
        self.annotations = annotations  # type: AnnotationsT

    @property
    def a(self):
        return self.annotations

    def item(self, item_id: str) -> Optional[str]:
        if self.item_url is None:
            return None
        return self.item_url.replace('${id}', item_id)

    def __eq__(self, other):
        if not isinstance(other, Integration):
            return False
        return other.uuid == self.uuid


class ApiIntegration(Integration):

    def __init__(self, uuid, name, logo, integration_id, item_url, props, rq_body,
                 rq_headers, rq_method, rq_url, rs_list_field, rs_item_id,
                 rs_item_template, annotations):
        super().__init__(
            uuid=uuid,
            name=name,
            logo=logo,
            integration_id=integration_id,
            item_url=item_url,
            props=props,
            annotations=annotations,
            integration_type='ApiIntegration',
        )
        self.rq_body = rq_body  # type: str
        self.rq_method = rq_method  # type: str
        self.rq_url = rq_url  # type: str
        self.rq_headers = rq_headers  # type: dict[str, str]
        self.rs_list_field = rs_list_field  # type: Optional[str]
        self.rs_item_id = rs_item_id  # type: Optional[str]
        self.rs_item_template = rs_item_template  # type: str

    @staticmethod
    def default():
        return ApiIntegration(
            uuid=NULL_UUID,
            name='',
            logo='',
            integration_id='',
            item_url='',
            props=[],
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
        return ApiIntegration(
            uuid=data['uuid'],
            name=data['name'],
            integration_id=data['id'],
            item_url=data['itemUrl'],
            logo=data['logo'],
            props=data['props'],
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

    def __init__(self, uuid, name, logo, integration_id, item_url, props,
                 widget_url, annotations):
        super().__init__(
            uuid=uuid,
            name=name,
            logo=logo,
            integration_id=integration_id,
            item_url=item_url,
            props=props,
            annotations=annotations,
            integration_type='WidgetIntegration',
        )
        self.widget_url = widget_url  # type: str

    @staticmethod
    def load(data: dict, **options):
        return WidgetIntegration(
            uuid=data['uuid'],
            name=data['name'],
            integration_id=data['id'],
            item_url=data['itemUrl'],
            logo=data['logo'],
            props=data['props'],
            widget_url=data['widgetUrl'],
            annotations=_load_annotations(data['annotations']),
        )


class Phase:

    def __init__(self, uuid, title, description, annotations, order=0):
        self.uuid = uuid  # type: str
        self.title = title  # type: str
        self.description = description  # type: Optional[str]
        self.order = order  # type: int
        self.annotations = annotations  # type: AnnotationsT

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

    def __init__(self, uuid, title, description, abbreviation, annotations):
        self.uuid = uuid  # type: str
        self.title = title  # type: str
        self.description = description  # type: Optional[str]
        self.abbreviation = abbreviation  # type: str
        self.annotations = annotations  # type: AnnotationsT

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

    def __init__(self, measure, weight, metric_uuid):
        self.measure = measure  # type: float
        self.weight = weight  # type: float
        self.metric_uuid = metric_uuid  # type: str
        self.metric = None  # type: Optional[Metric]

    def _resolve_links(self, ctx):
        if self.metric_uuid in ctx.e.metrics.keys():
            self.metric = ctx.e.metrics[self.metric_uuid]

    @staticmethod
    def load(data: dict, **options):
        return MetricMeasure(
            measure=float(data['measure']),
            weight=float(data['weight']),
            metric_uuid=data['metricUuid'],
        )


class Reference:

    def __init__(self, uuid, ref_type, annotations):
        self.uuid = uuid  # type: str
        self.type = ref_type  # type: str
        self.annotations = annotations  # type: AnnotationsT

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Reference):
            return False
        return other.uuid == self.uuid

    def _resolve_links(self, ctx):
        pass


class CrossReference(Reference):

    def __init__(self, uuid, target_uuid, description, annotations):
        super().__init__(uuid, 'CrossReference', annotations)
        self.target_uuid = target_uuid  # type: str
        self.description = description  # type: str

    @staticmethod
    def load(data: dict, **options):
        return CrossReference(
            uuid=data['uuid'],
            target_uuid=data['targetUuid'],
            description=data['description'],
            annotations=_load_annotations(data['annotations']),
        )


class URLReference(Reference):

    def __init__(self, uuid, label, url, annotations):
        super().__init__(uuid, 'URLReference', annotations)
        self.label = label  # type: str
        self.url = url  # type: str

    @staticmethod
    def load(data: dict, **options):
        return URLReference(
            uuid=data['uuid'],
            label=data['label'],
            url=data['url'],
            annotations=_load_annotations(data['annotations']),
        )


class ResourcePageReference(Reference):

    def __init__(self, uuid, resource_page_uuid, annotations):
        super().__init__(uuid, 'ResourcePageReference', annotations)
        self.resource_page_uuid = resource_page_uuid  # type: Optional[str]
        self.resource_page = None  # type: Optional[ResourcePage]

    def _resolve_links(self, ctx):
        if self.resource_page_uuid in ctx.e.resource_pages.keys():
            self.resource_page = ctx.e.resource_pages[self.resource_page_uuid]

    @staticmethod
    def load(data: dict, **options):
        return ResourcePageReference(
            uuid=data['uuid'],
            resource_page_uuid=data['resourcePageUuid'],
            annotations=_load_annotations(data['annotations']),
        )


class Expert:

    def __init__(self, uuid, name, email, annotations):
        self.uuid = uuid  # type: str
        self.name = name  # type: str
        self.email = email  # type: str
        self.annotations = annotations  # type: AnnotationsT

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


class Reply:

    def __init__(self, path, created_at, created_by, reply_type):
        self.path = path  # type: str
        self.fragments = path.split('.')  # type: list[str]
        self.created_at = created_at  # type: datetime.datetime
        self.created_by = created_by  # type: Optional[SimpleAuthor]
        self.type = reply_type  # type: str
        self.question = None  # type: Optional[Question]

    def _resolve_links_parent(self, ctx):
        question_uuid = self.fragments[-1]
        if question_uuid in ctx.e.questions.keys():
            self.question = ctx.e.questions.get(question_uuid, None)
            if self.question is not None:
                self.question.replies[self.path] = self

    def _resolve_links(self, ctx):
        pass


class AnswerReply(Reply):

    def __init__(self, path, created_at, created_by, answer_uuid):
        super().__init__(path, created_at, created_by, 'AnswerReply')
        self.answer_uuid = answer_uuid  # type: str
        self.answer = None  # type: Optional[Answer]

    @property
    def value(self) -> Optional[str]:
        return self.answer_uuid

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)
        self.answer = ctx.e.answers.get(self.answer_uuid, None)

    @staticmethod
    def load(path: str, data: dict, **options):
        return AnswerReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            answer_uuid=data['value']['value'],
        )


class StringReply(Reply):

    def __init__(self, path, created_at, created_by, value):
        super().__init__(path, created_at, created_by, 'StringReply')
        self.value = value  # type: str

    @property
    def as_number(self) -> Optional[float]:
        try:
            return float(self.value)
        except Exception:
            return None

    @property
    def as_datetime(self) -> Optional[datetime.datetime]:
        try:
            return dp.parse(self.value)
        except Exception:
            return None

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)

    @staticmethod
    def load(path: str, data: dict, **options):
        return StringReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            value=data['value']['value'],
        )


class ItemListReply(Reply):

    def __init__(self, path, created_at, created_by, items):
        super().__init__(path, created_at, created_by, 'ItemListReply')
        self.items = items  # type: list[str]

    @property
    def value(self) -> list[str]:
        return self.items

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)

    @staticmethod
    def load(path: str, data: dict, **options):
        return ItemListReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            items=data['value']['value'],
        )


class MultiChoiceReply(Reply):

    def __init__(self, path, created_at, created_by, choice_uuids):
        super().__init__(path, created_at, created_by, 'MultiChoiceReply')
        self.choice_uuids = choice_uuids  # type: list[str]
        self.choices = list()  # type: list[Choice]

    @property
    def value(self) -> list[str]:
        return self.choice_uuids

    def __iter__(self):
        return iter(self.choices)

    def __len__(self):
        return len(self.choices)

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)
        self.choices = [ctx.e.choices[key]
                        for key in self.choice_uuids
                        if key in ctx.e.choices.keys()]

    @staticmethod
    def load(path: str, data: dict, **options):
        return MultiChoiceReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            choice_uuids=data['value']['value'],
        )


class IntegrationReply(Reply):

    def __init__(self, path, created_at, created_by, item_id, value):
        super().__init__(path, created_at, created_by, 'IntegrationReply')
        self.item_id = item_id  # type: Optional[str]
        self.value = value  # type: str

    @property
    def id(self) -> Optional[str]:
        return self.item_id

    @property
    def is_plain(self) -> bool:
        return self.item_id is None

    @property
    def is_integration(self) -> bool:
        return not self.is_plain

    @property
    def url(self) -> Optional[str]:
        if not self.is_integration or self.item_id is None:
            return None
        if isinstance(self.question, IntegrationQuestion) \
                and self.question.integration is not None:
            return self.question.integration.item(self.item_id)
        return None

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)

    @staticmethod
    def load(path: str, data: dict, **options):
        return IntegrationReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            item_id=data['value']['value'].get('id', None),
            value=data['value']['value']['value'],
        )


class ItemSelectReply(Reply):

    def __init__(self, path, created_at, created_by, item_uuid):
        super().__init__(path, created_at, created_by, 'ItemSelectReply')
        self.item_uuid = item_uuid  # type: str
        self.item_title = 'Item'  # type: str

    @property
    def value(self) -> str:
        return self.item_uuid

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)

    @staticmethod
    def load(path: str, data: dict, **options):
        return ItemSelectReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            item_uuid=data['value']['value'],
        )


class FileReply(Reply):

    def __init__(self, path, created_at, created_by, file_uuid):
        super().__init__(path, created_at, created_by, 'FileReply')
        self.file_uuid = file_uuid  # type: str
        self.file = None  # type: Optional[QuestionnaireFile]

    @property
    def value(self) -> str:
        return self.file_uuid

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)
        self.file = ctx.questionnaire.files.get(self.file_uuid, None)
        if self.file is not None:
            self.file.reply = self

    @staticmethod
    def load(path: str, data: dict, **options):
        return FileReply(
            path=path,
            created_at=_datetime(data['createdAt']),
            created_by=SimpleAuthor.load(data['createdBy'], **options),
            file_uuid=data['value']['value'],
        )


class Answer:

    def __init__(self, uuid, label, advice, metric_measures, followup_uuids,
                 annotations):
        self.uuid = uuid  # type: str
        self.label = label  # type: str
        self.advice = advice  # type: Optional[str]
        self.metric_measures = metric_measures  # type: list[MetricMeasure]
        self.followup_uuids = followup_uuids  # type: list[str]
        self.followups = list()  # type: list[Question]
        self.parent = None  # type: Optional[OptionsQuestion]
        self.annotations = annotations  # type: AnnotationsT

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Answer):
            return False
        return other.uuid == self.uuid

    def _resolve_links(self, ctx):
        self.followups = [ctx.e.questions[key]
                          for key in self.followup_uuids
                          if key in ctx.e.questions.keys()]
        for followup in self.followups:
            followup.parent = self
            followup._resolve_links(ctx)
        for mm in self.metric_measures:
            mm._resolve_links(ctx)

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

    def __init__(self, uuid, label, annotations):
        self.uuid = uuid  # type: str
        self.label = label  # type: str
        self.parent = None  # type: Optional[MultiChoiceQuestion]
        self.annotations = annotations  # type: AnnotationsT

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


class Question:

    def __init__(self, uuid, q_type, title, text, tag_uuids, reference_uuids,
                 expert_uuids, required_phase_uuid, annotations):
        self.uuid = uuid  # type: str
        self.type = q_type  # type: str
        self.title = title  # type: str
        self.text = text  # type: Optional[str]
        self.tag_uuids = tag_uuids  # type: list[str]
        self.tags = list()  # type: list[Tag]
        self.reference_uuids = reference_uuids  # type: list[str]
        self.references = list()  # type: list[Reference]
        self.expert_uuids = expert_uuids  # type: list[str]
        self.experts = list()  # type: list[Expert]
        self.required_phase_uuid = required_phase_uuid  # type: Optional[str]
        self.required_phase = PHASE_NEVER  # type: Phase
        self.replies = dict()  # type: dict[str, Reply]  # added from replies
        self.is_required = None  # type: Optional[bool]
        self.parent = None  # type: Optional[Union[Chapter, ListQuestion, Answer]]
        self.annotations = annotations  # type: AnnotationsT

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Question):
            return False
        return other.uuid == self.uuid

    def _resolve_links_parent(self, ctx):
        self.tags = [ctx.e.tags[key]
                     for key in self.tag_uuids
                     if key in ctx.e.tags.keys()]
        self.experts = [ctx.e.experts[key]
                        for key in self.expert_uuids
                        if key in ctx.e.experts.keys()]
        self.references = [ctx.e.references[key]
                           for key in self.reference_uuids
                           if key in ctx.e.references.keys()]
        for ref in self.references:
            ref._resolve_links(ctx)
        if self.required_phase_uuid is None or ctx.current_phase is None:
            self.is_required = False
        else:
            self.required_phase = ctx.e.phases.get(self.required_phase_uuid, PHASE_NEVER)
            self.is_required = ctx.current_phase.order >= self.required_phase.order

    def _resolve_links(self, ctx):
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

    def __init__(self, validation_type: str, value: str | int | float | None = None):
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

    def __init__(self, uuid, title, text, tag_uuids, reference_uuids,
                 expert_uuids, required_phase_uuid, value_type, annotations):
        super().__init__(uuid, 'ValueQuestion', title, text, tag_uuids,
                         reference_uuids, expert_uuids, required_phase_uuid,
                         annotations)
        self.value_type = value_type  # type: str
        self.validations = list()  # type: list[ValueQuestionValidation]

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

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)

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

    def __init__(self, uuid, title, text, tag_uuids, reference_uuids,
                 expert_uuids, required_phase_uuid, answer_uuids,
                 annotations):
        super().__init__(uuid, 'OptionsQuestion', title, text, tag_uuids,
                         reference_uuids, expert_uuids, required_phase_uuid,
                         annotations)
        self.answer_uuids = answer_uuids  # type: list[str]
        self.answers = list()  # type: list[Answer]

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)
        self.answers = [ctx.e.answers[key]
                        for key in self.answer_uuids
                        if key in ctx.e.answers.keys()]
        for answer in self.answers:
            answer.parent = self
            answer._resolve_links(ctx)

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

    def __init__(self, uuid, title, text, tag_uuids, reference_uuids,
                 expert_uuids, required_phase_uuid, choice_uuids,
                 annotations):
        super().__init__(uuid, 'MultiChoiceQuestion', title, text, tag_uuids,
                         reference_uuids, expert_uuids, required_phase_uuid,
                         annotations)
        self.choice_uuids = choice_uuids  # type: list[str]
        self.choices = list()  # type: list[Choice]

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)
        self.choices = [ctx.e.choices[key]
                        for key in self.choice_uuids
                        if key in ctx.e.choices.keys()]
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

    def __init__(self, uuid, title, text, tag_uuids, reference_uuids,
                 expert_uuids, required_phase_uuid, followup_uuids,
                 annotations):
        super().__init__(uuid, 'ListQuestion', title, text, tag_uuids,
                         reference_uuids, expert_uuids, required_phase_uuid,
                         annotations)
        self.followup_uuids = followup_uuids  # type: list[str]
        self.followups = list()  # type: list[Question]

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)
        self.followups = [ctx.e.questions[key]
                          for key in self.followup_uuids
                          if key in ctx.e.questions.keys()]
        for followup in self.followups:
            followup.parent = self
            followup._resolve_links(ctx)

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

    def __init__(self, uuid, title, text, tag_uuids, reference_uuids, props,
                 expert_uuids, required_phase_uuid, integration_uuid,
                 annotations):
        super().__init__(uuid, 'IntegrationQuestion', title, text, tag_uuids,
                         reference_uuids, expert_uuids, required_phase_uuid,
                         annotations)
        self.props = props  # type: dict[str, str]
        self.integration_uuid = integration_uuid  # type: str
        self.integration = None  # type: Optional[Integration]

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)
        self.integration = ctx.e.integrations.get(
            self.integration_uuid,
            ApiIntegration.default(),
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
            props=data['props'],
            annotations=_load_annotations(data['annotations']),
        )


class ItemSelectQuestion(Question):

    def __init__(self, uuid, title, text, tag_uuids, reference_uuids,
                 expert_uuids, required_phase_uuid, list_question_uuid,
                 annotations):
        super().__init__(uuid, 'ItemSelectQuestion', title, text, tag_uuids,
                         reference_uuids, expert_uuids, required_phase_uuid,
                         annotations)
        self.list_question_uuid = list_question_uuid  # type: str
        self.list_question = None  # type: Optional[ListQuestion]

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)
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

    def __init__(self, uuid, title, text, tag_uuids, reference_uuids,
                 expert_uuids, required_phase_uuid, max_size, file_types,
                 annotations):
        super().__init__(uuid, 'FileQuestion', title, text, tag_uuids,
                         reference_uuids, expert_uuids, required_phase_uuid,
                         annotations)
        self.max_size = max_size
        self.file_types = file_types

    def _resolve_links(self, ctx):
        super()._resolve_links_parent(ctx)

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

    def __init__(self, uuid, title, text, question_uuids, annotations):
        self.uuid = uuid  # type: str
        self.title = title  # type: str
        self.text = text  # type: Optional[str]
        self.question_uuids = question_uuids  # type: list[str]
        self.questions = list()  # type: list[Question]
        self.reports = list()  # type: list[ReportItem]
        self.annotations = annotations  # type: AnnotationsT

    @property
    def a(self):
        return self.annotations

    def __eq__(self, other):
        if not isinstance(other, Chapter):
            return False
        return other.uuid == self.uuid

    def _resolve_links(self, ctx):
        self.questions = [ctx.e.questions[key]
                          for key in self.question_uuids
                          if key in ctx.e.questions.keys()]
        for question in self.questions:
            question.parent = self
            question._resolve_links(ctx)

    @staticmethod
    def load(data: dict, **options):
        return Chapter(
            uuid=data['uuid'],
            title=data['title'],
            text=data['text'],
            question_uuids=data['questionUuids'],
            annotations=_load_annotations(data['annotations']),
        )


def _load_question(data: dict, **options):
    if data['questionType'] == 'OptionsQuestion':
        return OptionsQuestion.load(data, **options)
    if data['questionType'] == 'ListQuestion':
        return ListQuestion.load(data, **options)
    if data['questionType'] == 'ValueQuestion':
        return ValueQuestion.load(data, **options)
    if data['questionType'] == 'MultiChoiceQuestion':
        return MultiChoiceQuestion.load(data, **options)
    if data['questionType'] == 'IntegrationQuestion':
        return IntegrationQuestion.load(data, **options)
    if data['questionType'] == 'ItemSelectQuestion':
        return ItemSelectQuestion.load(data, **options)
    if data['questionType'] == 'FileQuestion':
        return FileQuestion.load(data, **options)
    raise ValueError(f'Unknown question type: {data["questionType"]}')


def _load_reference(data: dict, **options):
    if data['referenceType'] == 'URLReference':
        return URLReference.load(data, **options)
    if data['referenceType'] == 'ResourcePageReference':
        return ResourcePageReference.load(data, **options)
    if data['referenceType'] == 'CrossReference':
        return CrossReference.load(data, **options)
    raise ValueError(f'Unknown reference type: {data["referenceType"]}')


def _load_integration(data: dict, **options):
    if data['integrationType'] == 'ApiIntegration':
        return ApiIntegration.load(data, **options)
    if data['integrationType'] == 'WidgetIntegration':
        return WidgetIntegration.load(data, **options)
    raise ValueError(f'Unknown integration type: {data["integrationType"]}')


def _load_reply(path: str, data: dict, **options):
    if data['value']['type'] == 'AnswerReply':
        return AnswerReply.load(path, data, **options)
    if data['value']['type'] == 'StringReply':
        return StringReply.load(path, data, **options)
    if data['value']['type'] == 'ItemListReply':
        return ItemListReply.load(path, data, **options)
    if data['value']['type'] == 'MultiChoiceReply':
        return MultiChoiceReply.load(path, data, **options)
    if data['value']['type'] == 'IntegrationReply':
        return IntegrationReply.load(path, data, **options)
    if data['value']['type'] == 'ItemSelectReply':
        return ItemSelectReply.load(path, data, **options)
    if data['value']['type'] == 'FileReply':
        return FileReply.load(path, data, **options)
    raise ValueError(f'Unknown reply type: {data["value"]["type"]}')


class KnowledgeModelEntities:

    def __init__(self):
        self.chapters = dict()  # type: dict[str, Chapter]
        self.questions = dict()  # type: dict[str, Question]
        self.answers = dict()  # type: dict[str, Answer]
        self.choices = dict()  # type: dict[str, Choice]
        self.resource_collections = dict()  # type: dict[str, ResourceCollection]
        self.resource_pages = dict()  # type: dict[str, ResourcePage]
        self.references = dict()  # type: dict[str, Reference]
        self.experts = dict()  # type: dict[str, Expert]
        self.tags = dict()  # type: dict[str, Tag]
        self.metrics = dict()  # type: dict[str, Metric]
        self.phases = dict()  # type: dict[str, Phase]
        self.integrations = dict()  # type: dict[str, Integration]

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

    def __init__(self, uuid, chapter_uuids, tag_uuids, metric_uuids,
                 phase_uuids, integration_uuids, resource_collection_uuids,
                 entities, annotations):
        self.uuid = uuid  # type: str
        self.entities = entities  # type: KnowledgeModelEntities
        self.chapter_uuids = chapter_uuids  # type: list[str]
        self.chapters = list()  # type: list[Chapter]
        self.tag_uuids = tag_uuids  # type: list[str]
        self.tags = list()  # type: list[Tag]
        self.metric_uuids = metric_uuids  # type: list[str]
        self.metrics = list()  # type: list[Metric]
        self.phase_uuids = phase_uuids  # type: list[str]
        self.phases = list()  # type: list[Phase]
        self.resource_collection_uuids = resource_collection_uuids  # type: list[str]
        self.resource_collections = list()  # type: list[ResourceCollection]
        self.integration_uuids = integration_uuids  # type: list[str]
        self.integrations = list()  # type: list[Integration]
        self.annotations = annotations  # type: AnnotationsT

    @property
    def a(self):
        return self.annotations

    @property
    def e(self):
        return self.entities

    def _resolve_links(self, ctx):
        self.chapters = [ctx.e.chapters[key]
                         for key in self.chapter_uuids
                         if key in ctx.e.chapters.keys()]
        self.tags = [ctx.e.tags[key]
                     for key in self.tag_uuids
                     if key in ctx.e.tags.keys()]
        self.metrics = [ctx.e.metrics[key]
                        for key in self.metric_uuids
                        if key in ctx.e.metrics.keys()]
        self.phases = [ctx.e.phases[key]
                       for key in self.phase_uuids
                       if key in ctx.e.phases.keys()]
        self.resource_collections = [ctx.e.resource_collections[key]
                                     for key in self.resource_collection_uuids
                                     if key in ctx.e.resource_collections.keys()]
        self.integrations = [ctx.e.integrations[key]
                             for key in self.integration_uuids
                             if key in ctx.e.integrations.keys()]
        for index, phase in enumerate(self.phases, start=1):
            phase.order = index
        for chapter in self.chapters:
            chapter._resolve_links(ctx)
        for resource_collection in self.resource_collections:
            resource_collection._resolve_links(ctx)

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

    def __init__(self, client_url):
        self.client_url = client_url  # type: str

    @staticmethod
    def load(data: dict, **options):
        return ContextConfig(
            client_url=data.get('clientUrl', None),
        )


class Document:

    def __init__(self, uuid, name, document_template_id, format_uuid,
                 created_by, created_at):
        self.uuid = uuid  # type: str
        self.name = name  # type: str
        self.document_template_id = document_template_id  # type: str
        self.format_uuid = format_uuid  # type: str
        self.created_by = created_by  # type: Optional[User]
        self.created_at = created_at  # type: datetime.datetime

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


class SimpleAuthor:

    def __init__(self, uuid, first_name, last_name, image_url, gravatar_hash):
        self.uuid = uuid  # type: str
        self.first_name = first_name  # type: str
        self.last_name = last_name  # type: str
        self.image_url = image_url  # type: Optional[str]
        self.gravatar_hash = gravatar_hash  # type: Optional[str]

    @staticmethod
    def load(data: Optional[dict], **options):
        if data is None:
            return None
        return SimpleAuthor(
            uuid=data['uuid'],
            first_name=data['firstName'],
            last_name=data['lastName'],
            image_url=data['imageUrl'],
            gravatar_hash=data['gravatarHash'],
        )


class QuestionnaireVersion:

    def __init__(self, uuid, event_uuid, name, description,
                 created_at, updated_at, created_by):
        self.uuid = uuid  # type: str
        self.event_uuid = event_uuid  # type: str
        self.name = name  # type: str
        self.description = description  # type: str
        self.created_at = created_at  # type: datetime.datetime
        self.updated_at = updated_at  # type: datetime.datetime
        self.created_by = created_by  # type: Optional[SimpleAuthor]

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

    def __init__(self, replies: dict[str, Reply]):
        self.replies = replies

    def __getitem__(self, path: str) -> Optional[Reply]:
        return self.get(path)

    def __len__(self) -> int:
        return len(self.replies)

    def get(self, path: str, default=None) -> Optional[Reply]:
        return self.replies.get(path, default)

    def iterate_by_prefix(self, path_prefix: str) -> Iterable[Reply]:
        return (r for path, r in self.replies.items() if path.startswith(path_prefix))

    def iterate_by_suffix(self, path_suffix: str) -> Iterable[Reply]:
        return (r for path, r in self.replies.items() if path.endswith(path_suffix))

    def values(self) -> Iterable[Reply]:
        return self.replies.values()

    def keys(self) -> Iterable[str]:
        return self.replies.keys()

    def items(self) -> ItemsView[str, Reply]:
        return self.replies.items()


class QuestionnaireFile:

    def __init__(self, uuid, file_name, file_size, content_type):
        self.uuid = uuid  # type: str
        self.name = file_name  # type: str
        self.size = file_size  # type: int
        self.content_type = content_type  # type: str

        self.reply = None  # type: Optional[FileReply]
        self.download_url = ''  # type: str

    def _resolve_links(self, ctx):
        # Update the download URL: /projects/<projectUuid>/files/<fileUuid>/download
        project_uuid = ctx.questionnaire.uuid
        client_url = ctx.config.client_url
        self.download_url = f'{client_url}/projects/{project_uuid}/files/{self.uuid}/download'

    @staticmethod
    def load(data: dict, questionnaire_uuid: str, **options):
        return QuestionnaireFile(
            uuid=data['uuid'],
            file_name=data['fileName'],
            file_size=data['fileSize'],
            content_type=data['contentType'],
        )


class Questionnaire:

    def __init__(self, uuid, name, description, created_by, phase_uuid,
                 created_at, updated_at):
        self.uuid = uuid  # type: str
        self.name = name  # type: str
        self.description = description  # type: str
        self.version = None  # type: Optional[QuestionnaireVersion]
        self.versions = list()  # type: list[QuestionnaireVersion]
        self.files = dict()  # type: dict[str, QuestionnaireFile]
        self.todos = list()  # type: list[str]
        self.created_by = created_by  # type: User
        self.phase_uuid = phase_uuid  # type: Optional[str]
        self.phase = PHASE_NEVER  # type: Phase
        self.project_tags = list()  # type: list[str]
        self.replies = RepliesContainer(dict())  # type: RepliesContainer
        self.created_at = created_at
        self.updated_at = updated_at

    def _resolve_links(self, ctx):
        for reply in self.replies.values():
            reply._resolve_links(ctx)
        for file in self.files.values():
            file._resolve_links(ctx)

    @staticmethod
    def load(data: dict, **options):
        questionnaire_uuid = data['uuid']
        versions = [QuestionnaireVersion.load(d, **options)
                    for d in data['versions']]
        version = None
        replies = {p: _load_reply(p, d, **options)
                   for p, d in data['replies'].items()}
        files = {d['uuid']: QuestionnaireFile.load(d, questionnaire_uuid, **options)
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

    def __init__(self, org_id, km_id, version, versions, name, description, created_at):
        self.organization_id = org_id  # type: str
        self.km_id = km_id  # type: str
        self.version = version  # type: str
        self.id = f'{org_id}:{km_id}:{version}'
        self.versions = versions  # type: list[str]
        self.name = name  # type: str
        self.description = description  # type: str
        self.created_at = created_at  # type: datetime.datetime

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

    def __init__(self, indication_type, answered, unanswered):
        self.indication_type = indication_type  # type: str
        self.answered = answered  # type: int
        self.unanswered = unanswered  # type: int

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

    def __init__(self, measure, metric_uuid):
        self.measure = measure  # type: float
        self.metric_uuid = metric_uuid  # type: str
        self.metric = None  # type: Optional[Metric]

    def _resolve_links(self, ctx):
        if self.metric_uuid in ctx.e.metrics.keys():
            self.metric = ctx.e.metrics[self.metric_uuid]

    @staticmethod
    def load(data: dict, **options):
        return ReportMetric(
            measure=float(data['measure']),
            metric_uuid=data['metricUuid'],
        )


class ReportItem:

    def __init__(self, indications, metrics, chapter_uuid):
        self.indications = indications  # type: list[ReportIndication]
        self.metrics = metrics  # type: list[ReportMetric]
        self.chapter_uuid = chapter_uuid  # type: Optional[str]
        self.chapter = None  # type: Optional[Chapter]

    def _resolve_links(self, ctx):
        for m in self.metrics:
            m._resolve_links(ctx)
        if self.chapter_uuid is not None and self.chapter_uuid in ctx.e.chapters.keys():
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

    def __init__(self, uuid, created_at, updated_at, chapter_reports, total_report):
        self.uuid = uuid  # type: str
        self.created_at = created_at  # type: datetime.datetime
        self.updated_at = updated_at  # type: datetime.datetime
        self.total_report = total_report  # type: ReportItem
        self.chapter_reports = chapter_reports  # type: list[ReportItem]

    def _resolve_links(self, ctx):
        self.total_report._resolve_links(ctx)
        for report in self.chapter_reports:
            report._resolve_links(ctx)

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


class User:

    def __init__(self, uuid, first_name, last_name, email, role, created_at,
                 updated_at, affiliation, permissions, sources, image_url):
        self.uuid = uuid  # type: str
        self.first_name = first_name  # type: str
        self.last_name = last_name  # type: str
        self.email = email  # type: str
        self.role = role  # type: str
        self.image_url = image_url  # type: Optional[str]
        self.affiliation = affiliation  # type: Optional[str]
        self.permissions = permissions  # type: list[str]
        self.sources = sources  # type: list[str]
        self.created_at = created_at  # type: datetime.datetime
        self.updated_at = updated_at  # type: datetime.datetime

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

    def __init__(self, org_id, name, description, affiliations):
        self.id = org_id  # type: str
        self.name = name  # type: str
        self.description = description  # type: Optional[str]
        self.affiliations = affiliations  # type: list[str]

    @staticmethod
    def load(data: dict, **options):
        return Organization(
            org_id=data['organizationId'],
            name=data['name'],
            description=data['description'],
            affiliations=data['affiliations'],
        )


class UserGroup:

    def __init__(self, uuid, name, description, private,
                 created_at, updated_at):
        self.uuid = uuid  # type: str
        self.name = name  # type: str
        self.description = description  # type: Optional[str]
        self.private = private  # type: bool
        self.members = list()  # type: list[UserGroupMember]
        self.created_at = created_at  # type: datetime.datetime
        self.updated_at = updated_at  # type: datetime.datetime

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

    def __init__(self, uuid, first_name, last_name, gravatar_hash,
                 image_url, membership_type):
        self.uuid = uuid  # type: str
        self.first_name = first_name  # type: str
        self.last_name = last_name  # type: str
        self.gravatar_hash = gravatar_hash  # type: str
        self.image_url = image_url  # type: Optional[str]
        self.membership_type = membership_type  # type: str

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

    def __init__(self, user, permissions):
        self.user = user  # type: Optional[User]
        self.permissions = permissions  # type: list[str]

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

    def __init__(self, group, permissions):
        self.group = group  # type: Optional[UserGroup]
        self.permissions = permissions  # type: list[str]

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
    METAMODEL_VERSION = 16

    def __init__(self, ctx, **options):
        self.metamodel_version = int(ctx.get('metamodelVersion', '0'))
        if self.metamodel_version != self.METAMODEL_VERSION:
            raise ValueError(f'Unsupported metamodel version: {self.metamodel_version} '
                             f'(expected: {self.METAMODEL_VERSION})')

        self.config = ContextConfig.load(ctx['config'], **options)
        self.km = KnowledgeModel.load(ctx['knowledgeModel'], **options)
        self.questionnaire = Questionnaire.load(ctx['questionnaire'], **options)
        self.report = Report.load(ctx['report'], **options)
        self.document = Document.load(ctx['document'], **options)
        self.package = Package.load(ctx['package'], **options)
        self.organization = Organization.load(ctx['organization'], **options)
        self.current_phase = PHASE_NEVER  # type: Phase

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

    def _resolve_links(self):
        phase_uuid = self.questionnaire.phase_uuid
        if phase_uuid is not None and phase_uuid in self.e.phases.keys():
            self.current_phase = self.e.phases[phase_uuid]
        self.questionnaire.phase = self.current_phase
        self.km._resolve_links(self)
        self.report._resolve_links(self)
        self.questionnaire._resolve_links(self)

        rv = ReplyVisitor(self)
        rv.visit()
        for reply in self.replies.values():
            if isinstance(reply, ItemSelectReply):
                reply.item_title = rv.item_titles.get(reply.item_uuid, 'Item')


class ReplyVisitor:

    def __init__(self, context: DocumentContext):
        self.item_titles = dict()  # type: dict[str, str]
        self._set_also = dict()  # type: dict[str, list[str]]
        self.context = context

    def visit(self):
        for chapter in self.context.km.chapters:
            self._visit_chapter(chapter)

    def _visit_chapter(self, chapter: Chapter):
        for question in chapter.questions:
            self._visit_question(question, path=chapter.uuid)

    def _visit_question(self, question: Question, path: str):
        new_path = f'{path}.{question.uuid}'
        if isinstance(question, ListQuestion):
            self._visit_list_question(question, new_path)
        elif isinstance(question, OptionsQuestion):
            self._visit_options_question(question, new_path)

    def _visit_list_question(self, question: ListQuestion, path: str):
        reply = self.context.replies.get(path)
        if reply is None or not isinstance(reply, ItemListReply):
            return
        for n, item_uuid in enumerate(reply.items, start=1):
            self.item_titles[item_uuid] = f'Item {n}'
            item_path = f'{path}.{item_uuid}'

            # title
            if len(question.followups) > 0:
                title_path = f'{item_path}.{question.followups[0].uuid}'
                title_reply = self.context.replies.get(title_path)
                if title_reply is not None and isinstance(title_reply, StringReply):
                    self.item_titles[item_uuid] = title_reply.value
                elif title_reply is not None and isinstance(title_reply, IntegrationReply):
                    non_empty_lines = list(filter(lambda line: len(line) > 0, title_reply.value.split('\n')))
                    if len(non_empty_lines) > 0:
                        self.item_titles[item_uuid] = non_empty_lines[0]
                elif title_reply is not None and isinstance(title_reply, ItemSelectReply):
                    ref_item_uuid = title_reply.item_uuid
                    if ref_item_uuid in self.item_titles.keys():
                        self.item_titles[item_uuid] = self.item_titles[ref_item_uuid]
                    else:
                        self._set_also.setdefault(ref_item_uuid, []).append(item_uuid)
            for set_also in self._set_also.get(item_uuid, []):
                self.item_titles[set_also] = self.item_titles[item_uuid]

            # followups
            for followup in question.followups:
                self._visit_question(followup, path=item_path)

    def _visit_options_question(self, question: OptionsQuestion, path: str):
        reply = self.context.replies.get(path)
        if reply is None or not isinstance(reply, AnswerReply) or reply.answer is None:
            return

        new_path = f'{path}.{reply.answer_uuid}'
        for followup in reply.answer.followups:
            self._visit_question(followup, path=new_path)
