"""`generate-context --from FILE --anonymize`: a context without personal data or free text.

Per WEP 24, Appendix D. Replaced: every person (users, group members, creators, and the
``createdBy`` of replies and versions: names, emails, affiliations; ``gravatarHash`` becomes ``""``
and ``imageUrl`` null), group names and descriptions, project tags, the name and description of the
project or KM editor, version names and descriptions, file names, and the string, text, email and
URL replies as well as integration replies (``value`` and every string inside ``raw``). Kept:
UUIDs, label paths, the structure, numbers and dates, the knowledge model, ``config`` and
``workspace``. The hash is recomputed.

Placeholders are deterministic: the same value always gets the same placeholder, derived from
HMAC-SHA256 keyed by the seed. Emails become ``anon-<hex>@example.org``, URLs
``https://example.org/<hex>`` and other strings lowercase letters of the original's length.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import typing
import uuid

from dsw.models.knowledge_model import flat, graph
from dsw.models.project.paths import split_path
from dsw.models.strictness import load

from .generate import Generated, KnowledgeModelInput, finalize


#: value types whose replies are free text
FREE_TEXT_TYPES = {'StringQuestionValueType', 'TextQuestionValueType', 'EmailQuestionValueType',
                   'UrlQuestionValueType'}


def anonymize_context(context: dict, seed: int) -> Generated:
    return Generated(finalize(_Anonymizer(context, seed).run()), [])


def anonymize_source(source: KnowledgeModelInput, seed: int) -> Generated:
    if source.base is None:
        raise ValueError('--anonymize needs a context (--from)')
    return anonymize_context(source.base, seed)


class _Anonymizer:

    def __init__(self, context: dict, seed: int):
        self.context = copy.deepcopy(context)
        self.key = str(seed).encode()
        self.memo: dict[tuple[str, str], str] = {}
        self.km = graph.KnowledgeModel(load(flat.KnowledgeModel, self.context['knowledgeModel']))

    # placeholders
    def _chunks(self, value: str) -> typing.Iterator[bytes]:
        for counter in range(1_000_000):
            yield hmac.new(self.key, f'{counter}\x00{value}'.encode(), hashlib.sha256).digest()

    def _make(self, kind: str, value: str) -> str:
        if value == '':
            return ''
        for chunk in self._chunks(value):
            if kind == 'email':
                placeholder = f'anon-{chunk.hex()[:12]}@example.org'
            elif kind == 'url':
                placeholder = f'https://example.org/{chunk.hex()[:12]}'
            else:
                stream = (chunk * (len(value) // len(chunk) + 1))[:max(1, len(value))]
                placeholder = ''.join(chr(ord('a') + byte % 26) for byte in stream)
            if placeholder != value:
                return placeholder
        raise RuntimeError('No placeholder found')  # practically impossible

    def text(self, value: str | None, kind: str = 'text') -> str | None:
        if value is None:
            return None
        key = (kind, value)
        if key not in self.memo:
            self.memo[key] = self._make(kind, value)
        return self.memo[key]

    # parts of the context
    def run(self) -> dict:
        project = self.context['project']
        if project is not None:
            self._named(project)
            project['createdBy'] = self._user(project['createdBy'])
            project['projectTags'] = [self.text(tag) for tag in project['projectTags']]
            for permission in project['users']:
                permission['user'] = self._user(permission['user'])
            for permission in project['groups']:
                group = permission['group']
                self._named(group)
                group['members'] = [self._suggestion(m) for m in group['members']]
        editor = self.context['knowledgeModelEditor']
        if editor is not None:
            self._named(editor)
            editor['createdBy'] = self._user(editor['createdBy'])
        questionnaire = self.context['questionnaire']
        for version in questionnaire['versions']:
            self._named(version)
            version['createdBy'] = self._suggestion(version['createdBy'])
        for file in questionnaire['files']:
            file['fileName'] = self.text(file['fileName'])
        for path, reply in questionnaire['replies'].items():
            reply['createdBy'] = self._suggestion(reply['createdBy'])
            self._reply(path, reply['value'])
        return self.context

    def _named(self, entity: dict) -> None:
        entity['name'] = self.text(entity['name'])
        entity['description'] = self.text(entity.get('description'))

    def _person(self, person: dict) -> dict:
        person = {**person, 'firstName': self.text(person['firstName']),
                  'lastName': self.text(person['lastName']),
                  'affiliation': self.text(person.get('affiliation')), 'imageUrl': None}
        if 'email' in person:
            person['email'] = self.text(person['email'], 'email')
        return person

    def _user(self, user: dict | None) -> dict | None:
        return None if user is None else self._person(user)

    def _suggestion(self, suggestion: dict | None) -> dict | None:
        if suggestion is None:
            return None
        return {**self._person(suggestion), 'gravatarHash': ''}

    def _reply(self, path: str, value: dict) -> None:
        if value['type'] == 'IntegrationReply':
            content = value['value']
            content['value'] = self.text(content['value'])
            if 'raw' in content:
                content['raw'] = self._raw(content['raw'])
        elif value['type'] == 'StringReply':
            question = self.km.questions.get(uuid.UUID(split_path(path)[-1]))
            value_type = getattr(question, 'value_type', None)
            if value_type in FREE_TEXT_TYPES:
                kind = {'EmailQuestionValueType': 'email',
                        'UrlQuestionValueType': 'url'}.get(value_type, 'text')
                value['value'] = self.text(value['value'], kind)

    def _raw(self, raw: typing.Any) -> typing.Any:
        if isinstance(raw, str):
            return self.text(raw)
        if isinstance(raw, list):
            return [self._raw(item) for item in raw]
        if isinstance(raw, dict):
            return {key: self._raw(item) for key, item in raw.items()}
        return raw

