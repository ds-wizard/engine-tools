"""Plausible document contexts (metamodel 19.0) for a knowledge model (`dsw-tdk generate-context`).

Rules from WEP 24, Appendix D: only visible questions are answered (chapter questions, the
follow-ups of the chosen answers and the item questions of each generated item), in two passes so
item selects find the items of their lists; every value is valid against its question; the same
inputs, seed and TDK version give the same bytes. Every generated context passes
:func:`dsw.models.document_context.validation.validate_context`.
"""
from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import operator
import random
import typing
import uuid

from dsw.models.common import format_timestamp
from dsw.models.document_context.hash import compute_context_hash
from dsw.models.document_context.validation import validate_context
from dsw.models.document_context.wire import DocumentContext
from dsw.models.knowledge_model import graph
from dsw.models.project.paths import join_path
from dsw.models.project.replies import Reply
from dsw.models.project.report import generate_report
from dsw.models.strictness import load
from dsw.models.versions import DOCUMENT_TEMPLATE_METAMODEL_VERSION, KM_METAMODEL_VERSION
from dsw.templating import ContextDefaults

from .profiles import PERMISSION_SETS, SHARING_MODES, VISIBILITIES, Profile
from .values import EDGE_STRINGS, WORDS, ValueGenerator


if typing.TYPE_CHECKING:
    from dsw.models.knowledge_model import flat
    from dsw.models.knowledge_model.package import KnowledgeModelBundle


Source = typing.Literal['project', 'km-editor']

DEFAULT_NOW = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
TODO_LABEL = '615b9028-5e3f-414f-b245-12d2ae2eeb20'
CLIENT_URL = 'https://wizard.example.org'
#: the `config` keys of document context 19.0, which `-D` may set
CONFIG_KEYS = ('clientUrl', 'appTitle', 'primaryColor', 'logoUrl')

# cspell:disable  # noqa: ERA001
FIRST_NAMES = ('Jane', 'John', 'Alice', 'Bob', 'Eva', 'Jan', 'Mei', 'Omar', 'Lena', 'Ravi')
LAST_NAMES = ('Doe', 'Smith', 'Novák', 'Müller', 'García', 'Chen', 'Haddad', 'Kowalski')
EDGE_NAMES = ('Žofie', 'Ἀριστοτέλης', 'محمد', '李', 'Wolfeschlegelsteinhausenbergerdorff',
              "O'Brien")
# cspell:enable  # noqa: ERA001
AFFILIATIONS = ('Example University', 'Institute of Data', 'Research Centre', None)
FILE_TYPES = ('application/pdf', 'text/csv', 'image/png', 'application/zip')
EDGE_FILE_NAMES = ('data (final) v2.csv', 'ž-ů-ě.pdf', '.hidden', 'no-extension',
                   'very-' + 'long-' * 40 + 'name.txt')


@dataclasses.dataclass(frozen=True)
class KnowledgeModelInput:
    """What the generator works from: a knowledge model and its package, or a whole context."""

    km: flat.KnowledgeModel
    #: `knowledgeModelPackage` of the context (None for a KM editor without a package)
    package: dict | None
    #: license and readme of the package, for a KM editor
    license: str = ''
    readme: str = ''
    #: the context of `--from`, whose knowledge model, package, config and workspace are kept
    base: dict | None = None


def input_from_bundle(bundle: KnowledgeModelBundle, compiled: flat.KnowledgeModel,
                      package_uuid: str | None, seed: int) -> KnowledgeModelInput:
    entry = next((p for p in bundle.packages
                  if p.id == bundle.id and p.version == bundle.version), None)
    if entry is None:
        raise ValueError(f'The bundle has no package {bundle.reference}')
    package_uuid = package_uuid or str(_seeded_uuid(random.Random(f'{seed}:package')))  # noqa: S311 (test data)
    package = {
        'uuid': package_uuid, 'id': entry.id, 'version': entry.version, 'name': entry.name,
        'description': entry.description, 'language': entry.language,
        'createdAt': format_timestamp(entry.created_at), 'workspaceUuid': None,
    }
    return KnowledgeModelInput(km=compiled, package=package, license=entry.license,
                               readme=entry.readme)


