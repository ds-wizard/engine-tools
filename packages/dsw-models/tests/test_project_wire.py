import pydantic
import pytest
from conftest import assert_same_json, load_synthetic

from dsw.models.project import changes, events, replies
from dsw.models.strictness import load


ANY_EVENTS = pydantic.TypeAdapter(list[events.AnyProjectEvent])
CONTENT_EVENTS = pydantic.TypeAdapter(list[events.ProjectEvent])
CHANGES = pydantic.TypeAdapter(list[changes.ProjectEventChange])


def _dump(adapter, value):
    return adapter.dump_python(value, mode='json', by_alias=True)


def test_all_events_round_trip():
    data = load_synthetic('project_events.json')
    parsed = ANY_EVENTS.validate_python(data)
    assert len({type(event) for event in parsed}) == 11
    assert_same_json(data, _dump(ANY_EVENTS, parsed))


def test_content_events_exclude_comments():
    data = load_synthetic('project_events.json')
    content = [item for item in data if 'Comment' not in item['type']]
    assert len(CONTENT_EVENTS.validate_python(content)) == len(content)
    with pytest.raises(pydantic.ValidationError):
        CONTENT_EVENTS.validate_python(data)


def test_reply_values():
    data = load_synthetic('project_events.json')
    values = {}
    for item in data:
        if item['type'] == 'SetReplyEvent':
            values.setdefault(item['value']['type'], item['value'])
    assert set(values) == {
        'AnswerReply', 'StringReply', 'MultiChoiceReply', 'ItemListReply',
        'IntegrationReply', 'ItemSelectReply', 'FileReply',
    }
    reply = load(replies.Reply, {'value': values['IntegrationReply'], 'createdAt': '2026-09-14T10:00:00Z'})
    assert isinstance(reply.value, replies.IntegrationReplyValue)
    assert reply.value.value.raw == {'id': 'bio', 'tags': ['a', 1, None]}
    assert reply.to_json_data()['createdBy'] is None


def test_path_parts():
    event = ANY_EVENTS.validate_python(load_synthetic('project_events.json'))[1]
    assert len(event.path_parts) == 4
    assert event.path_parts[-1] == '00000000-0000-0000-0000-000000000208'


def test_changes_round_trip():
    data = []
    for item in load_synthetic('project_events.json'):
        change = {key: value for key, value in item.items() if key not in ('createdBy', 'createdAt')}
        if item['type'] in ('ResolveCommentThreadEvent', 'ReopenCommentThreadEvent',
                            'DeleteCommentThreadEvent', 'EditCommentEvent', 'DeleteCommentEvent'):
            change['private'] = False
        data.append(change)
    assert_same_json(data, _dump(CHANGES, CHANGES.validate_python(data)))


def test_changes_reject_server_fields():
    item = load_synthetic('project_events.json')[0]
    with pytest.raises(pydantic.ValidationError, match='Unknown keys'):
        CHANGES.validate_python([item])
