"""Project report: indications and metric summaries per chapter and in total."""
from __future__ import annotations

import typing
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pydantic

from ..common import BaseModel, Timestamp
from ..knowledge_model import flat
from .replies import AnswerReplyValue, ItemListReplyValue, MultiChoiceReplyValue, Reply


if typing.TYPE_CHECKING:
    from collections.abc import Mapping

    from ..knowledge_model.common import MetricMeasure


class AnsweredIndication(BaseModel):
    indication_type: typing.Literal['AnsweredIndication'] = 'AnsweredIndication'
    answered_questions: int
    unanswered_questions: int


class PhasesAnsweredIndication(BaseModel):
    indication_type: typing.Literal['PhasesAnsweredIndication'] = 'PhasesAnsweredIndication'
    answered_questions: int
    unanswered_questions: int


Indication = typing.Annotated[
    AnsweredIndication | PhasesAnsweredIndication,
    pydantic.Field(discriminator='indication_type'),
]


class MetricSummary(BaseModel):
    metric_uuid: UUID
    measure: float | None = None


class TotalReport(BaseModel):
    indications: list[Indication]
    metrics: list[MetricSummary]


class ChapterReport(BaseModel):
    chapter_uuid: UUID
    indications: list[Indication]
    metrics: list[MetricSummary]


class Report(BaseModel):
    uuid: UUID
    total_report: TotalReport
    chapter_reports: list[ChapterReport]
    chapters: list[flat.Chapter]
    metrics: list[flat.Metric]
    created_at: Timestamp
    updated_at: Timestamp


# Report generation: port of ``Wizard.Service.Report`` (evaluators and generator).
_NOT_LISTED = 9999


class _Evaluator:
    """Walks answered paths of the knowledge model like the backend report evaluators."""

    def __init__(self, km: flat.KnowledgeModel, replies: Mapping[str, Reply]):
        self.km = km
        self.replies = replies
        # first occurrence wins, like Data.List.elemIndex
        self.phase_index = {uuid: index
                            for index, uuid in reversed(list(enumerate(km.phase_uuids)))}

    def _questions(self, uuids: list[UUID]) -> list[typing.Any]:
        questions = self.km.entities.questions
        return [questions[uuid] for uuid in uuids if uuid in questions]

    def chapters(self) -> list[flat.Chapter]:
        chapters = self.km.entities.chapters
        return [chapters[uuid] for uuid in self.km.chapter_uuids if uuid in chapters]

    # indications
    def _required_now(self, question_phase: UUID | None, project_phase: UUID | None,
                      value: int) -> int:
        if project_phase is None:
            return value
        question_index = self.phase_index.get(question_phase, _NOT_LISTED) \
            if question_phase is not None else _NOT_LISTED
        project_index = self.phase_index.get(project_phase, _NOT_LISTED)
        return value if question_index <= project_index else 0

    def count(self, chapter: flat.Chapter, found: int, not_found: int,
              project_phase: UUID | None) -> int:
        path = str(chapter.uuid)
        return sum(self._count_question(q, path, found, not_found, project_phase)
                   for q in self._questions(chapter.question_uuids))

    def _count_question(self, question: typing.Any, path: str, found: int, not_found: int,
                        phase: UUID | None) -> int:
        path = f'{path}.{question.uuid}'
        required = question.required_phase_uuid
        reply = self.replies.get(path)
        if reply is None:
            return self._required_now(required, phase, not_found)
        value = reply.value
        if isinstance(question, flat.MultiChoiceQuestion):
            answered = isinstance(value, MultiChoiceReplyValue) and bool(value.value)
            return self._required_now(required, phase, found if answered else not_found)
        if isinstance(question, flat.OptionsQuestion):
            if not isinstance(value, AnswerReplyValue):
                return (self._required_now(required, phase, found)
                        + self._required_now(required, phase, not_found))
            answer = self.km.entities.answers.get(value.value)
            follow_ups = self._questions(answer.follow_up_uuids) if answer else []
            answer_path = f'{path}.{value.value}'
            return self._required_now(required, phase, found) + sum(
                self._count_question(q, answer_path, found, not_found, phase) for q in follow_ups)
        if isinstance(question, flat.ListQuestion):
            items = value.value if isinstance(value, ItemListReplyValue) else []
            current = self._required_now(required, phase, found if items else not_found)
            item_questions = self._questions(question.item_template_question_uuids)
            return current + sum(
                self._count_question(q, f'{path}.{item}', found, not_found, phase)
                for item in items for q in item_questions)
        return self._required_now(required, phase, found)

    def indications(self, chapter: flat.Chapter, project_phase: UUID | None) -> list[Indication]:
        return [
            PhasesAnsweredIndication(
                answered_questions=self.count(chapter, 1, 0, project_phase),
                unanswered_questions=self.count(chapter, 0, 1, project_phase),
            ),
            AnsweredIndication(
                answered_questions=self.count(chapter, 1, 0, None),
                unanswered_questions=self.count(chapter, 0, 1, None),
            ),
        ]

    # metrics
    def measures(self, chapter: flat.Chapter) -> list[MetricMeasure]:
        path = str(chapter.uuid)
        return [m for q in self._questions(chapter.question_uuids)
                for m in self._question_measures(q, path)]

    def _question_measures(self, question: typing.Any, path: str) -> list[MetricMeasure]:
        path = f'{path}.{question.uuid}'
        reply = self.replies.get(path)
        if reply is None:
            return []
        value = reply.value
        if isinstance(question, flat.OptionsQuestion) and isinstance(value, AnswerReplyValue):
            answer = self.km.entities.answers.get(value.value)
            if answer is None:
                return []
            answer_path = f'{path}.{value.value}'
            return [*answer.metric_measures, *(
                m for q in self._questions(answer.follow_up_uuids)
                for m in self._question_measures(q, answer_path))]
        if isinstance(question, flat.ListQuestion) and isinstance(value, ItemListReplyValue):
            item_questions = self._questions(question.item_template_question_uuids)
            return [m for item in value.value for q in item_questions
                    for m in self._question_measures(q, f'{path}.{item}')]
        return []

    def metrics(self, chapter: flat.Chapter | None) -> list[MetricSummary]:
        chapters = [chapter] if chapter is not None else self.chapters()
        measures = [m for ch in chapters for m in self.measures(ch)]
        metrics = self.km.entities.metrics
        result = []
        for metric_uuid in self.km.metric_uuids:
            if metric_uuid not in metrics:
                continue
            weighted = [(m.measure, m.weight) for m in measures if m.metric_uuid == metric_uuid]
            if weighted:
                result.append(MetricSummary(metric_uuid=metric_uuid,
                                            measure=_weight_average(weighted)))
        return result