def input_from_context(context: dict) -> KnowledgeModelInput:
    wire = load(DocumentContext, context)
    return KnowledgeModelInput(km=wire.knowledge_model, package=context['knowledgeModelPackage'],
                               base=context)


@dataclasses.dataclass(frozen=True)
class Options:
    profile: Profile
    variant: int = 0
    seed: int = 0
    now: datetime.datetime = DEFAULT_NOW
    source: Source = 'project'
    #: `-D` values for `config` (keys from CONFIG_KEYS)
    config: dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class Generated:
    context: dict
    #: e.g. questions left unanswered because no valid value could be made
    warnings: list[str]


def generate_context(source: KnowledgeModelInput, options: Options) -> Generated:
    return _Generator(source, options).run()


def dumps(context: dict) -> str:
    """The file content: stable, human-readable JSON."""
    return json.dumps(context, indent=2, ensure_ascii=False) + '\n'


def finalize(context: dict) -> dict:
    """Schema order and the hash; fails if the context is not valid."""
    context = load(DocumentContext, context).to_json_data()
    context['hash'] = compute_context_hash(context)
    errors = [str(issue) for issue in validate_context(context) if issue.severity == 'error']
    if errors:
        raise ValueError('Generated an invalid context:\n' + '\n'.join(errors))
    return context


def _seeded_uuid(rng: random.Random) -> uuid.UUID:
    return uuid.UUID(int=rng.getrandbits(128), version=4)


