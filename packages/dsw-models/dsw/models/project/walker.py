"""Walk questions of a knowledge model along project replies.

This follows what a user sees in a questionnaire: follow-up questions of the chosen answer and
item questions of every list item, with the reply (if any) at each path.
"""
from __future__ import annotations

import dataclasses
import typing

from ..knowledge_model import graph
from .paths import join_path
from .replies import AnswerReplyValue, ItemListReplyValue, Reply


if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from uuid import UUID


@dataclasses.dataclass(frozen=True, slots=True)
class QuestionAtPath:
    path: str
    question: graph.Question
    reply: Reply | None
    #: UUIDs of list items on the way, outermost first
    item_uuids: tuple[UUID, ...] = ()

    @property
    def depth(self) -> int:
        return len(self.path.split('.')) - 2


def walk_replies(
    km: graph.KnowledgeModel, replies: Mapping[str, Reply],
) -> Iterator[QuestionAtPath]:
    """Questions in questionnaire order with their reply paths, answered or not."""
    for chapter in km.chapters:
        for question in chapter.questions:
            yield from _walk_question(question, str(chapter.uuid), (), replies, ())


def _walk_question(
    question: graph.Question,
    prefix: str,
    items: tuple[UUID, ...],
    replies: Mapping[str, Reply],
    chain: tuple[UUID, ...],
) -> Iterator[QuestionAtPath]:
    if question.uuid in chain:
        return  # cyclic knowledge model; the backend would not render it either
    path = join_path(prefix, question.uuid)
    reply = replies.get(path)
    yield QuestionAtPath(path, question, reply, items)
    chain = (*chain, question.uuid)
    if reply is None:
        return
    if isinstance(question, graph.OptionsQuestion) and isinstance(reply.value, AnswerReplyValue):
        answer = next((a for a in question.answers if a.uuid == reply.value.value), None)
        if answer is not None:
            for follow_up in answer.follow_up_questions:
                yield from _walk_question(
                    follow_up, join_path(path, answer.uuid), items, replies, chain)
    elif isinstance(question, graph.ListQuestion) and isinstance(reply.value, ItemListReplyValue):
        for item_uuid in reply.value.value:
            for item_question in question.item_template_questions:
                yield from _walk_question(
                    item_question, join_path(path, item_uuid), (*items, item_uuid), replies, chain)
