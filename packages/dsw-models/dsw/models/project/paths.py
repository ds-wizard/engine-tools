"""Reply paths: dot-joined UUIDs from a chapter down to a question.

``chapter.question`` for a top-level question, ``….question.answer.followUp`` below a chosen
answer and ``….listQuestion.item.itemQuestion`` inside a list item. The last segment is always
a question UUID.
"""
from __future__ import annotations

from uuid import UUID

from .common import PATH_SEPARATOR


def join_path(*parts: UUID | str) -> str:
    return PATH_SEPARATOR.join(str(part) for part in parts if str(part))


def split_path(path: str) -> list[str]:
    return path.split(PATH_SEPARATOR) if path else []


def question_uuid(path: str) -> UUID:
    return UUID(split_path(path)[-1])


def parent_path(path: str) -> str:
    return PATH_SEPARATOR.join(split_path(path)[:-1])
