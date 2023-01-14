import abc

from typing import Generic, Optional, TypeVar, Any

# https://github.com/ds-wizard/engine-backend/blob/develop/engine-shared/src/Shared/Model/Event/

T = TypeVar('T')


class MetricMeasure:

    def __init__(self, metric_uuid: str, measure: float, weight: float):
        self.metric_uuid = metric_uuid
        self.measure = measure
        self.weight = weight

    def to_dict(self) -> dict:
        return {
            'metricUuid': self.metric_uuid,
            'measure': self.measure,
            'weight': self.weight,
        }

    @staticmethod
    def from_dict(data: dict) -> 'MetricMeasure':
        return MetricMeasure(
            metric_uuid=data['metricUuid'],
            measure=data['measure'],
            weight=data['weight'],
        )


class EventField(Generic[T]):

    def __init__(self, changed: bool, value: Optional[T]):
        self.changed = changed
        self.value = value

    def to_dict(self) -> dict:
        if not self.changed:
            return {
                'changed': False,
            }
        return {
            'changed': True,
            'value': self.value,
        }

    @staticmethod
    def from_dict(data: dict, loader=None) -> 'EventField':
        value = data.get('value', None)
        if loader is not None and value is not None:
            value = loader(value)
        return EventField(
            changed=data['changed'],
            value=value,
        )


class MapEntry:

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def to_dict(self) -> dict:
        value = self.value
        if hasattr(value, 'to_json'):
            value = value.to_json()
        return {
            'key': self.key,
            'value': value,
        }

    @staticmethod
    def from_dict(data: dict) -> 'MapEntry':
        return MapEntry(
            key=data['key'],
            value=data['value'],
        )


class _KMEvent(abc.ABC):
    TYPE = 'UNKNOWN'
    METAMODEL_VERSION = 10

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str):
        self.event_uuid = event_uuid
        self.entity_uuid = entity_uuid
        self.parent_uuid = parent_uuid
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            'uuid': self.event_uuid,
            'parentUuid': self.parent_uuid,
            'entityUuid': self.entity_uuid,
            'createdAt': self.created_at,
        }

    @classmethod
    @abc.abstractmethod
    def from_dict(cls, data: dict):
        pass


class _KMAddEvent(_KMEvent, abc.ABC):
    TYPE = 'ADD'

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
        )
        self.annotations = annotations

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'annotations': self.annotations,
        })
        return result


class _KMEditEvent(_KMEvent, abc.ABC):
    TYPE = 'EDIT'

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
        )
        self.annotations = annotations

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'annotations': self.annotations.to_dict(),
        })
        return result


class _KMDeleteEvent(_KMEvent, abc.ABC):
    TYPE = 'DELETE'


class _KMMoveEvent(_KMEvent, abc.ABC):
    TYPE = 'MOVE'

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, target_uuid: str):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
        )
        self.target_uuid = target_uuid

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'targetUuid': self.target_uuid,
        })
        return result


EVENT_TYPES = {}  # type: dict[str, Any]


def event_class(cls):
    EVENT_TYPES[cls.__name__] = cls
    return cls


@event_class
class AddKnowledgeModelEvent(_KMAddEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddKnowledgeModelEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return AddKnowledgeModelEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
        )


