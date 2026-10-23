from __future__ import annotations

import abc
import contextlib
import copy
import logging
import re

from dsw.models.document_context import graph as dc


LOG = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'variant': 'simple',
    'version': '1',
    'annotations': {
        'key': 'json.key',
        'value': 'json.value',
    },
    'options': {
        'include_reply_objects': False,
    },
}

_INTEGER = re.compile(r'-?(0|[1-9][0-9]*)')
_DECIMAL = re.compile(r'-?(0|[1-9][0-9]*)\.[0-9]+')


def _merge_config(a: dict, b: dict) -> dict:
    for key in b:
        if isinstance(a.get(key), dict) and isinstance(b[key], dict):
            _merge_config(a[key], b[key])
        else:
            a[key] = copy.deepcopy(b[key])
    return a


def _get_annotation(annotations: dc.AnnotationsT, key: str) -> str | None:
    value = annotations.get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, list) and len(value) > 0:
        return value[0]
    return None


def _interpret_value(value: str):
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _interpret_value_strict(value: str):
    if value == 'true':
        return True
    if value == 'false':
        return False
    if _INTEGER.fullmatch(value):
        return int(value)
    return value


def _interpret_number(value: str):
    if _INTEGER.fullmatch(value):
        return int(value)
    if _DECIMAL.fullmatch(value):
        return float(value)
    return value


class ContextExtractor(abc.ABC):

    def __init__(self, ctx: dc.DocumentContext, config: dict):
        self.ctx = ctx
        self.config = config

    @abc.abstractmethod
    def extract(self):
        """Extract data from the context."""


