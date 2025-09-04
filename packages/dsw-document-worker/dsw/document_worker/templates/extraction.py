import abc

from ..model import context as dc


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


def _merge_config(a: dict, b: dict, path=None) -> dict:
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                _merge_config(a[key], b[key], path + [str(key)])
            elif a[key] != b[key]:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


def _get_annotation(annotations: dc.AnnotationsT, key: str) -> str | None:
    value = annotations.get(key, None)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        if len(value) > 0:
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
        self._objects = {}  # type: dict[str, dict]

    def _visit_chapter(self, key: str, chapter: dc.Chapter):
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
        reply = question.replies.get(path, None)

        if a_key is not None:
            if reply is not None and isinstance(reply, dc.StringReply):
                self._objects[key][a_key] = {
                    '_value': reply.value,
                    '_path': path,
                }
                if self._include_reply:
                    self._objects[key][a_key]['_reply'] = reply
            else:
                self._objects[key][a_key] = None

    def _visit_integration_question(self, key: str, question: dc.IntegrationQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = question.replies.get(path, None)

        if a_key is not None:
            self._objects[key][a_key] = None
            if reply is not None and isinstance(reply, dc.IntegrationReply):
                if reply.is_plain:
                    self._objects[key][a_key] = {
                        '_value': reply.value,
                        '_path': path,
                    }
                elif reply.is_legacy_integration:
                    self._objects[key][a_key] = {
                        '_value': reply.value,
                        '_id': reply.id,
                        '_url': reply.url,
                        '_path': path,
                    }
                else:
                    self._objects[key][a_key] = {
                        '_value': reply.value,
                        '_id': reply.id,
                        '_url': reply.url,
                        '_raw': reply.raw,
                        '_path': path,
                    }
                if self._include_reply:
                    self._objects[key][a_key]['_reply'] = reply

    def _visit_options_question(self, key: str, question: dc.OptionsQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = question.replies.get(path, None)

        if a_key is not None:
            if reply is not None and isinstance(reply, dc.AnswerReply) and reply.answer is not None:
                answer_path = f'{path}.{reply.answer_uuid}'
                a_val = _get_annotation(reply.answer.a, self._a_val)
                if a_val is not None:
                    self._objects[answer_path] = {
                        '_uuid': reply.answer_uuid,
                        '_label': reply.answer.label,
                        '_value': _interpret_value(a_val),
                        '_path': path,
                    }
                else:
                    self._objects[answer_path] = {
                        '_uuid': reply.answer_uuid,
                        '_label': reply.answer.label,
                        '_value': None,
                        '_path': path,
                    }
                if self._include_reply:
                    self._objects[answer_path]['_reply'] = reply
                for followup in reply.answer.followups:
                    self._visit_question(answer_path, followup, answer_path)
                self._objects[key][a_key] = self._objects[answer_path]
            else:
                self._objects[key][a_key] = None
        elif reply is not None and isinstance(reply, dc.AnswerReply) and reply.answer is not None:
            for followup in reply.answer.followups:
                answer_path = f'{path}.{reply.answer_uuid}'
                self._visit_question(key, followup, answer_path)

    def _visit_multi_choice_question(self, key: str, question: dc.MultiChoiceQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = question.replies.get(path, None)

        if a_key is not None:
            self._objects[key][a_key] = []
            if reply is not None and isinstance(reply, dc.MultiChoiceReply):
                for choice in reply.choices:
                    a_val = _get_annotation(choice.a, self._a_val)
                    if a_val is not None:
                        self._objects[key][a_key].append({
                            '_uuid': choice.uuid,
                            '_label': choice.label,
                            '_value': _interpret_value(a_val),
                            '_path': path,
                        })
                    else:
                        self._objects[key][a_key].append({
                            '_uuid': choice.uuid,
                            '_label': choice.label,
                            '_value': None,
                            '_path': path,
                        })
                if self._include_reply:
                    self._objects[key][a_key]['_reply'] = reply

    def _visit_list_question(self, key: str, question: dc.ListQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = question.replies.get(path, None)

        if a_key is not None:
            self._objects[key][a_key] = []
            if reply is not None and isinstance(reply, dc.ItemListReply):
                for item_uuid in reply.items:
                    item_path = f'{path}.{item_uuid}'
                    self._objects[item_path] = {
                        '_uuid': item_uuid,
                        '_path': path,
                    }
                    for followup in question.followups:
                        self._visit_question(item_path, followup, item_path)
                    self._objects[key][a_key].append(self._objects[item_path])
                if self._include_reply:
                    self._objects[key][a_key]['_reply'] = reply

    def _visit_item_select_question(self, key: str, question: dc.ItemSelectQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = question.replies.get(path, None)

        if a_key is not None:
            self._objects[key][a_key] = None
            if reply is not None and isinstance(reply, dc.ItemSelectReply):
                self._objects[key][a_key] = {
                    '_uuid': reply.item_uuid,
                    '_label': reply.item_title,
                    '_path': path,
                }
                if self._include_reply:
                    self._objects[key][a_key]['_reply'] = reply

    def _visit_file_question(self, key: str, question: dc.FileQuestion, path: str):
        a_key = _get_annotation(question.a, self._a_key)
        reply = question.replies.get(path, None)

        if a_key is not None:
            self._objects[key][a_key] = None
            if reply is not None and isinstance(reply, dc.FileReply) and reply.file is not None:
                self._objects[key][a_key] = {
                    '_uuid': reply.file.uuid,
                    '_name': reply.file.name,
                    '_size': reply.file.size,
                    '_content_type': reply.file.content_type,
                    '_url': reply.file.download_url,
                    '_path': path,
                }
                if self._include_reply:
                    self._objects[key][a_key]['_reply'] = reply

    def extract(self) -> dict[str, dict]:
        self._objects.clear()
        self._objects[self.ROOT] = {}
        for chapter in self.ctx.km.chapters:
            self._visit_chapter(self.ROOT, chapter)
        return self._objects[self.ROOT]


EXTRACTORS: dict[str, type[ContextExtractor]] = {
    'simple:1': SimpleExtractor,
}


def extract_replies(ctx: dc.DocumentContext, config: dict | None = None):
    cfg = DEFAULT_CONFIG if config is None else _merge_config(config, DEFAULT_CONFIG)
    extractor_key = f'{cfg["variant"]}:{cfg["version"]}'
    extractor_class = EXTRACTORS.get(extractor_key, None)
    if extractor_class is None:
        raise ValueError(f'No extractor found for key: {extractor_key}')
    extractor = extractor_class(ctx, cfg)
    return extractor.extract()
