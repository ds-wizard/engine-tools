"""Squash project events like the backend's periodic job.

Port of ``squash`` in ``Wizard.Service.Project.Event.ProjectEventService``: events are sorted by
``createdAt`` (stable), grouped by UTC day and split after every event a version points to. In
each period a reply set is dropped when a later reply set on the same path by the same user
exists; all other events are kept.
"""
from __future__ import annotations

import itertools
import typing

from ..common import utc_date
from .events import SetReplyEvent


if typing.TYPE_CHECKING:
    from collections.abc import Iterable
    from uuid import UUID

    from .events import ProjectEvent
    from .versions import ProjectVersion


_MISSING = object()


def squash_project_events(
    events: Iterable[ProjectEvent],
    versions: Iterable[ProjectVersion] = (),
) -> list[ProjectEvent]:
    version_events = {version.event_uuid for version in versions}
    ordered = sorted(events, key=lambda event: event.created_at)
    result: list[ProjectEvent] = []
    for _, day in itertools.groupby(ordered, key=lambda event: utc_date(event.created_at)):
        for period in _split_after_versions(list(day), version_events):
            result.extend(_squash_period(period))
    return result


def _split_after_versions(events: list[ProjectEvent], version_events: set[UUID]) -> list[list]:
    periods: list[list] = [[]]
    for event in events:
        periods[-1].append(event)
        if event.uuid in version_events:
            periods.append([])
    return [period for period in periods if period]


def _author(event: SetReplyEvent) -> UUID | None:
    return event.created_by.uuid if event.created_by is not None else None


def _squash_period(events: list[ProjectEvent]) -> list[ProjectEvent]:
    latest_author: dict[str, object] = {}
    kept: list[ProjectEvent] = []
    for event in reversed(events):
        if isinstance(event, SetReplyEvent):
            if latest_author.get(event.path, _MISSING) == _author(event):
                continue
            latest_author[event.path] = _author(event)
        kept.append(event)
    kept.reverse()
    return kept
