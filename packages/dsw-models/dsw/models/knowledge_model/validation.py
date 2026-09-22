"""Semantic validation of a knowledge model.

Schema validation (:mod:`.flat`) checks shapes; this module checks meaning: references resolve
to the right kind of entity, every entity has one place in the tree, and the content makes sense
to a user. Each issue names the entity, where it is (``Chapter 'Data' › Question 'Reuse?'``),
what is wrong and how to fix it, so the issue can be fixed without reading the code.

Errors describe models the backend would store but that break the questionnaire or documents,
warnings likely authoring mistakes, and infos harmless leftovers such as entities that are no
longer reachable (the backend keeps them after some deletes and type changes).
"""
from __future__ import annotations

import collections
import dataclasses
import re
import typing

from . import flat, graph


if typing.TYPE_CHECKING:
    from uuid import UUID


Severity = typing.Literal['error', 'warning', 'info']

_COLOR = re.compile(r'^#[0-9a-fA-F]{6}$')
_STRING_VALIDATIONS = {'MinLengthQuestionValidation', 'MaxLengthQuestionValidation',
                       'RegexQuestionValidation', 'OrcidQuestionValidation',
                       'DoiQuestionValidation', 'DomainQuestionValidation'}
_VALIDATIONS_BY_VALUE_TYPE: dict[str, set[str]] = {
    'StringQuestionValueType': _STRING_VALIDATIONS,
    'TextQuestionValueType': _STRING_VALIDATIONS,
    'EmailQuestionValueType': _STRING_VALIDATIONS,
    'UrlQuestionValueType': _STRING_VALIDATIONS,
    'NumberQuestionValueType': {'MinNumberQuestionValidation', 'MaxNumberQuestionValidation'},
    'DateQuestionValueType': {'FromDateQuestionValidation', 'ToDateQuestionValidation'},
    'DateTimeQuestionValueType': {'FromDateTimeQuestionValidation',
                                  'ToDateTimeQuestionValidation'},
    'TimeQuestionValueType': {'FromTimeQuestionValidation', 'ToTimeQuestionValidation'},
    'ColorQuestionValueType': set(),
}


@dataclasses.dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    severity: Severity
    entity_uuid: UUID
    location: str
    message: str
    hint: str

    def __str__(self) -> str:
        return f'[{self.severity}] {self.code} at {self.location}: {self.message} {self.hint}'


def validate(km: flat.KnowledgeModel | graph.KnowledgeModel) -> list[ValidationIssue]:
    """All issues found, by severity (errors first), then in knowledge model order."""
    km_graph = km if isinstance(km, graph.KnowledgeModel) else graph.KnowledgeModel(km)
    issues = _Validator(km_graph).run()
    order = {'error': 0, 'warning': 1, 'info': 2}
    return sorted(issues, key=lambda issue: order[issue.severity])


def _describe(node: graph.Node | None) -> str:
    if node is None:
        return 'knowledge model'
    kind = type(node).__name__
    entity = node.entity
    label = next((getattr(entity, name) for name in ('title', 'label', 'name', 'url')
                  if isinstance(getattr(entity, name, None), str)), None)
    return f"{kind} '{_shorten(label)}'" if label else f'{kind} {node.uuid}'


def _shorten(text: str, limit: int = 40) -> str:
    text = ' '.join(text.split())
    return text if len(text) <= limit else f'{text[:limit - 1]}…'


def location(node: graph.Node | None) -> str:
    """Human-readable position of a node, e.g. ``Chapter 'A' › OptionsQuestion 'B'``."""
    if node is None or isinstance(node, graph._RootNode):  # noqa: SLF001
        return 'knowledge model'
    return ' › '.join(_describe(n) for n in [*reversed(node.ancestors), node])