@event_class
class EditKnowledgeModelEvent(_KMEditEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 chapter_uuids:  EventField[list[str]], tag_uuids:  EventField[list[str]],
                 integration_uuids:  EventField[list[str]], metric_uuids:  EventField[list[str]],
                 phase_uuids:  EventField[list[str]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.chapter_uuids = chapter_uuids
        self.tag_uuids = tag_uuids
        self.integration_uuids = integration_uuids
        self.metric_uuids = metric_uuids
        self.phase_uuids = phase_uuids

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'chapterUuids': self.chapter_uuids.to_dict(),
            'tagUuids': self.tag_uuids.to_dict(),
            'integrationUuids': self.integration_uuids.to_dict(),
            'metricUuids': self.metric_uuids.to_dict(),
            'phaseUuids': self.phase_uuids.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditKnowledgeModelEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return EditKnowledgeModelEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            chapter_uuids=EventField.from_dict(data['chapterUuids']),
            tag_uuids=EventField.from_dict(data['tagUuids']),
            integration_uuids=EventField.from_dict(data['integrationUuids']),
            metric_uuids=EventField.from_dict(data['metricUuids']),
            phase_uuids=EventField.from_dict(data['phaseUuids']),
        )


@event_class
class AddChapterEvent(_KMAddEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 title: str, text: Optional[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.title = title
        self.text = text

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'title': self.title,
            'text': self.text,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddChapterEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return AddChapterEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            title=data['title'],
            text=data['text'],
        )


@event_class
class EditChapterEvent(_KMEditEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 title:  EventField[str], text:  EventField[Optional[str]],
                 question_uuids: EventField[list[str]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.title = title
        self.text = text
        self.question_uuids = question_uuids

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'title': self.title.to_dict(),
            'text': self.text.to_dict(),
            'questionUuids': self.question_uuids.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditChapterEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return EditChapterEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            title=EventField.from_dict(data['title']),
            text=EventField.from_dict(data['text']),
            question_uuids=EventField.from_dict(data['questionUuids']),
        )


@event_class
class DeleteChapterEvent(_KMDeleteEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DeleteChapterEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return DeleteChapterEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
        )


@event_class
class AddQuestionEvent(_KMAddEvent, abc.ABC):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 title: str, text: Optional[str], required_phase_uuid: Optional[str],
                 tag_uuids: list[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.title = title
        self.text = text
        self.required_phase_uuid = required_phase_uuid
        self.tag_uuids = tag_uuids

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': 'AddQuestionEvent',
            'title': self.title,
            'text': self.text,
            'requiredPhaseUuid': self.required_phase_uuid,
            'tagUuids': self.tag_uuids,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddQuestionEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        question_type = data['questionType']
        if question_type == 'OptionsQuestion':
            return AddOptionsQuestionEvent.from_dict(data)
        if question_type == 'ListQuestion':
            return AddListQuestionEvent.from_dict(data)
        if question_type == 'ValueQuestion':
            return AddValueQuestionEvent.from_dict(data)
        if question_type == 'IntegrationQuestion':
            return AddIntegrationQuestionEvent.from_dict(data)
        if question_type == 'MultiChoiceQuestion':
            return AddMultiChoiceQuestionEvent.from_dict(data)
        raise ValueError(f'Unknown question type "{question_type}"')


class AddOptionsQuestionEvent(AddQuestionEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 title: str, text: Optional[str], required_phase_uuid: Optional[str],
                 tag_uuids: list[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            title=title,
            text=text,
            required_phase_uuid=required_phase_uuid,
            tag_uuids=tag_uuids,
        )

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'questionType': 'OptionsQuestion',
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddOptionsQuestionEvent':
        if data['eventType'] != 'AddQuestionEvent':
            raise ValueError('Event of incorrect type (expect AddQuestionEvent)')
        if data['questionType'] != 'OptionsQuestion':
            raise ValueError('Event of incorrect type (expect OptionsQuestion)')
        return AddOptionsQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            title=data['title'],
            text=data['text'],
            required_phase_uuid=data['requiredPhaseUuid'],
            tag_uuids=data['tagUuids'],
        )


class AddMultiChoiceQuestionEvent(AddQuestionEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 title: str, text: Optional[str], required_phase_uuid: Optional[str],
                 tag_uuids: list[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            title=title,
            text=text,
            required_phase_uuid=required_phase_uuid,
            tag_uuids=tag_uuids,
        )

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'questionType': 'MultiChoiceQuestion',
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddMultiChoiceQuestionEvent':
        if data['eventType'] != 'AddQuestionEvent':
            raise ValueError('Event of incorrect type (expect AddQuestionEvent)')
        if data['questionType'] != 'MultiChoiceQuestion':
            raise ValueError('Event of incorrect type (expect MultiChoiceQuestion)')
        return AddMultiChoiceQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            title=data['title'],
            text=data['text'],
            required_phase_uuid=data['requiredPhaseUuid'],
            tag_uuids=data['tagUuids'],
        )


class AddListQuestionEvent(AddQuestionEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 title: str, text: Optional[str], required_phase_uuid: Optional[str],
                 tag_uuids: list[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            title=title,
            text=text,
            required_phase_uuid=required_phase_uuid,
            tag_uuids=tag_uuids,
        )

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'questionType': 'ListQuestion',
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddListQuestionEvent':
        if data['eventType'] != 'AddQuestionEvent':
            raise ValueError('Event of incorrect type (expect AddQuestionEvent)')
        if data['questionType'] != 'ListQuestion':
            raise ValueError('Event of incorrect type (expect ListQuestion)')
        return AddListQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            title=data['title'],
            text=data['text'],
            required_phase_uuid=data['requiredPhaseUuid'],
            tag_uuids=data['tagUuids'],
        )


class AddValueQuestionEvent(AddQuestionEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 title: str, text: Optional[str], required_phase_uuid: Optional[str],
                 tag_uuids: list[str], value_type: str):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            title=title,
            text=text,
            required_phase_uuid=required_phase_uuid,
            tag_uuids=tag_uuids,
        )
        self.value_type = value_type

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'questionType': 'ValueQuestion',
            'valueType': self.value_type,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddValueQuestionEvent':
        if data['eventType'] != 'AddQuestionEvent':
            raise ValueError('Event of incorrect type (expect AddQuestionEvent)')
        if data['questionType'] != 'ValueQuestion':
            raise ValueError('Event of incorrect type (expect ValueQuestion)')
        return AddValueQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            title=data['title'],
            text=data['text'],
            required_phase_uuid=data['requiredPhaseUuid'],
            tag_uuids=data['tagUuids'],
            value_type=data['valueType'],
        )


class AddIntegrationQuestionEvent(AddQuestionEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 title: str, text: Optional[str], required_phase_uuid: Optional[str],
                 tag_uuids: list[str], integration_uuid: str, props: dict[str, str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            title=title,
            text=text,
            required_phase_uuid=required_phase_uuid,
            tag_uuids=tag_uuids,
        )
        self.integration_uuid = integration_uuid
        self.props = props

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'questionType': 'IntegrationQuestion',
            'integrationUuid': self.integration_uuid,
            'props': self.props,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddIntegrationQuestionEvent':
        if data['eventType'] != 'AddQuestionEvent':
            raise ValueError('Event of incorrect type (expect AddQuestionEvent)')
        if data['questionType'] != 'IntegrationQuestion':
            raise ValueError('Event of incorrect type (expect IntegrationQuestion)')
        return AddIntegrationQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            title=data['title'],
            text=data['text'],
            required_phase_uuid=data['requiredPhaseUuid'],
            tag_uuids=data['tagUuids'],
            integration_uuid=data['integrationUuid'],
            props=data['props'],
        )


@event_class
class EditQuestionEvent(_KMEditEvent, abc.ABC):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 title: EventField[str], text: EventField[Optional[str]],
                 required_phase_uuid: EventField[Optional[str]],
                 tag_uuids: EventField[list[str]], expert_uuids: EventField[list[str]],
                 reference_uuids: EventField[list[str]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.title = title
        self.text = text
        self.required_phase_uuid = required_phase_uuid
        self.tag_uuids = tag_uuids
        self.expert_uuids = expert_uuids
        self.reference_uuids = reference_uuids

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': 'EditQuestionEvent',
            'title': self.title.to_dict(),
            'text': self.text.to_dict(),
            'requiredPhaseUuid': self.required_phase_uuid.to_dict(),
            'tagUuids': self.tag_uuids.to_dict(),
            'expertUuids': self.expert_uuids.to_dict(),
            'referenceUuids': self.reference_uuids.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditQuestionEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        question_type = data['questionType']
        if question_type == 'OptionsQuestion':
            return EditOptionsQuestionEvent.from_dict(data)
        if question_type == 'ListQuestion':
            return EditListQuestionEvent.from_dict(data)
        if question_type == 'ValueQuestion':
            return EditValueQuestionEvent.from_dict(data)
        if question_type == 'IntegrationQuestion':
            return EditIntegrationQuestionEvent.from_dict(data)
        if question_type == 'MultiChoiceQuestion':
            return EditMultiChoiceQuestionEvent.from_dict(data)
        raise ValueError(f'Unknown question type "{question_type}"')


class EditOptionsQuestionEvent(EditQuestionEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 title: EventField[str], text: EventField[Optional[str]],
                 required_phase_uuid: EventField[Optional[str]],
                 tag_uuids: EventField[list[str]], expert_uuids: EventField[list[str]],
                 reference_uuids: EventField[list[str]],
                 answer_uuids: EventField[list[str]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            title=title,
            text=text,
            required_phase_uuid=required_phase_uuid,
            tag_uuids=tag_uuids,
            expert_uuids=expert_uuids,
            reference_uuids=reference_uuids,
        )
        self.answer_uuids = answer_uuids

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'questionType': 'OptionsQuestion',
            'answerUuids': self.answer_uuids.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditOptionsQuestionEvent':
        if data['eventType'] != 'EditQuestionEvent':
            raise ValueError('Event of incorrect type (expect EditQuestionEvent)')
        if data['questionType'] != 'OptionsQuestion':
            raise ValueError('Event of incorrect type (expect OptionsQuestion)')
        return EditOptionsQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            title=EventField.from_dict(data['title']),
            text=EventField.from_dict(data['text']),
            required_phase_uuid=EventField.from_dict(data['requiredPhaseUuid']),
            tag_uuids=EventField.from_dict(data['tagUuids']),
            expert_uuids=EventField.from_dict(data['expertUuids']),
            reference_uuids=EventField.from_dict(data['referenceUuids']),
            answer_uuids=EventField.from_dict(data['answerUuids']),
        )


class EditMultiChoiceQuestionEvent(EditQuestionEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 title: EventField[str], text: EventField[Optional[str]],
                 required_phase_uuid: EventField[Optional[str]],
                 tag_uuids: EventField[list[str]], expert_uuids: EventField[list[str]],
                 reference_uuids: EventField[list[str]],
                 choice_uuids: EventField[list[str]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            title=title,
            text=text,
            required_phase_uuid=required_phase_uuid,
            tag_uuids=tag_uuids,
            expert_uuids=expert_uuids,
            reference_uuids=reference_uuids,
        )
        self.choice_uuids = choice_uuids

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'questionType': 'MultiChoiceQuestion',
            'choiceUuids': self.choice_uuids.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditMultiChoiceQuestionEvent':
        if data['eventType'] != 'EditQuestionEvent':
            raise ValueError('Event of incorrect type (expect EditQuestionEvent)')
        if data['questionType'] != 'MultiChoiceQuestion':
            raise ValueError('Event of incorrect type (expect MultiChoiceQuestion)')
        return EditMultiChoiceQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            title=EventField.from_dict(data['title']),
            text=EventField.from_dict(data['text']),
            required_phase_uuid=EventField.from_dict(data['requiredPhaseUuid']),
            tag_uuids=EventField.from_dict(data['tagUuids']),
            expert_uuids=EventField.from_dict(data['expertUuids']),
            reference_uuids=EventField.from_dict(data['referenceUuids']),
            choice_uuids=EventField.from_dict(data['choiceUuids']),
        )


class EditListQuestionEvent(EditQuestionEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 title: EventField[str], text: EventField[Optional[str]],
                 required_phase_uuid: EventField[Optional[str]],
                 tag_uuids: EventField[list[str]], expert_uuids: EventField[list[str]],
                 reference_uuids: EventField[list[str]],
                 item_template_question_uuids: EventField[list[str]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            title=title,
            text=text,
            required_phase_uuid=required_phase_uuid,
            tag_uuids=tag_uuids,
            expert_uuids=expert_uuids,
            reference_uuids=reference_uuids,
        )
        self.item_template_question_uuids = item_template_question_uuids

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'questionType': 'ListQuestion',
            'itemTemplateQuestionUuids': self.item_template_question_uuids.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditListQuestionEvent':
        if data['eventType'] != 'EditQuestionEvent':
            raise ValueError('Event of incorrect type (expect EditQuestionEvent)')
        if data['questionType'] != 'ListQuestion':
            raise ValueError('Event of incorrect type (expect ListQuestion)')
        return EditListQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            title=EventField.from_dict(data['title']),
            text=EventField.from_dict(data['text']),
            required_phase_uuid=EventField.from_dict(data['requiredPhaseUuid']),
            tag_uuids=EventField.from_dict(data['tagUuids']),
            expert_uuids=EventField.from_dict(data['expertUuids']),
            reference_uuids=EventField.from_dict(data['referenceUuids']),
            item_template_question_uuids=EventField.from_dict(data['itemTemplateQuestionUuids']),
        )


class EditValueQuestionEvent(EditQuestionEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 title: EventField[str], text: EventField[Optional[str]],
                 required_phase_uuid: EventField[Optional[str]],
                 tag_uuids: EventField[list[str]], expert_uuids: EventField[list[str]],
                 reference_uuids: EventField[list[str]], value_type: EventField[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            title=title,
            text=text,
            required_phase_uuid=required_phase_uuid,
            tag_uuids=tag_uuids,
            expert_uuids=expert_uuids,
            reference_uuids=reference_uuids,
        )
        self.value_type = value_type

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'questionType': 'ValueQuestion',
            'valueType': self.value_type.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditValueQuestionEvent':
        if data['eventType'] != 'EditQuestionEvent':
            raise ValueError('Event of incorrect type (expect EditQuestionEvent)')
        if data['questionType'] != 'ValueQuestion':
            raise ValueError('Event of incorrect type (expect ValueQuestion)')
        return EditValueQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            title=EventField.from_dict(data['title']),
            text=EventField.from_dict(data['text']),
            required_phase_uuid=EventField.from_dict(data['requiredPhaseUuid']),
            tag_uuids=EventField.from_dict(data['tagUuids']),
            expert_uuids=EventField.from_dict(data['expertUuids']),
            reference_uuids=EventField.from_dict(data['referenceUuids']),
            value_type=EventField.from_dict(data['valueType']),
        )


class EditIntegrationQuestionEvent(EditQuestionEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 title: EventField[str], text: EventField[Optional[str]],
                 required_phase_uuid: EventField[Optional[str]],
                 tag_uuids: EventField[list[str]], expert_uuids: EventField[list[str]],
                 reference_uuids: EventField[list[str]], integration_uuid: EventField[str],
                 props: EventField[dict[str, str]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            title=title,
            text=text,
            required_phase_uuid=required_phase_uuid,
            tag_uuids=tag_uuids,
            expert_uuids=expert_uuids,
            reference_uuids=reference_uuids,
        )
        self.integration_uuid = integration_uuid
        self.props = props

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'questionType': 'IntegrationQuestion',
            'integrationUuid': self.integration_uuid.to_dict(),
            'props': self.props.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditIntegrationQuestionEvent':
        if data['eventType'] != 'EditQuestionEvent':
            raise ValueError('Event of incorrect type (expect EditQuestionEvent)')
        if data['questionType'] != 'IntegrationQuestion':
            raise ValueError('Event of incorrect type (expect IntegrationQuestion)')
        return EditIntegrationQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            title=EventField.from_dict(data['title']),
            text=EventField.from_dict(data['text']),
            required_phase_uuid=EventField.from_dict(data['requiredPhaseUuid']),
            tag_uuids=EventField.from_dict(data['tagUuids']),
            expert_uuids=EventField.from_dict(data['expertUuids']),
            reference_uuids=EventField.from_dict(data['referenceUuids']),
            integration_uuid=EventField.from_dict(data['integrationUuid']),
            props=EventField.from_dict(data['props']),
        )


@event_class
class DeleteQuestionEvent(_KMDeleteEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DeleteQuestionEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return DeleteQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
        )


@event_class
class AddAnswerEvent(_KMAddEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 label: str, advice: Optional[str], metric_measures: list[MetricMeasure]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.label = label
        self.advice = advice
        self.metric_measures = metric_measures

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'label': self.label,
            'advice': self.advice,
            'metricMeasures': [m.to_dict() for m in self.metric_measures],
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddAnswerEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return AddAnswerEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            label=data['label'],
            advice=data['advice'],
            metric_measures=[MetricMeasure.from_dict(m) for m in data['metricMeasures']],
        )


@event_class
class EditAnswerEvent(_KMEditEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 label: EventField[str], advice: EventField[Optional[str]],
                 follow_up_uuids: EventField[list[str]],
                 metric_measures: EventField[list[MetricMeasure]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.label = label
        self.advice = advice
        self.follow_up_uuids = follow_up_uuids
        self.metric_measures = metric_measures

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'label': self.label.to_dict(),
            'advice': self.advice.to_dict(),
            'followUpUuids': self.follow_up_uuids.to_dict(),
            'metricMeasures': self.metric_measures.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditAnswerEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return EditAnswerEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            label=EventField.from_dict(data['label']),
            advice=EventField.from_dict(data['advice']),
            follow_up_uuids=EventField.from_dict(data['followUpUuids']),
            metric_measures=EventField.from_dict(
                data=data['metricMeasures'],
                loader=lambda v: [MetricMeasure.from_dict(x) for x in v],
            ),
        )


@event_class
class DeleteAnswerEvent(_KMDeleteEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DeleteAnswerEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return DeleteAnswerEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
        )


@event_class
class AddChoiceEvent(_KMAddEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 label: str):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.label = label

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'label': self.label,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddChoiceEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return AddChoiceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            label=data['label'],
        )


@event_class
class EditChoiceEvent(_KMEditEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 label: EventField[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.label = label

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'label': self.label.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditChoiceEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return EditChoiceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            label=EventField.from_dict(data['label']),
        )


@event_class
class DeleteChoiceEvent(_KMDeleteEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DeleteChoiceEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return DeleteChoiceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
        )


@event_class
class AddExpertEvent(_KMAddEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 name: str, email: str):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.name = name
        self.email = email

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'name': self.name,
            'email': self.email,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddExpertEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return AddExpertEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            name=data['name'],
            email=data['email'],
        )


@event_class
class EditExpertEvent(_KMEditEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 name: EventField[str], email: EventField[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.name = name
        self.email = email

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'name': self.name.to_dict(),
            'email': self.email.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditExpertEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return EditExpertEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            name=EventField.from_dict(data['name']),
            email=EventField.from_dict(data['email']),
        )


@event_class
class DeleteExpertEvent(_KMDeleteEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DeleteExpertEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return DeleteExpertEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
        )


@event_class
class AddReferenceEvent(_KMAddEvent, abc.ABC):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': 'AddReferenceEvent',
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddReferenceEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        reference_type = data['referenceType']
        if reference_type == 'ResourcePageReference':
            return AddResourcePageReferenceEvent.from_dict(data)
        if reference_type == 'URLReference':
            return AddURLReferenceEvent.from_dict(data)
        if reference_type == 'CrossReference':
            return AddCrossReferenceEvent.from_dict(data)
        raise ValueError(f'Unknown reference type "{reference_type}"')


class AddResourcePageReferenceEvent(AddReferenceEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 short_uuid: str):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.short_uuid = short_uuid

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'referenceType': 'ResourcePageReference',
            'shortUuid': self.short_uuid,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddResourcePageReferenceEvent':
        if data['eventType'] != 'AddReferenceEvent':
            raise ValueError('Event of incorrect type (expect AddReferenceEvent)')
        if data['referenceType'] != 'ResourcePageReference':
            raise ValueError('Event of incorrect type (expect ResourcePageReference)')
        return AddResourcePageReferenceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            short_uuid=data['shortUuid'],
        )


class AddURLReferenceEvent(AddReferenceEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 url: str, label: str):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.url = url
        self.label = label

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'referenceType': 'URLReference',
            'url': self.url,
            'label': self.label,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddURLReferenceEvent':
        if data['eventType'] != 'AddReferenceEvent':
            raise ValueError('Event of incorrect type (expect AddReferenceEvent)')
        if data['referenceType'] != 'URLReference':
            raise ValueError('Event of incorrect type (expect URLReference)')
        return AddURLReferenceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            url=data['url'],
            label=data['label'],
        )


class AddCrossReferenceEvent(AddReferenceEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 target_uuid: str, description: str):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.target_uuid = target_uuid
        self.description = description

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'referenceType': 'CrossReference',
            'targetUuid': self.target_uuid,
            'description': self.description,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddCrossReferenceEvent':
        if data['eventType'] != 'AddReferenceEvent':
            raise ValueError('Event of incorrect type (expect AddReferenceEvent)')
        if data['referenceType'] != 'CrossReference':
            raise ValueError('Event of incorrect type (expect CrossReference)')
        return AddCrossReferenceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            target_uuid=data['targetUuid'],
            description=data['description'],
        )


@event_class
class EditReferenceEvent(_KMEditEvent, abc.ABC):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': 'EditReferenceEvent',
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditReferenceEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        reference_type = data['referenceType']
        if reference_type == 'ResourcePageReference':
            return EditResourcePageReferenceEvent.from_dict(data)
        if reference_type == 'URLReference':
            return EditURLReferenceEvent.from_dict(data)
        if reference_type == 'CrossReference':
            return EditCrossReferenceEvent.from_dict(data)
        raise ValueError(f'Unknown reference type "{reference_type}"')


class EditResourcePageReferenceEvent(EditReferenceEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 short_uuid: EventField[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.short_uuid = short_uuid

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'referenceType': 'ResourcePageReference',
            'shortUuid': self.short_uuid.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditResourcePageReferenceEvent':
        if data['eventType'] != 'EditReferenceEvent':
            raise ValueError('Event of incorrect type (expect EditReferenceEvent)')
        if data['referenceType'] != 'ResourcePageReference':
            raise ValueError('Event of incorrect type (expect ResourcePageReference)')
        return EditResourcePageReferenceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            short_uuid=EventField.from_dict(data['shortUuid']),
        )


class EditURLReferenceEvent(EditReferenceEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 url: EventField[str], label: EventField[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.url = url
        self.label = label

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'referenceType': 'URLReference',
            'url': self.url.to_dict(),
            'label': self.label.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditURLReferenceEvent':
        if data['eventType'] != 'EditReferenceEvent':
            raise ValueError('Event of incorrect type (expect EditReferenceEvent)')
        if data['referenceType'] != 'URLReference':
            raise ValueError('Event of incorrect type (expect URLReference)')
        return EditURLReferenceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            url=EventField.from_dict(data['url']),
            label=EventField.from_dict(data['label']),
        )


class EditCrossReferenceEvent(EditReferenceEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 target_uuid: EventField[str], description: EventField[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.target_uuid = target_uuid
        self.description = description

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'referenceType': 'CrossReference',
            'targetUuid': self.target_uuid.to_dict(),
            'description': self.description.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditCrossReferenceEvent':
        if data['eventType'] != 'EditReferenceEvent':
            raise ValueError('Event of incorrect type (expect EditReferenceEvent)')
        if data['referenceType'] != 'CrossReference':
            raise ValueError('Event of incorrect type (expect CrossReference)')
        return EditCrossReferenceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            target_uuid=EventField.from_dict(data['targetUuid']),
            description=EventField.from_dict(data['description']),
        )


@event_class
class DeleteReferenceEvent(_KMDeleteEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DeleteReferenceEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return DeleteReferenceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
        )


@event_class
class AddTagEvent(_KMAddEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 name: str, description: Optional[str], color: str):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.name = name  # why not title?
        self.description = description  # why not text?
        self.color = color

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'name': self.name,
            'description': self.description,
            'color': self.color,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddTagEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return AddTagEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            name=data['name'],
            description=data['description'],
            color=data['color'],
        )


@event_class
class EditTagEvent(_KMEditEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 name: EventField[str], description: EventField[Optional[str]],
                 color: EventField[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.name = name  # why not title?
        self.description = description  # why not text?
        self.color = color

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'name': self.name.to_dict(),
            'description': self.description.to_dict(),
            'color': self.color.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditTagEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return EditTagEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            name=EventField.from_dict(data['name']),
            description=EventField.from_dict(data['description']),
            color=EventField.from_dict(data['color']),
        )


@event_class
class DeleteTagEvent(_KMDeleteEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DeleteTagEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return DeleteTagEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
        )


@event_class
class AddIntegrationEvent(_KMAddEvent, abc.ABC):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 integration_id: str, name: str, props: list[str], logo: str,
                 item_url: str):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.integration_id = integration_id
        self.name = name
        self.props = props
        self.logo = logo
        self.item_url = item_url

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': 'AddIntegrationEvent',
            'id': self.integration_id,
            'name': self.name,
            'props': self.props,
            'logo': self.logo,
            'itemUrl': self.item_url,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddIntegrationEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        integration_type = data['integrationType']
        if integration_type == 'ApiIntegration':
            return AddApiIntegrationEvent.from_dict(data)
        if integration_type == 'WidgetIntegration':
            return AddWidgetIntegrationEvent.from_dict(data)
        raise ValueError(f'Unknown integration type "{integration_type}"')


class AddApiIntegrationEvent(AddIntegrationEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 integration_id: str, name: str, props: list[str], logo: str,
                 item_url: str, rq_method: str, rq_url: str, rq_headers: list[MapEntry],
                 rq_body: str, rq_empty_search: bool, rs_list_field: str,
                 rs_item_id: str, rs_item_template: str):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            integration_id=integration_id,
            name=name,
            props=props,
            logo=logo,
            item_url=item_url
        )
        self.rq_method = rq_method
        self.rq_url = rq_url
        self.rq_headers = rq_headers
        self.rq_body = rq_body
        self.rq_empty_search = rq_empty_search
        self.rs_list_field = rs_list_field
        self.rs_item_id = rs_item_id
        self.rs_item_template = rs_item_template

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'integrationType': 'ApiIntegration',
            'requestMethod': self.rq_method,
            'requestUrl': self.rq_url,
            'requestHeaders': self.rq_headers,
            'requestBody': self.rq_body,
            'requestEmptySearch': self.rq_empty_search,
            'responseListField': self.rs_list_field,
            'responseItemId': self.rs_item_id,
            'responseItemTemplate': self.rs_item_template,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddApiIntegrationEvent':
        if data['eventType'] != 'AddIntegrationEvent':
            raise ValueError('Event of incorrect type (expect AddIntegrationEvent)')
        if data['integrationType'] != 'ApiIntegration':
            raise ValueError('Event of incorrect type (expect ApiIntegration)')
        return AddApiIntegrationEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            integration_id=data['id'],
            name=data['name'],
            props=data['props'],
            logo=data['logo'],
            item_url=data['itemUrl'],
            rq_method=data['requestMethod'],
            rq_url=data['requestUrl'],
            rq_headers=data['requestHeaders'],
            rq_body=data['requestBody'],
            rq_empty_search=data['requestEmptySearch'],
            rs_list_field=data['responseListField'],
            rs_item_id=data['responseItemId'],
            rs_item_template=data['responseItemTemplate'],
        )


class AddWidgetIntegrationEvent(AddIntegrationEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 integration_id: str, name: str, props: list[str], logo: str,
                 item_url: str, widget_url: str):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            integration_id=integration_id,
            name=name,
            props=props,
            logo=logo,
            item_url=item_url
        )
        self.widget_url = widget_url

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'integrationType': 'WidgetIntegration',
            'widgetUrl': self.widget_url,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddWidgetIntegrationEvent':
        if data['eventType'] != 'AddIntegrationEvent':
            raise ValueError('Event of incorrect type (expect AddIntegrationEvent)')
        if data['integrationType'] != 'WidgetIntegration':
            raise ValueError('Event of incorrect type (expect WidgetIntegration)')
        return AddWidgetIntegrationEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            integration_id=data['id'],
            name=data['name'],
            props=data['props'],
            logo=data['logo'],
            item_url=data['itemUrl'],
            widget_url=data['widgetUrl'],
        )


