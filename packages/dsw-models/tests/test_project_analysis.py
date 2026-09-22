from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pydantic
from conftest import load_synthetic
from strategies import deterministic_uuids

from dsw.models.common import UserSuggestion
from dsw.models.document_context.wire import DocumentContext
from dsw.models.knowledge_model.builder import KnowledgeModelBuilder
from dsw.models.project import events, replies
from dsw.models.project.content import compile_project_events
from dsw.models.project.report import (
    AnsweredIndication,
    PhasesAnsweredIndication,
    generate_report,
)
from dsw.models.project.squash import squash_project_events
from dsw.models.project.versions import ProjectVersion
from dsw.models.strictness import load


EVENTS = pydantic.TypeAdapter(list[events.AnyProjectEvent])
JANE = UserSuggestion(uuid=UUID(int=7), first_name='Jane', last_name='Doe', gravatar_hash='')
JOHN = UserSuggestion(uuid=UUID(int=8), first_name='John', last_name='Doe', gravatar_hash='')
_ids = deterministic_uuids(5000)


def at(minute: int, day: int = 1) -> datetime:
    return datetime(2026, 1, day, 10, minute, tzinfo=UTC)


def set_reply(path: str, value: str, user=JANE, minute=0, day=1) -> events.SetReplyEvent:
    return events.SetReplyEvent(uuid=_ids(), path=path, created_by=user, created_at=at(minute, day),
                                value=replies.StringReplyValue(value=value))


def content_events():
    return [event for event in EVENTS.validate_python(load_synthetic('project_events.json'))
            if isinstance(event, (events.SetReplyEvent, events.ClearReplyEvent,
                                  events.SetPhaseEvent, events.SetLabelsEvent))]


# content
def test_compile_project_events():
    content = compile_project_events(content_events())
    assert content.phase_uuid is None  # the last SetPhaseEvent clears it
    assert '00000000-0000-0000-0000-000000000101.00000000-0000-0000-0000-000000000202' not in content.replies
    assert len(content.replies) == 6  # 8 sets on 7 paths, one cleared
    assert content.labels == {
        '00000000-0000-0000-0000-000000000101.00000000-0000-0000-0000-000000000201':
            [UUID('615b9028-5e3f-414f-b245-12d2ae2eeb20')],
    }
    reply = content.replies['00000000-0000-0000-0000-000000000101.00000000-0000-0000-0000-000000000201']
    assert reply.created_by is not None and reply.created_by.affiliation == 'Example University'


def test_compile_until_version_event_and_label_clearing():
    stream = content_events()
    until = stream[9]  # the first SetPhaseEvent
    content = compile_project_events(stream, until=until.uuid)
    assert content.phase_uuid == UUID('00000000-0000-0000-0000-000000000a01')
    assert content.labels == {}
    clear = events.SetLabelsEvent(uuid=_ids(), path=stream[11].path, value=[], created_at=at(59))
    assert compile_project_events([*stream, clear]).labels == {}


# squash
def test_squash_keeps_last_reply_per_user_and_path():
    first = set_reply('a.b', '1', minute=1)
    by_john = set_reply('a.b', '2', user=JOHN, minute=2)
    second = set_reply('a.b', '3', minute=3)
    third = set_reply('a.b', '4', minute=4)
    other_path = set_reply('a.c', 'x', minute=5)
    assert squash_project_events([first, by_john, second, third, other_path]) == [
        first, by_john, third, other_path]


def test_squash_respects_days_and_versions():
    morning = set_reply('a.b', '1', minute=1)
    versioned = set_reply('a.b', '2', minute=2)
    later = set_reply('a.b', '3', minute=3)
    next_day = set_reply('a.b', '4', minute=1, day=2)
    version = ProjectVersion(uuid=_ids(), name='v1', event_uuid=versioned.uuid,
                             created_at=at(2), updated_at=at(2))
    assert squash_project_events([morning, versioned, later, next_day], [version]) == [
        versioned, later, next_day]
    assert squash_project_events([morning, versioned, later, next_day]) == [later, next_day]


def test_squash_groups_by_utc_day():
    minus_one = timezone(timedelta(hours=-1))
    first = set_reply('a.b', '1').model_copy(
        update={'created_at': datetime(2026, 1, 1, 23, 30, tzinfo=minus_one)})
    second = set_reply('a.b', '2').model_copy(
        update={'created_at': datetime(2026, 1, 2, 0, 30, tzinfo=minus_one)})
    assert squash_project_events([first, second]) == [second]  # both 2 January in UTC


# report
def test_report_of_synthetic_context_matches_fixture():
    context = load(DocumentContext, load_synthetic('document_context.json'))
    report = generate_report(context.knowledge_model, context.project.replies,
                             context.project.phase_uuid, uuid=context.report.uuid,
                             now=context.report.created_at)
    assert report == context.report


def _reply(value) -> replies.Reply:
    return replies.Reply(value=value, created_at=at(0))


def test_report_counting_rules():
    b = KnowledgeModelBuilder(uuid_factory=deterministic_uuids())
    first, second = b.phase('First'), b.phase('Second')
    metric = b.metric('M')
    chapter = b.chapter('C')
    options = chapter.options_question('Options', required_phase=first)
    yes = options.answer('Yes', metric_measures=[(metric, 1.0, 1.0)])
    yes.value_question('Follow-up', required_phase=second)
    options.answer('No', metric_measures=[(metric, 0.0, 3.0)])
    unanswered = chapter.value_question('No phase')
    items = chapter.list_question('List', required_phase=first)
    item_question = items.options_question('Item options')
    item_answer = item_question.answer('Zero weight', metric_measures=[(metric, 0.5, 0.0)])
    multi = chapter.multi_choice_question('Multi')
    km = b.build()
    path = f'{chapter.uuid}'
    answers = {
        f'{path}.{options.uuid}': _reply(replies.AnswerReplyValue(value=yes.uuid)),
        f'{path}.{items.uuid}': _reply(replies.ItemListReplyValue(value=[UUID(int=1), UUID(int=2)])),
        f'{path}.{items.uuid}.{UUID(int=1)}.{item_question.uuid}':
            _reply(replies.AnswerReplyValue(value=item_answer.uuid)),
        f'{path}.{multi.uuid}': _reply(replies.MultiChoiceReplyValue(value=[])),
    }
    report = generate_report(km, answers, first.uuid)
    phases, answered = report.total_report.indications
    # answered: options, list, item 1 options; unanswered: follow-up, no phase, item 2, multi
    assert answered == AnsweredIndication(answered_questions=3, unanswered_questions=4)
    # phase 'First' counts only questions requiring 'First': options and list
    assert phases == PhasesAnsweredIndication(answered_questions=2, unanswered_questions=0)
    [summary] = report.total_report.metrics
    assert summary.measure == 1.0  # (1.0×1 + 0.5×0) / (1 + 0)
    assert unanswered.uuid in km.entities.questions


def test_report_options_question_with_unexpected_reply_counts_twice():
    b = KnowledgeModelBuilder(uuid_factory=deterministic_uuids())
    chapter = b.chapter('C')
    options = chapter.options_question('Options')
    km = b.build()
    answers = {f'{chapter.uuid}.{options.uuid}': _reply(replies.StringReplyValue(value='x'))}
    _, answered = generate_report(km, answers).total_report.indications
    assert (answered.answered_questions, answered.unanswered_questions) == (1, 1)