class _Validator:

    def __init__(self, km: graph.KnowledgeModel):
        self.km = km
        self.issues: list[ValidationIssue] = []

    def _add(self, code: str, severity: Severity, node: graph.Node | None, message: str,
             hint: str) -> None:
        uuid = node.uuid if node is not None else self.km.uuid
        self.issues.append(ValidationIssue(code, severity, uuid, location(node), message, hint))

    def run(self) -> list[ValidationIssue]:
        self._references()
        self._tree()
        self._duplicates()
        reachable = self.km.reachable
        for node in self.km.nodes:
            if node.uuid not in reachable:
                continue
            check = getattr(self, f'_check_{node.kind}', None)
            if check is not None:
                check(node)
            if isinstance(node, graph.Question):
                self._check_question(node)
        return self.issues

    # structure
    def _references(self) -> None:
        for dangling in self.km.dangling:
            field = dangling.field
            if dangling.reason == 'missing':
                self._add('missing-reference', 'error', dangling.source,
                          f'{field} refers to {dangling.target_uuid}, which does not exist.',
                          f'Remove the UUID from {field} or add the missing entity.')
            else:
                target = self.km.get(dangling.target_uuid)
                self._add('wrong-reference-kind', 'error', dangling.source,
                          f'{field} refers to {_describe(target)}, which cannot be used there.',
                          f'Point {field} to an entity of the right kind.')

    def _tree(self) -> None:
        for kept, other in self.km.collisions:
            self._add('duplicate-uuid', 'error', kept,
                      f'{kept.uuid} is also the UUID of {_describe(other)}, which is ignored.',
                      'Give one of the entities a new UUID.')
        reachable = self.km.reachable
        for child, parent in self.km.shared:
            if parent.uuid not in reachable:
                continue  # leftovers are reported as unreachable
            if child is parent or child in parent.ancestors:
                self._add('containment-cycle', 'error', parent,
                          f'{_describe(child)} contains itself through {_describe(parent)}.',
                          'Remove the UUID from the child list to break the cycle.')
            else:
                self._add('multiple-parents', 'warning', child,
                          f'Also listed by {location(parent)}; an entity must have one parent.',
                          'Keep it under one parent or create a copy with a new UUID.')
        for node in self.km.unreachable:
            self._add('unreachable-entity', 'info', node,
                      'Not reachable from the knowledge model lists, so it is never shown.',
                      'Add its UUID to a parent list, or remove the entity.')

    def _duplicates(self) -> None:
        lists: list[tuple[graph.Node | None, str, list[UUID]]] = [
            (None, name, getattr(self.km.flat, name))
            for name in ('chapter_uuids', 'tag_uuids', 'integration_uuids', 'metric_uuids',
                         'phase_uuids', 'resource_collection_uuids')
        ]
        for node in self.km.nodes:
            for name, value in node.entity:
                if name.endswith('_uuids') and isinstance(value, list):
                    lists.append((node, name, value))
        for node, name, uuids in lists:
            for uuid, count in collections.Counter(uuids).items():
                if count > 1:
                    self._add('duplicate-in-list', 'error', node,
                              f'{name} lists {uuid} {count} times.',
                              'Keep each UUID once.')

    # content
    def _check_question(self, question: graph.Question) -> None:
        if not question.entity.title.strip():
            self._add('empty-title', 'warning', question, 'The question has no title.',
                      'Write the question the user should answer.')

    def _check_options_question(self, question: graph.OptionsQuestion) -> None:
        if len(question.answers) < 2:  # noqa: PLR2004
            self._add('too-few-answers', 'warning', question,
                      f'Options question has {len(question.answers)} answer(s).',
                      'Add at least two answers or use another question type.')

    def _check_multi_choice_question(self, question: graph.MultiChoiceQuestion) -> None:
        if not question.choices:
            self._add('no-choices', 'warning', question, 'Multi-choice question has no choices.',
                      'Add choices or use another question type.')

    def _check_list_question(self, question: graph.ListQuestion) -> None:
        if not question.item_template_questions:
            self._add('no-item-questions', 'warning', question,
                      'List question has no item questions.',
                      'Add questions asked for every item.')

    def _check_value_question(self, question: graph.ValueQuestion) -> None:
        allowed = _VALIDATIONS_BY_VALUE_TYPE.get(question.entity.value_type, set())
        for validation in question.entity.validations:
            if validation.type not in allowed:
                self._add('validation-type-mismatch', 'warning', question,
                          f'{validation.type} does not apply to {question.entity.value_type}.',
                          'Remove the validation or change the value type.')

    def _check_integration_question(self, question: graph.IntegrationQuestion) -> None:
        integration = question.integration
        if isinstance(integration, graph.ApiIntegration):
            expected = set(integration.entity.variables)
            actual = set(question.entity.variables)
            if expected != actual:
                self._add('integration-variables-mismatch', 'warning', question,
                          f'Variables {sorted(actual)} differ from integration '
                          f"'{integration.entity.name}' variables {sorted(expected)}.",
                          'Set a value for each integration variable and nothing else.')

    def _check_item_select_question(self, question: graph.ItemSelectQuestion) -> None:
        if question.entity.list_question_uuid is None:
            self._add('no-list-question', 'warning', question,
                      'Item select question does not select from any list question.',
                      'Set listQuestionUuid to a list question.')

    def _check_answer(self, answer: graph.Answer) -> None:
        if not answer.entity.label.strip():
            self._add('empty-label', 'warning', answer, 'The answer has no label.',
                      'Write the answer text.')
        for measure in answer.entity.metric_measures:
            if not (0 <= measure.measure <= 1 and 0 <= measure.weight <= 1):
                self._add('metric-measure-range', 'error', answer,
                          f'Metric measure {measure.measure} / weight {measure.weight} is not '
                          'between 0 and 1.',
                          'Use values from 0 to 1.')

    def _check_tag(self, tag: graph.Tag) -> None:
        if not _COLOR.match(tag.entity.color):
            self._add('invalid-color', 'warning', tag,
                      f"Color '{tag.entity.color}' is not a six-digit hexadecimal color.",
                      'Use a hexadecimal color such as #0033aa.')

    def _check_cross_reference(self, reference: graph.CrossReference) -> None:
        if reference.target is not None and reference.target is reference.parent:
            self._add('self-reference', 'warning', reference,
                      'Cross-reference points to its own question.',
                      'Point it to another question.')
