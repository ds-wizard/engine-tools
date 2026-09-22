"""Metamodel migration steps of knowledge model events, on raw JSON.

Port of ``Wizard.Service.KnowledgeModel.Metamodel.Migrator.Migrations.Migration0001``–``0019``;
step ``n`` upgrades an event from version ``n`` to ``n + 1`` and returns zero or more events.
Before version 19 events are flat objects (``eventType`` next to ``uuid``); from 19 on the
fields live under ``content``.
"""
from __future__ import annotations

import typing


if typing.TYPE_CHECKING:
    from collections.abc import Callable

JsonObject = dict[str, typing.Any]
Step = typing.Callable[[JsonObject, 'MigrationContext'], list[typing.Any]]

NULL_UUID = '00000000-0000-0000-0000-000000000000'
UNCHANGED: JsonObject = {'changed': False}


class MigrationContext(typing.NamedTuple):
    #: ``createdAt`` of the package, already formatted as the backend writes it
    created_at: str


class MigrationStepError(ValueError):
    """An event cannot be migrated (the backend would fail too)."""


# basic operations (Migrations.Utils)
def _unchanged() -> JsonObject:
    return dict(UNCHANGED)


def rename(obj: JsonObject, old: str, new: str) -> None:
    if old in obj:
        obj[new] = obj.pop(old)


def change(obj: JsonObject, key: str, fn: Callable[[typing.Any], typing.Any]) -> None:
    if key in obj:
        obj[key] = fn(obj[key])


def on_event_field(fn: Callable[[typing.Any], typing.Any]) -> Callable[[typing.Any], typing.Any]:
    """Apply ``fn`` to ``value`` of an event field object, if it has one."""
    def apply(field: typing.Any) -> typing.Any:
        if isinstance(field, dict) and 'value' in field:
            return {**field, 'value': fn(field['value'])}
        return field
    return apply


def _event_type(event: typing.Any) -> str | None:
    if isinstance(event, dict) and isinstance(event.get('eventType'), str):
        return event['eventType']
    return None