class SimpleExtractor(ContextExtractor):
    ROOT = 'root'

    def __init__(self, ctx: dc.DocumentContext, config: dict):
        super().__init__(ctx, config)
        self._a_key = config['annotations']['key']
        self._a_val = config['annotations']['value']
        self._include_reply = config['options']['include_reply_objects']
        self._objects: dict[str, dict] = {}
        self._warned: set[str] = set()
        self._empty = False

    def _set(self, key: str, a_key: str, value, path: str):
        obj = self._objects[key]
        if self._empty:
            obj.setdefault(a_key, value)
            return
        if a_key in obj:
            LOG.warning('Replies extraction: key "%s" is written twice into one object, '
                        'the question at %s replaces the previous value', a_key, path)
        obj[a_key] = value

    def _reply(self, question: dc.Question, path: str) -> dc.Reply | None:
        if self._empty:
            return None
        return question.replies.get(path)

    def _interpret(self, value: str):
        return _interpret_value(value)

    def _string_value(self, question: dc.ValueQuestion, reply: dc.StringReply):
        return reply.value

    def _unanswered(self, path: str) -> dict | None:
        return None

    def _unanswered_options(self, question: dc.OptionsQuestion, path: str) -> dict | None:
        return None

    def _complete_answers(self, key: str, question: dc.OptionsQuestion, path: str,
                          selected: dc.Answer | None):
        pass

    def _item_select_object(self, reply: dc.ItemSelectReply, path: str) -> dict:
        return {
            '_uuid': reply.item_uuid,
            '_label': reply.item_title,
            '_path': path,
        }

    def _file_object(self, file: dc.ProjectFile, path: str) -> dict:
        return {
            '_uuid': file.uuid,
            '_name': file.name,
            '_size': file.size,
            '_content_type': file.content_type,
            '_url': file.download_url,
            '_path': path,
        }

    def _list_item_object(self, item_uuid: str, item_path: str, path: str) -> dict:
        return {
            '_uuid': item_uuid,
            '_path': path,
        }

    def _has_keys(self, questions: list[dc.Question]) -> bool:
        for question in questions:
            if _get_annotation(question.a, self._a_key) is not None:
                return True
            if isinstance(question, dc.OptionsQuestion):
                if any(self._has_keys(answer.followups) for answer in question.answers):
                    return True
            elif isinstance(question, dc.ListQuestion) and self._has_keys(question.followups):
                return True
        return False

    def _visit_chapter(self, key: str, chapter: dc.Chapter):
        a_key = _get_annotation(chapter.a, self._a_key)
        if a_key is not None:
            self._objects[chapter.uuid] = {}
            for question in chapter.questions:
                self._visit_question(chapter.uuid, question, chapter.uuid)
            self._set(key, a_key, self._objects.pop(chapter.uuid), chapter.uuid)
        else:
            for question in chapter.questions:
                self._visit_question(key, question, chapter.uuid)

    def _visit_question(self, key: str, question: dc.Question, path: str):
        path = f'{path}.{question.uuid}'
        if isinstance(question, dc.ValueQuestion):
            self._visit_value_question(key, question, path)
        elif isinstance(question, dc.IntegrationQuestion):
            self._visit_integration_question(key, question, path)
        elif isinstance(question, dc.OptionsQuestion):
            self._visit_options_question(key, question, path)
        elif isinstance(question, dc.MultiChoiceQuestion):
            self._visit_multi_choice_question(key, question, path)
        elif isinstance(question, dc.ListQuestion):
            self._visit_list_question(key, question, path)
        elif isinstance(question, dc.ItemSelectQuestion):
            self._visit_item_select_question(key, question, path)
        elif isinstance(question, dc.FileQuestion):
            self._visit_file_question(key, question, path)

    def _visit_value_question(self, key: str, question: dc.ValueQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = self._reply(question, path)

        if a_key is not None:
            obj = self._unanswered(path)
            if isinstance(reply, dc.StringReply):
                obj = {
                    '_value': self._string_value(question, reply),
                    '_path': path,
                }
                if self._include_reply:
                    obj['_reply'] = reply
            self._set(key, a_key, obj, path)

    def _visit_integration_question(self, key: str, question: dc.IntegrationQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = self._reply(question, path)

        if a_key is not None:
            obj: dict | None = self._unanswered(path)
            if isinstance(reply, dc.IntegrationReply):
                if reply.is_plain:
                    obj = {
                        '_value': reply.value,
                        '_path': path,
                    }
                else:
                    obj = {
                        '_value': reply.value,
                        '_raw': reply.raw,
                        '_path': path,
                    }
                if self._include_reply:
                    obj['_reply'] = reply
            self._set(key, a_key, obj, path)

    def _visit_options_question(self, key: str, question: dc.OptionsQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = self._reply(question, path)
        answer = reply.answer if isinstance(reply, dc.AnswerReply) else None

        if a_key is not None:
            if answer is not None:
                answer_path = f'{path}.{answer.uuid}'
                a_val = _get_annotation(answer.a, self._a_val)
                self._objects[answer_path] = {
                    '_uuid': answer.uuid,
                    '_label': answer.label,
                    '_value': None if a_val is None else self._interpret(a_val),
                    '_path': path,
                }
                if self._include_reply:
                    self._objects[answer_path]['_reply'] = reply
                for followup in answer.followups:
                    self._visit_question(answer_path, followup, answer_path)
                self._complete_answers(answer_path, question, path, answer)
                self._set(key, a_key, self._objects[answer_path], path)
            else:
                self._set(key, a_key, self._unanswered_options(question, path), path)
        else:
            if answer is not None:
                answer_path = f'{path}.{answer.uuid}'
                for followup in answer.followups:
                    self._visit_question(key, followup, answer_path)
            self._complete_answers(key, question, path, answer)

    def _visit_multi_choice_question(self, key: str, question: dc.MultiChoiceQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = self._reply(question, path)

        if a_key is not None:
            choices = []
            if isinstance(reply, dc.MultiChoiceReply):
                for choice in reply.choices:
                    a_val = _get_annotation(choice.a, self._a_val)
                    choice_obj = {
                        '_uuid': choice.uuid,
                        '_label': choice.label,
                        '_value': None if a_val is None else self._interpret(a_val),
                        '_path': path,
                    }
                    if self._include_reply:
                        choice_obj['_reply'] = reply
                    choices.append(choice_obj)
            self._set(key, a_key, choices, path)

    def _visit_list_question(self, key: str, question: dc.ListQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = self._reply(question, path)

        if a_key is None:
            if question.uuid not in self._warned and self._has_keys(question.followups):
                self._warned.add(question.uuid)
                LOG.warning('Replies extraction: list question %s has no "%s" annotation, '
                            'the annotated questions of its items are left out',
                            question.uuid, self._a_key)
            return
        items = []
        if isinstance(reply, dc.ItemListReply):
            for item_uuid in reply.items:
                item_path = f'{path}.{item_uuid}'
                self._objects[item_path] = self._list_item_object(item_uuid, item_path, path)
                if self._include_reply:
                    self._objects[item_path]['_reply'] = reply
                for followup in question.followups:
                    self._visit_question(item_path, followup, item_path)
                items.append(self._objects[item_path])
        self._set(key, a_key, items, path)

    def _visit_item_select_question(self, key: str, question: dc.ItemSelectQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = self._reply(question, path)

        if a_key is not None:
            obj = self._unanswered(path)
            if isinstance(reply, dc.ItemSelectReply):
                obj = self._item_select_object(reply, path)
                if self._include_reply:
                    obj['_reply'] = reply
            self._set(key, a_key, obj, path)

    def _visit_file_question(self, key: str, question: dc.FileQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = self._reply(question, path)

        if a_key is not None:
            obj = self._unanswered(path)
            if isinstance(reply, dc.FileReply) and reply.file is not None:
                obj = self._file_object(reply.file, path)
                if self._include_reply:
                    obj['_reply'] = reply
            self._set(key, a_key, obj, path)

    def extract(self) -> dict[str, dict]:
        self._objects.clear()
        self._warned.clear()
        self._objects[self.ROOT] = {}
        for chapter in self.ctx.km.chapters:
            self._visit_chapter(self.ROOT, chapter)
        return self._objects[self.ROOT]


class SimpleExtractorV2(SimpleExtractor):
    """Like ``simple:1``, with a complete structure, uniform objects and strict values.

    Every annotated question is present, also when unanswered and under answers that are not
    selected, every object has ``_value``, and ``json.value`` is converted only when it is
    ``true``, ``false`` or a plain integer.
    """

    def __init__(self, ctx: dc.DocumentContext, config: dict):
        super().__init__(ctx, config)
        self._item_titles: dict[str, str] = {}

    @contextlib.contextmanager
    def _empty_mode(self):
        empty, self._empty = self._empty, True
        try:
            yield
        finally:
            self._empty = empty

    def _interpret(self, value: str):
        return _interpret_value_strict(value)

    def _string_value(self, question: dc.ValueQuestion, reply: dc.StringReply):
        if question.is_number:
            return _interpret_number(reply.value)
        return reply.value

    def _unanswered(self, path: str) -> dict | None:
        return {
            '_value': None,
            '_path': path,
        }

    def _unanswered_options(self, question: dc.OptionsQuestion, path: str) -> dict | None:
        self._objects[path] = {
            '_uuid': None,
            '_label': None,
            '_value': None,
            '_path': path,
        }
        self._complete_answers(path, question, path, None)
        return self._objects.pop(path)

    def _complete_answers(self, key: str, question: dc.OptionsQuestion, path: str,
                          selected: dc.Answer | None):
        with self._empty_mode():
            for answer in question.answers:
                if selected is not None and answer.uuid == selected.uuid:
                    continue
                answer_path = f'{path}.{answer.uuid}'
                for followup in answer.followups:
                    self._visit_question(key, followup, answer_path)

    def _item_select_object(self, reply: dc.ItemSelectReply, path: str) -> dict:
        obj = super()._item_select_object(reply, path)
        obj['_value'] = reply.item_uuid
        return obj

    def _file_object(self, file: dc.ProjectFile, path: str) -> dict:
        obj = super()._file_object(file, path)
        obj['_value'] = file.uuid
        return obj

    def _list_item_object(self, item_uuid: str, item_path: str, path: str) -> dict:
        return {
            '_uuid': item_uuid,
            '_label': self._item_titles.get(item_uuid),
            '_value': item_uuid,
            '_path': item_path,
        }

    def extract(self) -> dict[str, dict]:
        visitor = dc.ReplyVisitor(context=self.ctx)
        visitor.visit()
        self._item_titles = visitor.item_titles
        return super().extract()


EXTRACTORS: dict[str, type[ContextExtractor]] = {
    'simple:1': SimpleExtractor,
    'simple:2': SimpleExtractorV2,
}


def extract_replies(ctx: dc.DocumentContext, config: dict | None = None):
    cfg = _merge_config(copy.deepcopy(DEFAULT_CONFIG), config or {})
    extractor_key = f'{cfg["variant"]}:{cfg["version"]}'
    extractor_class = EXTRACTORS.get(extractor_key)
    if extractor_class is None:
        raise ValueError(f'No extractor found for key: {extractor_key}')
    extractor = extractor_class(ctx, cfg)
    return extractor.extract()
