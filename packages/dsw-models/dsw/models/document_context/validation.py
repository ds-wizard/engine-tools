"""Checks of a document context beyond its schema (``dsw-tdk validate-context``, WEP 24).

Everything is checked against the context itself: replies are resolved in its own
``knowledgeModel``, nothing is fetched. Each finding is an :class:`Issue` with a JSON pointer
(RFC 6901) into the context.

A reply path has to follow the structure of the knowledge model, but the question does not have
to be reachable: the backend keeps the replies below an answer that is no longer chosen.
"""
from __future__ import annotations

import dataclasses
import typing
import uuid

import pydantic

from ..errors import MetamodelVersionError
from ..knowledge_model import graph
from ..project import replies as r
from ..project.paths import join_path, split_path
from ..project.walker import walk_replies
from ..strictness import load
from ..versions import DOCUMENT_TEMPLATE_METAMODEL_VERSION, MetamodelVersion
from .hash import compute_context_hash
from .wire import DocumentContext


if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


Severity = typing.Literal['error', 'warning']

_NOT_LISTED = 9999

_EXPECTED_REPLY: dict[type[graph.Question], type] = {
    graph.OptionsQuestion: r.AnswerReplyValue,
    graph.MultiChoiceQuestion: r.MultiChoiceReplyValue,
    graph.ListQuestion: r.ItemListReplyValue,
    graph.ValueQuestion: r.StringReplyValue,
    graph.IntegrationQuestion: r.IntegrationReplyValue,
    graph.ItemSelectQuestion: r.ItemSelectReplyValue,
    graph.FileQuestion: r.FileReplyValue,
}


@dataclasses.dataclass(frozen=True, slots=True)
class Issue:
    severity: Severity
    #: JSON pointer into the context, '' for the whole context
    path: str
    message: str

    def __str__(self) -> str:
        return f'[{self.severity}] {self.path or "/"}: {self.message}'


def validate_context(ctx: Mapping[str, typing.Any]) -> list[Issue]:
    """All issues of a document context (parsed JSON), errors first."""
    try:
        context = load(DocumentContext, ctx)
    except pydantic.ValidationError as e:
        # without a valid structure the other checks cannot run
        return [Issue('error', pointer(*error['loc']), error['msg']) for error in e.errors()]
    issues = [*_check_version(context), *_check_hash(ctx), *_ContentChecker(context).run()]
    return sorted(issues, key=lambda issue: issue.severity != 'error')


def pointer(*parts: typing.Any) -> str:
    """A JSON pointer (RFC 6901) from path parts."""
    return ''.join('/' + str(part).replace('~', '~0').replace('/', '~1') for part in parts)


def _check_version(context: DocumentContext) -> Iterable[Issue]:
    try:
        version = MetamodelVersion.parse(context.metamodel_version)
    except MetamodelVersionError as e:
        yield Issue('error', '/metamodelVersion', str(e))
        return
    expected = DOCUMENT_TEMPLATE_METAMODEL_VERSION.major
    if version.major != expected:
        yield Issue('error', '/metamodelVersion', f'{version} is not {expected}.x')


def _check_hash(ctx: Mapping[str, typing.Any]) -> Iterable[Issue]:
    expected = compute_context_hash(ctx)
    if ctx.get('hash') != expected:
        yield Issue('error', '/hash', f'does not match the content, which gives {expected}')


