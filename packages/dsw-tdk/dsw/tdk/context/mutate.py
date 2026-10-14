"""`generate-context --from FILE --mutate`: an existing context, perturbed at the profile's rate.

Per WEP 24, Appendix D, with the rate ``p`` of the profile (``empty`` 1.0 drops everything, ``full``
only adds): each answered question is dropped with probability ``p`` and then re-answered with
probability ``p``; each list gets or loses one item with probability ``p``; ``ceil(p × n)`` users
are added or removed (at least one ADMIN stays). Dropping a reply or an item drops the replies
below it and the item selects of a removed item. The report, the sort orders and the hash are
recomputed.
"""
from __future__ import annotations

import copy
import math
import operator
import uuid

from dsw.models.knowledge_model import graph
from dsw.models.project.paths import split_path
from dsw.models.project.replies import Reply
from dsw.models.project.report import generate_report
from dsw.models.strictness import load

from .generate import Generated, KnowledgeModelInput, Options, _Generator, finalize
from .profiles import PERMISSION_SETS


def mutate_context(source: KnowledgeModelInput, options: Options) -> Generated:
    return _Mutator(source, options).run()


class _Mutator:

    def __init__(self, source: KnowledgeModelInput, options: Options):
        if source.base is None:
            raise ValueError('--mutate needs a context (--from)')
        self.context: dict = copy.deepcopy(source.base)
        self.gen = _Generator(source, options)
        self.rng = self.gen.rng
        self.p = options.profile.mutation_rate
        self.additions_only = options.profile.name == 'full'
        self.km = self.gen.km
        self.questionnaire = self.context['questionnaire']
        self.replies: dict[str, dict] = self.questionnaire['replies']
        project = self.context['project']
        self.gen.users = [p['user'] for p in project['users']] if project else []
        self.gen.editor = project is None
        self.gen.files = self.questionnaire['files']

    def happens(self) -> bool:
        return self.rng.random() < self.p

    def run(self) -> Generated:
        self._drop_replies()
        self._change_lists()
        self._answer_again()
        if self.context['project'] is not None:
            self._change_users()
        replies = {path: load(Reply, reply) for path, reply in self.replies.items()}
        phase = self.questionnaire['phaseUuid']
        report = generate_report(self.gen.source.km, replies,
                                 None if phase is None else uuid.UUID(phase)).to_json_data()
        self.questionnaire['report'] = {key: report[key] for key in (
            'totalReport', 'chapterReports', 'chapters', 'metrics')}
        self.questionnaire['files'] = sorted(self.gen.files, key=operator.itemgetter('uuid'))
        self.questionnaire['labels'] = {path: labels for path, labels
                                        in self.questionnaire['labels'].items()
                                        if path in self.replies}
        return Generated(finalize(self.context), self.gen.warnings)

    # removals
    def _remove(self, path: str) -> None:
        """Remove a reply and everything below it."""
        for other in [p for p in self.replies if p == path or p.startswith(path + '.')]:
            del self.replies[other]

    def _remove_item_selects(self, item: str) -> None:
        for path, reply in list(self.replies.items()):
            value = reply['value']
            if value['type'] == 'ItemSelectReply' and value['value'] == item:
                del self.replies[path]

    def _drop_replies(self) -> None:
        if self.additions_only:
            return
        for path in sorted(self.replies):
            if path in self.replies and self.happens():
                value = self.replies[path]['value']
                if value['type'] == 'ItemListReply':
                    for item in value['value']:
                        self._remove_item_selects(item)
                self._remove(path)

    def _change_lists(self) -> None:
        for path in sorted(self.replies):
            value = self.replies.get(path, {}).get('value', {})
            if value.get('type') != 'ItemListReply' or not self.happens():
                continue
            if value['value'] and not self.additions_only and self.rng.random() < 0.5:  # noqa: PLR2004
                item = self.rng.choice(value['value'])
                value['value'].remove(item)
                self._remove(f'{path}.{item}')
                self._remove_item_selects(item)
            else:
                value['value'].append(self.gen.new_uuid())

    # re-answers
    def _question(self, path: str) -> graph.Question | None:
        return self.km.questions.get(uuid.UUID(split_path(path)[-1]))

    def _items_of(self, list_question: graph.ListQuestion | None) -> list[str]:
        if list_question is None:
            return []
        items = []
        for path, reply in self.replies.items():
            question = self._question(path)
            if question is not None and question.uuid == list_question.uuid:
                items.extend(reply['value']['value'])
        return items

    def _answer_again(self) -> None:
        for path in sorted(self.replies):
            question = self._question(path)
            if question is None or not self.happens():
                continue
            value = self._new_value(question)
            if value is not None:
                self.gen._reply(path, value)  # noqa: SLF001

    def _new_value(self, question: graph.Question) -> dict | None:  # noqa: PLR0911
        gen = self.gen
        if isinstance(question, graph.OptionsQuestion):
            if not question.answers:
                return None
            return {'type': 'AnswerReply', 'value': str(self.rng.choice(question.answers).uuid)}
        if isinstance(question, graph.MultiChoiceQuestion):
            return {'type': 'MultiChoiceReply', 'value': gen._choices(question)} \
                if question.choices else None  # noqa: SLF001
        if isinstance(question, graph.ItemSelectQuestion):
            items = self._items_of(question.list_question)
            return {'type': 'ItemSelectReply', 'value': self.rng.choice(items)} if items else None
        if isinstance(question, graph.ValueQuestion):
            text = gen.values.value(question.entity)
            return None if text is None else {'type': 'StringReply', 'value': text}
        if isinstance(question, graph.IntegrationQuestion):
            return {'type': 'IntegrationReply', 'value': gen._integration()}  # noqa: SLF001
        if isinstance(question, graph.FileQuestion) and not gen.editor:
            return {'type': 'FileReply', 'value': gen._file(question.entity)}  # noqa: SLF001
        return None  # list questions change through their items

    # people
    def _change_users(self) -> None:
        users: list[dict] = self.context['project']['users']
        for _ in range(math.ceil(self.p * len(users))):
            if self.rng.random() < 0.5 or self.additions_only:  # noqa: PLR2004
                person = self.gen._person(len(users) + 1)  # noqa: SLF001
                users.append({'user': self.gen._user(person),  # noqa: SLF001
                              'perms': list(self.rng.choice(PERMISSION_SETS))})
                continue
            admins = [u for u in users if 'ADMIN' in u['perms']]
            removable = [u for u in users if 'ADMIN' not in u['perms'] or len(admins) > 1]
            if removable:
                users.remove(self.rng.choice(removable))
        users.sort(key=lambda u: u['user']['uuid'])

