"""Traversal of :class:`graph.KnowledgeModel` with visitors.

A visitor defines ``visit_<kind>`` methods (and optionally ``leave_<kind>`` for depth-first
walks). Method lookup follows the node class hierarchy, so ``visit_options_question`` is
preferred, then ``visit_question``, then ``visit_node``, then
:meth:`KnowledgeModelVisitor.generic_visit`.

Returning :data:`SKIP` from a ``visit_*`` method skips the node's children.

Example::

    class QuestionsWithoutReferences(KnowledgeModelVisitor):
        def __init__(self):
            self.found = []

        def visit_question(self, question):
            if not question.references:
                self.found.append(question)

    visitor = QuestionsWithoutReferences()
    walk(graph.KnowledgeModel(km), visitor)
"""
from __future__ import annotations

import collections
import enum
import typing


if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from . import graph


class Control(enum.Enum):
    SKIP = 'skip'


SKIP = Control.SKIP

Order = typing.Literal['depth', 'breadth']


def _method_names(node: graph.Node, prefix: str) -> Iterator[str]:
    for cls in type(node).__mro__:
        kind = cls.__dict__.get('kind')
        if kind is not None:
            yield f'{prefix}_{kind}'


class KnowledgeModelVisitor:

    def visit(self, node: graph.Node) -> Control | None:
        return self._dispatch(node, 'visit', self.generic_visit)

    def leave(self, node: graph.Node) -> None:
        self._dispatch(node, 'leave', self.generic_leave)

    def generic_visit(self, node: graph.Node) -> Control | None:
        """Called for nodes without a matching ``visit_*`` method."""
        return None

    def generic_leave(self, node: graph.Node) -> None:
        """Called for nodes without a matching ``leave_*`` method."""

    def _dispatch(self, node: graph.Node, prefix: str, default: typing.Callable) -> typing.Any:
        for name in _method_names(node, prefix):
            method = getattr(self, name, None)
            if method is not None:
                return method(node)
        return default(node)


def iter_nodes(
    km: graph.KnowledgeModel,
    *,
    order: Order = 'depth',
    include_unreachable: bool = False,
) -> Iterator[graph.Node]:
    """All nodes reachable from the top-level lists, each once, in knowledge model order."""
    visitor = _Collector()
    walk(km, visitor, order=order, include_unreachable=include_unreachable)
    return iter(visitor.nodes)


def walk(
    km: graph.KnowledgeModel,
    visitor: KnowledgeModelVisitor,
    *,
    order: Order = 'depth',
    include_unreachable: bool = False,
) -> None:
    """Walk containment from the top-level lists; every node is visited at most once.

    ``leave_*`` methods are called only in depth-first order.
    """
    seen: set[int] = set()
    starts: list[graph.Node] = list(km.roots)
    if include_unreachable:
        # nodes without a parent first, so others are visited under their parent
        starts.extend(sorted(km.unreachable, key=lambda node: node.parent is not None))
    for start in starts:
        if order == 'depth':
            _walk_depth(start, visitor, seen)
        else:
            _walk_breadth(start, visitor, seen)


def _walk_depth(start: graph.Node, visitor: KnowledgeModelVisitor, seen: set[int]) -> None:
    stack: list[tuple[graph.Node, bool]] = [(start, False)]
    while stack:
        node, leaving = stack.pop()
        if leaving:
            visitor.leave(node)
            continue
        if id(node) in seen:
            continue
        seen.add(id(node))
        if visitor.visit(node) is SKIP:
            continue
        stack.append((node, True))
        stack.extend((child, False) for child in reversed(node.children))


def _walk_breadth(start: graph.Node, visitor: KnowledgeModelVisitor, seen: set[int]) -> None:
    queue = collections.deque([start])
    while queue:
        node = queue.popleft()
        if id(node) in seen:
            continue
        seen.add(id(node))
        if visitor.visit(node) is SKIP:
            continue
        queue.extend(node.children)


class _Collector(KnowledgeModelVisitor):

    def __init__(self):
        self.nodes: list[graph.Node] = []

    def generic_visit(self, node: graph.Node) -> None:
        self.nodes.append(node)