class _Generator:

    def __init__(self, source: KnowledgeModelInput, options: Options):
        self.source = source
        self.options = options
        self.profile = options.profile
        self.n = options.variant
        # seeded test data, reproducible on purpose
        self.rng = random.Random(f'{options.seed}:{self.profile.name}:{self.n}')  # noqa: S311
        self.values = ValueGenerator(self.rng, self.profile.strings, options.now)
        self.km = graph.KnowledgeModel(source.km)
        self.editor = options.source == 'km-editor'
        self.replies: dict[str, dict] = {}
        self.items: dict[uuid.UUID, list[str]] = {}
        self.item_selects: list[tuple[graph.ItemSelectQuestion, str]] = []
        self.files: list[dict] = []
        self.users: list[dict] = []
        self.warnings: list[str] = []

    # helpers
    def new_uuid(self) -> str:
        return str(_seeded_uuid(self.rng))

    def time(self, days_ago: float) -> str:
        return format_timestamp(self.options.now - datetime.timedelta(days=days_ago))

    def count(self, bounds: tuple[int, int]) -> int:
        return self.rng.randint(*bounds)

    def edge(self) -> bool:
        return self.profile.name == 'edge'

    # the context
    def run(self) -> Generated:
        self.users = self._users()
        phase_uuid = None if self.editor else self._phase()
        self._answer_chapters()
        replies = {path: load(Reply, reply) for path, reply in self.replies.items()}
        report = generate_report(self.source.km, replies, phase_uuid).to_json_data()
        base = self.source.base or {}
        context = {
            'metamodelVersion': str(DOCUMENT_TEMPLATE_METAMODEL_VERSION),
            'hash': '',
            'workspace': base.get('workspace') or {
                'uuid': self.new_uuid(), 'name': 'Sample Workspace', 'description': None},
            'project': None if self.editor else self._project(),
            'knowledgeModelEditor': self._editor() if self.editor else None,
            'questionnaire': {
                'replies': self.replies,
                'labels': {} if self.editor else self._labels(),
                'phaseUuid': None if phase_uuid is None else str(phase_uuid),
                **self._versions(),
                'files': sorted(self.files, key=operator.itemgetter('uuid')),
                'report': {key: report[key]
                           for key in ('totalReport', 'chapterReports', 'chapters', 'metrics')},
                'language': None if self.editor else self.rng.choice((None, 'en', 'cs')),
            },
            'knowledgeModel': self.source.km.to_json_data(),
            'knowledgeModelPackage': self.source.package,
            'document': None,
            'config': self._config(base.get('config')),
        }
        return Generated(finalize(context), self.warnings)

    def _config(self, base: dict | None) -> dict:
        if base is not None:
            config = {key: base.get(key) for key in CONFIG_KEYS}
        else:
            defaults = ContextDefaults()
            config = {
                'clientUrl': CLIENT_URL,
                'appTitle': defaults.default_app_title,
                'primaryColor': defaults.default_primary_color,
                'logoUrl': defaults.default_logo_url.replace('{{clientUrl}}', CLIENT_URL),
            }
        config.update(self.options.config)
        return config

    def _phase(self) -> uuid.UUID | None:
        phases = [phase.uuid for phase in self.km.phases]
        mode = self.profile.phase
        if mode == 'none' or not phases:
            return None
        if mode == 'first':
            return phases[0]
        if mode == 'last':
            return phases[-1]
        if mode == 'random':
            return self.rng.choice([None, *phases])
        return [None, *phases][self.n % (len(phases) + 1)]

    # people
    def _person(self, index: int) -> dict:
        names = EDGE_NAMES if self.edge() and index % 2 else FIRST_NAMES
        first, last = self.rng.choice(names), self.rng.choice(LAST_NAMES)
        email = f'{first}.{last}.{index}@example.org'.lower()
        return {
            'uuid': self.new_uuid(), 'firstName': first, 'lastName': last, 'email': email,
            'affiliation': self.rng.choice(AFFILIATIONS), 'active': True, 'imageUrl': None,
            'createdAt': self.time(800 - index), 'updatedAt': self.time(400 - index),
        }

    def _users(self) -> list[dict]:
        return [self._person(index) for index in range(self.count(self.profile.users))]

    @staticmethod
    def suggestion(user: dict) -> dict:
        return {
            'uuid': user['uuid'], 'firstName': user['firstName'], 'lastName': user['lastName'],
            'gravatarHash': hashlib.md5(user['email'].encode(), usedforsecurity=False).hexdigest(),
            'imageUrl': user['imageUrl'], 'affiliation': user['affiliation'],
        }

    def _creator(self) -> dict | None:
        return self.suggestion(self.rng.choice(self.users)) if self.users else None

    def _user(self, user: dict) -> dict:
        return {key: user[key] for key in ('uuid', 'firstName', 'lastName', 'email', 'affiliation',
                                           'active', 'imageUrl', 'createdAt', 'updatedAt')}

    def _user_permissions(self) -> list[dict]:
        permissions = []
        for index, user in enumerate(self.users):
            if index == 0:
                perms = PERMISSION_SETS[-1]  # the owner
            elif self.edge():
                perms = PERMISSION_SETS[index % len(PERMISSION_SETS)]
            else:
                perms = self.rng.choice(PERMISSION_SETS)
            permissions.append({'user': self._user(user), 'perms': list(perms)})
        return sorted(permissions, key=lambda p: p['user']['uuid'])

    def _group_permissions(self) -> list[dict]:
        groups = []
        for index in range(self.count(self.profile.groups)):
            members = self.rng.sample(self.users, k=min(len(self.users), self.rng.randint(1, 4)))
            groups.append({'group': {
                'uuid': self.new_uuid(), 'name': self.values.text(2) or f'Group {index}',
                'description': self.rng.choice((None, self.values.text(5))),
                'private': self.rng.random() < 0.5,  # noqa: PLR2004
                'members': sorted(({
                    **self.suggestion(member),
                    'membershipType': 'OwnerUserGroupMembershipType' if position == 0
                    else 'MemberUserGroupMembershipType',
                } for position, member in enumerate(members)), key=operator.itemgetter('uuid')),
                'createdAt': self.time(300), 'updatedAt': self.time(200),
            }, 'perms': list(self.rng.choice(PERMISSION_SETS))})
        return sorted(groups, key=lambda g: g['group']['uuid'])

    # metadata
    def _settings(self) -> tuple[str, str]:
        if self.profile.settings == 'fixed':
            return VISIBILITIES[0], SHARING_MODES[0]
        if self.profile.settings == 'random':
            return self.rng.choice(VISIBILITIES), self.rng.choice(SHARING_MODES)
        return VISIBILITIES[self.n % 4], SHARING_MODES[self.n % 4]

    def _project(self) -> dict:
        visibility, sharing = self._settings()
        creator = None if self.edge() and self.n % 2 else self._user(self.users[0])
        tags = [self.values.text(1) for _ in range(self.count(self.profile.project_tags))]
        return {
            'uuid': self.new_uuid(), 'name': f'Generated project {self.profile.name} {self.n}',
            'description': None, 'createdBy': creator,
            'createdAt': self.time(365), 'updatedAt': self.time(1),
            'visibility': visibility, 'sharing': sharing, 'isTemplate': False,
            'knowledgeModelPackageUuid': self.source.package['uuid'] if self.source.package
            else self.new_uuid(),
            'selectedQuestionTagUuids': [str(tag.uuid) for tag in self.km.tags] if self.edge()
            else [],
            'projectTags': tags, 'documentTemplateUuid': None, 'formatUuid': None,
            'users': self._user_permissions(), 'groups': self._group_permissions(),
        }

    def _editor(self) -> dict:
        package = self.source.package
        return {
            'uuid': self.new_uuid(), 'name': f'Generated KM editor {self.profile.name} {self.n}',
            'description': '', 'createdBy': self._user(self.users[0]),
            'createdAt': self.time(30), 'updatedAt': self.time(1),
            'id': package['id'] if package else 'generated.km',
            'version': package['version'] if package else '1.0.0',
            'license': self.source.license, 'readme': self.source.readme,
            'previousPackageUuid': package['uuid'] if package else None,
            'previousPackageId': package['id'] if package else None,
            'previousPackageVersion': package['version'] if package else None,
            'knowledgeModelMetamodelVersion': KM_METAMODEL_VERSION,
        }

    def _versions(self) -> dict:
        if self.editor:
            return {'versionUuid': None, 'versions': []}
        versions = [{
            'uuid': self.new_uuid(), 'name': f'{index + 1}.0',
            'description': self.rng.choice((None, self.values.text(4))),
            'eventUuid': self.new_uuid(), 'createdBy': self._creator(),
            'createdAt': self.time(200 - index), 'updatedAt': self.time(200 - index),
        } for index in range(self.count(self.profile.versions))]
        versions.sort(key=operator.itemgetter('createdAt', 'uuid'))
        chosen = self.rng.choice([None, *versions])
        return {'versionUuid': chosen and chosen['uuid'], 'versions': versions}

    def _labels(self) -> dict:
        paths = sorted(self.replies)
        count = min(len(paths), self.count(self.profile.labels))
        return {path: [TODO_LABEL] for path in sorted(self.rng.sample(paths, k=count))}

    # replies
    def _reply(self, path: str, value: dict) -> None:
        self.replies[path] = {'value': value, 'createdBy': self._creator(),
                              'createdAt': self.time(self.rng.randint(0, 100))}

    def _answer_chapters(self) -> None:
        for chapter in self.km.chapters:
            for question in chapter.questions:
                self._visit(question, str(chapter.uuid), depth=0, lists=0, chain=())
        for question, path in self.item_selects:
            items = self.items.get(question.list_question.uuid, []) if question.list_question \
                else []
            if items:
                self._reply(path, {'type': 'ItemSelectReply', 'value': self.rng.choice(items)})

    def _wanted(self, depth: int) -> bool:
        mode = self.profile.replies
        if mode == 'none' or (mode == 'chapter' and depth > 0):
            return False
        return mode != 'random' or self.rng.random() < self.profile.reply_probability

    def _visit(self, question: graph.Question, prefix: str, depth: int, lists: int,
               chain: tuple) -> None:
        if question.uuid in chain or depth > self.profile.max_depth * 4 or not self._wanted(depth):
            return
        path = join_path(prefix, question.uuid)
        chain = (*chain, question.uuid)
        if isinstance(question, graph.OptionsQuestion):
            if question.answers:
                answer = self.rng.choice(question.answers)
                self._reply(path, {'type': 'AnswerReply', 'value': str(answer.uuid)})
                for follow_up in answer.follow_up_questions:
                    self._visit(follow_up, join_path(path, answer.uuid), depth + 1, lists, chain)
        elif isinstance(question, graph.ListQuestion):
            self._visit_list(question, path, depth, lists, chain)
        elif isinstance(question, graph.MultiChoiceQuestion):
            if question.choices:
                self._reply(path, {'type': 'MultiChoiceReply', 'value': self._choices(question)})
        elif isinstance(question, graph.ItemSelectQuestion):
            self.item_selects.append((question, path))
        else:
            self._answer_leaf(question, path)

    def _visit_list(self, question: graph.ListQuestion, path: str, depth: int, lists: int,
                    chain: tuple) -> None:
        if lists >= self.profile.max_depth:
            return
        bounds = self.profile.list_items if lists == 0 else self.profile.nested_list_items
        items = [self.new_uuid() for _ in range(self.count(bounds))]
        self.items.setdefault(question.uuid, []).extend(items)
        self._reply(path, {'type': 'ItemListReply', 'value': items})
        for item in items:
            for item_question in question.item_template_questions:
                self._visit(item_question, join_path(path, item), depth + 1, lists + 1, chain)

    def _choices(self, question: graph.MultiChoiceQuestion) -> list[str]:
        choices = [str(choice.uuid) for choice in question.choices]
        mode = self.profile.multi_choice
        if mode == 'one':
            return [self.rng.choice(choices)]
        if mode == 'all' or (mode == 'alternate' and self.n % 2):
            return choices
        if mode == 'alternate':
            return []
        return sorted(self.rng.sample(choices, k=self.rng.randint(0, len(choices))),
                      key=choices.index)

    def _answer_leaf(self, question: graph.Question, path: str) -> None:
        if isinstance(question, graph.ValueQuestion):
            value = self.values.value(question.entity)
            if value is None:
                self.warnings.append(f'Question {question.uuid} left unanswered: no candidate '
                                     'matches its regex validation')
            else:
                self._reply(path, {'type': 'StringReply', 'value': value})
        elif isinstance(question, graph.IntegrationQuestion):
            self._reply(path, {'type': 'IntegrationReply', 'value': self._integration()})
        elif isinstance(question, graph.FileQuestion) and not self.editor:
            self._reply(path, {'type': 'FileReply', 'value': self._file(question.entity)})

    def _integration(self) -> dict:
        label = self.values.text(2) or 'Item'
        if self.rng.random() < 0.3:  # noqa: PLR2004
            return {'type': 'PlainType', 'value': label}
        raw: dict[str, typing.Any] = {'id': self.new_uuid(), 'name': label}
        if self.edge():
            raw.update({'název': 'hodnota',  # cspell:disable-line
                        '😀': [1.0, 1e21, -0.0, None], 'nested': {'ü': 'ö'}})
        return {'type': 'IntegrationType', 'value': label, 'raw': raw}

    def _file(self, question: flat.FileQuestion) -> str:
        types = [t.strip() for t in (question.file_types or '').split(',') if t.strip()]
        content_type = self.rng.choice(types or list(FILE_TYPES))
        size = self.rng.randint(1, question.max_size or 10_000_000)
        name = self.rng.choice(EDGE_FILE_NAMES) if self.edge() \
            else f'{self.rng.choice(WORDS)}-{len(self.files) + 1}.{content_type.rsplit("/")[-1]}'
        file_uuid = self.new_uuid()
        self.files.append({'uuid': file_uuid, 'fileName': name, 'contentType': content_type,
                           'fileSize': size})
        return file_uuid


__all__ = ['CONFIG_KEYS', 'DEFAULT_NOW', 'EDGE_STRINGS', 'Generated', 'KnowledgeModelInput',
           'Options', 'dumps', 'finalize', 'generate_context', 'input_from_bundle',
           'input_from_context']