@event_class
class EditIntegrationEvent(_KMEditEvent, abc.ABC):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 integration_id: EventField[str], name: EventField[str],
                 props: EventField[list[str]], logo: EventField[str],
                 item_url: EventField[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.integration_id = integration_id
        self.name = name
        self.props = props
        self.logo = logo
        self.item_url = item_url

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': 'EditIntegrationEvent',
            'id': self.integration_id.to_dict(),
            'name': self.name.to_dict(),
            'props': self.props.to_dict(),
            'logo': self.logo.to_dict(),
            'itemUrl': self.item_url.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditIntegrationEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        integration_type = data['integrationType']
        if integration_type == 'ApiIntegration':
            return EditApiIntegrationEvent.from_dict(data)
        if integration_type == 'WidgetIntegration':
            return EditWidgetIntegrationEvent.from_dict(data)
        raise ValueError(f'Unknown integration type "{integration_type}"')


class EditApiIntegrationEvent(EditIntegrationEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 integration_id: EventField[str], name: EventField[str],
                 props: EventField[list[str]], logo: EventField[str],
                 item_url: EventField[str], rq_method: EventField[str],
                 rq_url: EventField[str], rq_headers: EventField[list[MapEntry]],
                 rq_body: EventField[str], rq_empty_search: EventField[bool],
                 rs_list_field: EventField[str], rs_item_id: EventField[str],
                 rs_item_template: EventField[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            integration_id=integration_id,
            name=name,
            props=props,
            logo=logo,
            item_url=item_url
        )
        self.rq_method = rq_method
        self.rq_url = rq_url
        self.rq_headers = rq_headers
        self.rq_body = rq_body
        self.rq_empty_search = rq_empty_search
        self.rs_list_field = rs_list_field
        self.rs_item_id = rs_item_id
        self.rs_item_template = rs_item_template

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'integrationType': 'ApiIntegration',
            'requestMethod': self.rq_method.to_dict(),
            'requestUrl': self.rq_url.to_dict(),
            'requestHeaders': self.rq_headers.to_dict(),
            'requestBody': self.rq_body.to_dict(),
            'requestEmptySearch': self.rq_empty_search.to_dict(),
            'responseListField': self.rs_list_field.to_dict(),
            'responseItemId': self.rs_item_id.to_dict(),
            'responseItemTemplate': self.rs_item_template.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditApiIntegrationEvent':
        if data['eventType'] != 'EditIntegrationEvent':
            raise ValueError('Event of incorrect type (expect EditIntegrationEvent)')
        if data['integrationType'] != 'ApiIntegration':
            raise ValueError('Event of incorrect type (expect ApiIntegration)')
        return EditApiIntegrationEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            integration_id=EventField.from_dict(data['id']),
            name=EventField.from_dict(data['name']),
            props=EventField.from_dict(data['props']),
            logo=EventField.from_dict(data['logo']),
            item_url=EventField.from_dict(data['itemUrl']),
            rq_method=EventField.from_dict(data['requestMethod']),
            rq_url=EventField.from_dict(data['requestUrl']),
            rq_headers=EventField.from_dict(
                data=data['requestHeaders'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            rq_body=EventField.from_dict(data['requestBody']),
            rq_empty_search=EventField.from_dict(data['requestEmptySearch']),
            rs_list_field=EventField.from_dict(data['responseListField']),
            rs_item_id=EventField.from_dict(data['responseItemId']),
            rs_item_template=EventField.from_dict(data['responseItemTemplate']),
        )


class EditWidgetIntegrationEvent(EditIntegrationEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 integration_id: EventField[str], name: EventField[str],
                 props: EventField[list[str]], logo: EventField[str],
                 item_url: EventField[str], widget_url: EventField[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
            integration_id=integration_id,
            name=name,
            props=props,
            logo=logo,
            item_url=item_url
        )
        self.widget_url = widget_url

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'integrationType': 'WidgetIntegration',
            'widgetUrl': self.widget_url.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditWidgetIntegrationEvent':
        if data['eventType'] != 'EditIntegrationEvent':
            raise ValueError('Event of incorrect type (expect EditIntegrationEvent)')
        if data['integrationType'] != 'WidgetIntegration':
            raise ValueError('Event of incorrect type (expect WidgetIntegration)')
        return EditWidgetIntegrationEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            integration_id=EventField.from_dict(data['id']),
            name=EventField.from_dict(data['name']),
            props=EventField.from_dict(data['props']),
            logo=EventField.from_dict(data['logo']),
            item_url=EventField.from_dict(data['itemUrl']),
            widget_url=EventField.from_dict(data['widgetUrl']),
        )


@event_class
class DeleteIntegrationEvent(_KMDeleteEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DeleteIntegrationEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return DeleteIntegrationEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
        )


@event_class
class AddMetricEvent(_KMAddEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 title: str, abbreviation: Optional[str], description: Optional[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.title = title
        self.abbreviation = abbreviation
        self.description = description

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'title': self.title,
            'abbreviation': self.abbreviation,
            'description': self.description,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddMetricEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return AddMetricEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            title=data['title'],
            abbreviation=data['abbreviation'],
            description=data['description'],
        )


@event_class
class EditMetricEvent(_KMEditEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 title: EventField[str], abbreviation: EventField[Optional[str]],
                 description: EventField[Optional[str]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.title = title
        self.abbreviation = abbreviation
        self.description = description

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'title': self.title.to_dict(),
            'abbreviation': self.abbreviation.to_dict(),
            'description': self.description.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditMetricEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return EditMetricEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            title=EventField.from_dict(data['title']),
            abbreviation=EventField.from_dict(data['abbreviation']),
            description=EventField.from_dict(data['description']),
        )


@event_class
class DeleteMetricEvent(_KMDeleteEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DeleteMetricEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return DeleteMetricEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
        )


@event_class
class AddPhaseEvent(_KMAddEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: list[MapEntry],
                 title: str, description: Optional[str]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.title = title
        self.description = description  # why not text?

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'title': self.title,
            'description': self.description,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AddPhaseEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return AddPhaseEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=[MapEntry.from_dict(x) for x in data['annotations']],
            title=data['title'],
            description=data['description'],
        )


@event_class
class EditPhaseEvent(_KMEditEvent):

    def __init__(self, event_uuid: str, entity_uuid: str, parent_uuid: str,
                 created_at: str, annotations: EventField[list[MapEntry]],
                 title:  EventField[str], description:  EventField[Optional[str]]):
        super().__init__(
            event_uuid=event_uuid,
            entity_uuid=entity_uuid,
            parent_uuid=parent_uuid,
            created_at=created_at,
            annotations=annotations,
        )
        self.title = title
        self.description = description

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
            'title': self.title.to_dict(),
            'description': self.description.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'EditPhaseEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return EditPhaseEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
            annotations=EventField.from_dict(
                data=data['annotations'],
                loader=lambda v: [MapEntry.from_dict(x) for x in v],
            ),
            title=EventField.from_dict(data['title']),
            description=EventField.from_dict(data['description']),
        )


@event_class
class DeletePhaseEvent(_KMDeleteEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DeletePhaseEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return DeletePhaseEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            created_at=data['createdAt'],
        )


@event_class
class MoveQuestionEvent(_KMMoveEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'MoveQuestionEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return MoveQuestionEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            target_uuid=data['targetUuid'],
            created_at=data['createdAt'],
        )


@event_class
class MoveAnswerEvent(_KMMoveEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'MoveAnswerEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return MoveAnswerEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            target_uuid=data['targetUuid'],
            created_at=data['createdAt'],
        )


@event_class
class MoveChoiceEvent(_KMMoveEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'MoveChoiceEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return MoveChoiceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            target_uuid=data['targetUuid'],
            created_at=data['createdAt'],
        )


@event_class
class MoveExpertEvent(_KMMoveEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'MoveExpertEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return MoveExpertEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            target_uuid=data['targetUuid'],
            created_at=data['createdAt'],
        )


@event_class
class MoveReferenceEvent(_KMMoveEvent):

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'eventType': type(self).__name__,
        })
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'MoveReferenceEvent':
        if data['eventType'] != cls.__name__:
            raise ValueError(f'Event of incorrect type (expect {cls.__name__})')
        return MoveReferenceEvent(
            event_uuid=data['uuid'],
            entity_uuid=data['entityUuid'],
            parent_uuid=data['parentUuid'],
            target_uuid=data['targetUuid'],
            created_at=data['createdAt'],
        )


class Event:

    @classmethod
    def from_dict(cls, data: dict):
        event_type = data['eventType']
        if event_type not in EVENT_TYPES.keys():
            raise ValueError(f'Unknown event type: {event_type}')
        t = EVENT_TYPES[event_type]
        if not hasattr(t, 'from_dict'):
            raise ValueError(f'Type {event_type} cannot be used for deserialization')
        return t.from_dict(data)