def _weight_average(values: list[tuple[float, float]]) -> float:
    weights = sum(weight for _, weight in values)
    if weights == 0:
        return 0.0
    return sum(measure * weight for measure, weight in values) / weights


def generate_report(
    km: flat.KnowledgeModel,
    replies: Mapping[str, Reply],
    phase_uuid: UUID | None = None,
    *,
    uuid: UUID | None = None,
    now: datetime | None = None,
) -> Report:
    """Indications and metrics of a project, as the backend puts them into the document context."""
    evaluator = _Evaluator(km, replies)
    chapter_indications = []
    chapter_reports = []
    for chapter in evaluator.chapters():
        indications = evaluator.indications(chapter, phase_uuid)
        chapter_indications.append(indications)
        chapter_reports.append(ChapterReport(chapter_uuid=chapter.uuid, indications=indications,
                                             metrics=evaluator.metrics(chapter)))
    total = [
        PhasesAnsweredIndication(
            answered_questions=sum(i[0].answered_questions for i in chapter_indications),
            unanswered_questions=sum(i[0].unanswered_questions for i in chapter_indications),
        ),
        AnsweredIndication(
            answered_questions=sum(i[1].answered_questions for i in chapter_indications),
            unanswered_questions=sum(i[1].unanswered_questions for i in chapter_indications),
        ),
    ]
    timestamp = now or datetime.now(tz=UTC)
    return Report(
        uuid=uuid or uuid4(),
        total_report=TotalReport(indications=total, metrics=evaluator.metrics(None)),
        chapter_reports=chapter_reports,
        chapters=[km.entities.chapters[key] for key in sorted(km.entities.chapters)],
        metrics=[km.entities.metrics[key] for key in sorted(km.entities.metrics)],
        created_at=timestamp,
        updated_at=timestamp,
    )