class _ContentChecker:

    def __init__(self, context: DocumentContext):
        self.context = context
        self.questionnaire = context.questionnaire
        self.km = graph.KnowledgeModel(context.knowledge_model)
        self.replies = self.questionnaire.replies
        self.issues: list[Issue] = []

    def run(self) -> list[Issue]:
        self._check_replies()
        self._check_labels()
        self._check_phase_and_version()
        self._check_order()
        self._check_required()
        return self.issues

    def _add(self, severity: Severity, path: str, message: str) -> None:
        self.issues.append(Issue(severity, path, message))

    # structure of reply paths
    def resolve(self, path: str) -> graph.Question | str:
        """The question at a reply path, or why there is none."""
        try:
            segments = [uuid.UUID(segment) for segment in split_path(path)]
        except ValueError:
            return 'is not a path of UUIDs'
        if len(segments) < 2 or len(segments) % 2:  # noqa: PLR2004
            return 'is not a reply path (chapter, question, then answer or item and question)'
        chapter = self.km.chapters_by_uuid.get(segments[0])
        if chapter is None or chapter not in self.km.chapters:
            return f'chapter {segments[0]} is not in the knowledge model'
        question = _find(chapter.questions, segments[1])
        if question is None:
            return f'question {segments[1]} is not in chapter {chapter.uuid}'
        for index in range(2, len(segments), 2):
            step, next_uuid = segments[index], segments[index + 1]
            children = self._children(question, step, join_path(*segments[:index]))
            if isinstance(children, str):
                return children
            child = _find(children, next_uuid)
            if child is None:
                return f'question {next_uuid} does not follow {step}'
            question = child
        return question

    def _children(self, question: graph.Question, step: uuid.UUID,
                  path: str) -> list[graph.Question] | str:
        """Questions below an answer or an item of ``question`` at ``path``."""
        if isinstance(question, graph.OptionsQuestion):
            answer = _find(question.answers, step)
            if answer is None:
                return f'{step} is not an answer of question {question.uuid}'
            return answer.follow_up_questions
        if isinstance(question, graph.ListQuestion):
            if step not in self._items_at(path):
                return f'{step} is not an item of the list question {question.uuid}'
            return question.item_template_questions
        return f'question {question.uuid} has no follow-up or item questions'

    def _items_at(self, path: str) -> list[uuid.UUID]:
        reply = self.replies.get(path)
        if reply is not None and isinstance(reply.value, r.ItemListReplyValue):
            return reply.value.value
        return []

    # replies
    def _check_replies(self) -> None:
        resolved: dict[str, graph.Question] = {}
        for path, reply in self.replies.items():
            question = self.resolve(path)
            where = pointer('questionnaire', 'replies', path)
            if isinstance(question, str):
                self._add('error', where, f'the path does not resolve: {question}')
                continue
            resolved[path] = question
            expected = _EXPECTED_REPLY.get(type(question))
            if expected is not None and not isinstance(reply.value, expected):
                self._add('error', where, f'a {reply.value.type} cannot answer the '
                                          f'{question.question_type} {question.uuid}')
                continue
            self._check_value(where, question, reply.value)
        self._check_item_selects(resolved)

    def _check_value(self, where: str, question: graph.Question, value: typing.Any) -> None:
        if isinstance(value, r.AnswerReplyValue):
            options = typing.cast('graph.OptionsQuestion', question)
            if _find(options.answers, value.value) is None:
                self._add('error', where, f'{value.value} is not an answer of {question.uuid}')
        elif isinstance(value, r.MultiChoiceReplyValue):
            multi = typing.cast('graph.MultiChoiceQuestion', question)
            for choice in value.value:
                if _find(multi.choices, choice) is None:
                    self._add('error', where, f'{choice} is not a choice of {question.uuid}')
        elif isinstance(value, r.FileReplyValue):
            if value.value not in {file.uuid for file in self.questionnaire.files}:
                self._add('error', where, f'file {value.value} is not in questionnaire.files')

    def _check_item_selects(self, resolved: dict[str, graph.Question]) -> None:
        items: dict[uuid.UUID, set[uuid.UUID]] = {}
        for path, question in resolved.items():
            if isinstance(question, graph.ListQuestion):
                items.setdefault(question.uuid, set()).update(self._items_at(path))
        for path, question in resolved.items():
            value = self.replies[path].value
            if not isinstance(question, graph.ItemSelectQuestion) or \
                    not isinstance(value, r.ItemSelectReplyValue):
                continue
            listed = items.get(question.list_question.uuid, set()) \
                if question.list_question is not None else set()
            if value.value not in listed:
                self._add('error', pointer('questionnaire', 'replies', path),
                          f'{value.value} is not an item of the list question it selects from')

    # other references
    def _check_labels(self) -> None:
        for path in self.questionnaire.labels:
            problem = self.resolve(path)
            if isinstance(problem, str):
                self._add('error', pointer('questionnaire', 'labels', path),
                          f'the path does not resolve: {problem}')

    def _check_phase_and_version(self) -> None:
        phase = self.questionnaire.phase_uuid
        if phase is not None and phase not in self.km.phases_by_uuid:
            self._add('error', '/questionnaire/phaseUuid', f'{phase} is not a phase of the KM')
        version = self.questionnaire.version_uuid
        if version is not None and version not in {v.uuid for v in self.questionnaire.versions}:
            self._add('error', '/questionnaire/versionUuid',
                      f'{version} is not in questionnaire.versions')

    # warnings
    def _check_order(self) -> None:
        project = self.context.project
        if project is not None:
            self._check_sorted('/project/users', [str(p.user.uuid) for p in project.users],
                               'user UUID')
            self._check_sorted('/project/groups', [str(p.group.uuid) for p in project.groups],
                               'group UUID')
            for index, permission in enumerate(project.groups):
                self._check_sorted(pointer('project', 'groups', index, 'group', 'members'),
                                   [str(m.uuid) for m in permission.group.members], 'UUID')
        self._check_sorted('/questionnaire/versions',
                           [(v.created_at, str(v.uuid)) for v in self.questionnaire.versions],
                           'createdAt and UUID')
        self._check_sorted('/questionnaire/files',
                           [str(f.uuid) for f in self.questionnaire.files], 'UUID')

    def _check_sorted(self, where: str, keys: list, order: str) -> None:
        if keys != sorted(keys):
            self._add('warning', where, f'is not sorted by {order}')

    def _check_required(self) -> None:
        # the rule of the report (project.report._Evaluator._required_now)
        phase_uuids = self.context.knowledge_model.phase_uuids
        phase_index = {phase: index for index, phase in reversed(list(enumerate(phase_uuids)))}
        current = self.questionnaire.phase_uuid
        current_index = phase_index.get(current, _NOT_LISTED) if current is not None else None
        for at in walk_replies(self.km, self.replies):
            if at.reply is not None:
                continue
            required = at.question.required_phase
            required_index = _NOT_LISTED if required is None else \
                phase_index.get(required.uuid, _NOT_LISTED)
            if current_index is not None and required_index > current_index:
                continue
            self._add('warning', pointer('questionnaire', 'replies', at.path),
                      f'"{at.question.title}" is required now and unanswered')


def _find[T: graph.Node](nodes: Iterable[T], node_uuid: uuid.UUID) -> T | None:
    return next((node for node in nodes if node.uuid == node_uuid), None)