# 1 → 2: integrations added to the knowledge model
def step_01(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    if _event_type(event) == 'EditKnowledgeModelEvent':
        event = {**event, 'integrationUuids': _unchanged()}
    return [event]


# 2 → 3: question value types renamed
_VALUE_TYPES = {
    'StringValue': 'StringQuestionValueType',
    'NumberValue': 'NumberQuestionValueType',
    'DateValue': 'DateQuestionValueType',
    'TextValue': 'TextQuestionValueType',
}


def _value_type(value: typing.Any) -> typing.Any:
    return _VALUE_TYPES.get(value, value) if isinstance(value, str) else value


def step_02(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    event_type = _event_type(event)
    if event_type == 'AddQuestionEvent':
        event = dict(event)
        change(event, 'valueType', _value_type)
    elif event_type == 'EditQuestionEvent':
        event = dict(event)
        change(event, 'valueType', on_event_field(_value_type))
    return [event]


# 3 → 4: "path" becomes "parentUuid", "<entity>Uuid" becomes "entityUuid"
_ENTITY_UUID_FIELDS = {
    'Answer': 'answerUuid', 'Chapter': 'chapterUuid', 'Expert': 'expertUuid',
    'Integration': 'integrationUuid', 'Question': 'questionUuid', 'Reference': 'referenceUuid',
    'Tag': 'tagUuid',
}


def _path_to_parent_uuid(path: typing.Any) -> typing.Any:
    if isinstance(path, list) and path:
        last = path[-1]
        if isinstance(last, dict) and 'uuid' in last:
            return last['uuid']
    return NULL_UUID


def step_03(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    event_type = _event_type(event)
    if event_type is None:
        return [event]
    event = dict(event)
    if event_type in ('AddKnowledgeModelEvent', 'EditKnowledgeModelEvent'):
        rename(event, 'kmUuid', 'entityUuid')
        event.pop('path', None)
        event['parentUuid'] = NULL_UUID
        return [event]
    rename(event, 'path', 'parentUuid')
    change(event, 'parentUuid', _path_to_parent_uuid)
    for prefix in ('Add', 'Edit', 'Delete'):
        entity = event_type.removeprefix(prefix).removesuffix('Event')
        if event_type.startswith(prefix) and entity in _ENTITY_UUID_FIELDS:
            rename(event, _ENTITY_UUID_FIELDS[entity], 'entityUuid')
    return [event]


# 4 → 5 (move events), 5 → 6 (multi-choice), 12 → 13, 13 → 14, 15 → 16: nothing to migrate
def step_noop(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    return [event]


# 6 → 7: knowledge model name removed
def step_06(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    if _event_type(event) in ('AddKnowledgeModelEvent', 'EditKnowledgeModelEvent'):
        event = {key: value for key, value in event.items() if key != 'name'}
    return [event]


# 7 → 8: default phases and metrics, required level becomes required phase
_PHASES = (
    ('b101f2d0-2476-452d-aa8d-95a41a02b52c', 'eff6bbfc-8983-4799-8b89-f7a4ea37b611',
     'Before Submitting the Proposal'),
    ('1796fa3c-9f53-475f-89ff-c66a0453c42e', 'e9bfcd64-411e-424a-98c9-5b4d531f0890',
     'Before Submitting the DMP'),
    ('adc9133d-afcd-4616-9aea-db5f475898a2', 'bd22e504-295a-4ade-8fca-7f86aacddd76',
     'Before Finishing the Project'),
    ('1ace0fc6-a949-495f-a32e-e948f3f6bed1', 'fc62249c-700a-45d2-97b8-e5817468a5d5',
     'After Finishing the Project'),
)
_METRICS = (
    ('8db30660-d4e5-4c0a-bf3e-553f3f0f997a', 'b630056c-3acf-4f26-b317-50f1805402c0',
     'Findability', 'F',
     'The Findability metric describes how easily data can be located. The score associated with '
     'an answer will be higher if it makes it easier for humans or for computers to locate your '
     'data set, e.g. if it ends up in an index or has a unique resolvable identifier.'),
    ('0feac7e6-add4-4723-abae-be5ce7864c63', 'c19feec6-2ab2-4757-893a-c11c47f352b8',
     'Accessibility', 'A',
     'The Accessibility metric describes how well the access to the database is described and how '
     'easy it is to implement. The score associated with an answer will be higher if it makes it '
     'easier for humans and computers to get to the data. This is determined by e.g. the protocol '
     'for accessing the data or for authenticating users, and also by the guaranteed longevity of '
     'the repository. Note that this is different from the Openness metric!'),
    ('a42bded3-a085-45f8-b384-32b4a77c8385', '412854a9-ee08-4630-8e9a-71978c8290b3',
     'Interoperability', 'I',
     'The Interoperability metric describes how well the data interoperates with other data. The '
     'score associated with an answer will be higher if it makes it easier for humans and '
     "computers to couple the data with other data and 'understand' relationships. This is "
     'influenced by the use of standard ontologies for different fields and proper descriptions '
     'of the relations. It is also influenced by proper standard metadata that is agreed by the '
     'community.'),
    ('0bafe0c2-a8f2-4c74-80c8-dbf3a5b8e9b7', 'b0bf9ac7-cd4c-4e77-9d56-2363e558bc8e',
     'Reusability', 'R',
     'The Reusability metric describes how well the data is suitable for reuse in other context. '
     'The score associated with an answer will be higher if it makes it easier for humans and '
     'computers to reuse the data. This is influenced largely by proper description of how the '
     'data was obtained, and also by the conditions that are put on the reuse (license and, for '
     'personally identifying information, consent).'),
    ('8845fe2b-79df-4138-baea-3a035bf5e249', 'c99e578d-f4cc-4a36-94cc-1451901f11fe',
     'Good DMP Practice', 'G',
     'The Good DMP Practice metric describes how appreciated a process is among Data Stewards. A '
     'score associated with an answer will be high if a practice would be considered preferable '
     'over alternatives, generally a good idea.'),
    ('cc02c5a0-9754-4432-a7e0-ce0f3cf7a0a0', '04d738dd-3b71-4433-afd6-65b105fa71cd',
     'Openness', 'O',
     'The Openness metric describes how Open the data are available. Note that this is different '
     'from the Accessibility metric. A score associated with an answer will be high if the data '
     'will be as open as possible, and low if voluntary restrictions apply to access and re-use.'),
)
_LEVEL_TO_PHASE = {index + 1: phase[0] for index, phase in enumerate(_PHASES)}


def _level_to_phase(level: typing.Any) -> typing.Any:
    if isinstance(level, (int, float)) and not isinstance(level, bool) and level in _LEVEL_TO_PHASE:
        return _LEVEL_TO_PHASE[int(level)]
    return None


def step_07(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    event_type = _event_type(event)
    if event_type == 'AddKnowledgeModelEvent':
        km_uuid = event.get('entityUuid')
        if not isinstance(km_uuid, str):
            return [event]
        phases = [{'uuid': event_uuid, 'entityUuid': entity_uuid, 'parentUuid': km_uuid,
                   'eventType': 'AddPhaseEvent', 'title': title, 'description': None}
                  for entity_uuid, event_uuid, title in _PHASES]
        metrics = [{'uuid': event_uuid, 'entityUuid': entity_uuid, 'parentUuid': km_uuid,
                    'eventType': 'AddMetricEvent', 'title': title, 'abbreviation': abbreviation,
                    'description': description}
                   for entity_uuid, event_uuid, title, abbreviation, description in _METRICS]
        return [event, *phases, *metrics]
    if event_type == 'EditKnowledgeModelEvent':
        return [{**event, 'metricUuids': _unchanged(), 'phaseUuids': _unchanged()}]
    if event_type in ('AddQuestionEvent', 'EditQuestionEvent'):
        event = dict(event)
        rename(event, 'requiredLevel', 'requiredPhaseUuid')
        convert = _level_to_phase if event_type == 'AddQuestionEvent' else on_event_field(
            _level_to_phase)
        change(event, 'requiredPhaseUuid', convert)
    return [event]


# 8 → 9: annotations (empty object on add, unchanged on edit)
def step_08(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    event_type = _event_type(event)
    if event_type is not None and event_type.startswith('Add'):
        event = {**event, 'annotations': {}}
    elif event_type is not None and event_type.startswith('Edit'):
        event = {**event, 'annotations': _unchanged()}
    return [event]


# 9 → 10: integration response fields become Jinja templates
def _to_jinja(value: typing.Any) -> typing.Any:
    return f'{{{{item.{value}}}}}' if isinstance(value, str) else value


def step_09(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    event_type = _event_type(event)
    if event_type not in ('AddIntegrationEvent', 'EditIntegrationEvent'):
        return [event]
    event = dict(event)
    convert = _to_jinja if event_type == 'AddIntegrationEvent' else on_event_field(_to_jinja)
    rename(event, 'responseIdField', 'responseItemId')
    rename(event, 'responseNameField', 'responseItemTemplate')
    change(event, 'responseItemId', convert)
    change(event, 'responseItemTemplate', convert)
    return [event]


# 10 → 11: createdAt added; annotations and request headers become key-value lists
def _map_to_list(value: typing.Any) -> list[JsonObject]:
    if not isinstance(value, dict):
        raise MigrationStepError('Expected an object to convert into a key-value list')
    # Aeson's KeyMap is ordered by key, so the backend produces keys in sorted order
    return [{'key': key, 'value': value[key]} for key in sorted(value)]


def step_10(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    event_type = _event_type(event)
    if event_type is None:
        return [event]
    event = {**event, 'createdAt': ctx.created_at}
    if event_type.startswith('Add'):
        change(event, 'annotations', _map_to_list)
    elif event_type.startswith('Edit'):
        change(event, 'annotations', on_event_field(_map_to_list))
    if event_type == 'AddIntegrationEvent':
        change(event, 'requestHeaders', _map_to_list)
    elif event_type == 'EditIntegrationEvent':
        change(event, 'requestHeaders', on_event_field(_map_to_list))
    return [event]


# 11 → 12: integration type, empty search flag, item URL renamed
def step_11(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    event_type = _event_type(event)
    if event_type not in ('AddIntegrationEvent', 'EditIntegrationEvent'):
        return [event]
    event = {
        **event,
        'requestEmptySearch': True if event_type == 'AddIntegrationEvent' else _unchanged(),
        'integrationType': 'ApiIntegration',
    }
    rename(event, 'responseItemUrl', 'itemUrl')
    return [event]


# 14 → 15: resource collections; old resource page references lose their short UUID
def step_14(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    event_type = _event_type(event)
    if event_type == 'EditKnowledgeModelEvent':
        return [{**event, 'resourceCollectionUuids': _unchanged()}]
    if (event_type in ('AddReferenceEvent', 'EditReferenceEvent')
            and event.get('referenceType') == 'ResourcePageReference'):
        event = {key: value for key, value in event.items() if key != 'shortUuid'}
        event['resourcePageUuid'] = None if event_type == 'AddReferenceEvent' else _unchanged()
    return [event]


# 16 → 17: validations of value questions
def step_16(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    event_type = _event_type(event)
    if (event_type in ('AddQuestionEvent', 'EditQuestionEvent')
            and event.get('questionType') == 'ValueQuestion'):
        event = {**event, 'validations': [] if event_type == 'AddQuestionEvent' else _unchanged()}
    return [event]


# 17 → 18: API integrations become legacy, "props" become "variables"
def step_17(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    event_type = _event_type(event)
    if event_type in ('AddIntegrationEvent', 'EditIntegrationEvent'):
        event = dict(event)
        change(event, 'integrationType',
               lambda value: 'ApiLegacyIntegration' if value == 'ApiIntegration' else value)
        rename(event, 'props', 'variables')
    elif event_type in ('AddQuestionEvent', 'EditQuestionEvent'):
        event = dict(event)
        rename(event, 'props', 'variables')
    return [event]


# 18 → 19: event fields move under "content"
_TOP_LEVEL = ('uuid', 'parentUuid', 'entityUuid', 'createdAt')


def _has_content_already(event: JsonObject) -> bool:
    if 'content' not in event:
        return False
    content = event['content']
    event_type = event.get('eventType')
    if event_type == 'AddResourcePageEvent' and isinstance(content, str):
        return False
    return not (event_type == 'EditResourcePageEvent' and isinstance(content, dict)
                and 'changed' in content)


def step_18(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    if not isinstance(event, dict) or 'uuid' not in event or _has_content_already(event):
        return [event]
    top = {key: value for key, value in event.items() if key in _TOP_LEVEL}
    rest = {key: value for key, value in event.items() if key not in _TOP_LEVEL}
    return [{**top, 'content': rest}]


# 19 → 20: legacy API integrations become API integrations, widget integrations are dropped
_LEGACY_FIELDS = ('name', 'variables', 'requestUrl', 'requestBody', 'requestMethod',
                  'requestHeaders', 'responseListField', 'responseItemTemplate', 'annotations')


def _legacy_integration(content: JsonObject, *, add: bool) -> JsonObject:
    migrated: JsonObject = {name: content.get(name, _unchanged()) for name in _LEGACY_FIELDS}
    migrated['requestAllowEmptySearch'] = content.get('requestEmptySearch', _unchanged())
    migrated.update({
        'eventType': 'AddIntegrationEvent' if add else 'EditIntegrationEvent',
        'integrationType': 'ApiIntegration',
        'allowCustomReply': True if add else _unchanged(),
        'responseItemTemplateForSelection': None if add else _unchanged(),
        'testQ': '' if add else _unchanged(),
        'testVariables': {} if add else _unchanged(),
        'testResponse': None if add else _unchanged(),
    })
    return migrated


def step_19(event: typing.Any, ctx: MigrationContext) -> list[typing.Any]:
    if not isinstance(event, dict) or 'content' not in event:
        return []  # the backend drops events it cannot read
    content = event['content']
    event_type = _event_type(content)
    if event_type is None:
        return []
    if event_type in ('AddIntegrationEvent', 'EditIntegrationEvent'):
        integration_type = content.get('integrationType')
        if integration_type == 'WidgetIntegration':
            return []
        if integration_type == 'ApiLegacyIntegration':
            content = _legacy_integration(content, add=event_type == 'AddIntegrationEvent')
    return [{**event, 'content': content}]


STEPS: dict[int, Step] = {
    1: step_01, 2: step_02, 3: step_03, 4: step_noop, 5: step_noop, 6: step_06, 7: step_07,
    8: step_08, 9: step_09, 10: step_10, 11: step_11, 12: step_noop, 13: step_noop, 14: step_14,
    15: step_noop, 16: step_16, 17: step_17, 18: step_18, 19: step_19,
}
