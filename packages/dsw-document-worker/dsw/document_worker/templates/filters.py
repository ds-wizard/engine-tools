import datetime
import logging
import re
import typing

import dateutil.parser as dp
import jinja2
import markdown
import markdown.preprocessors
import markupsafe

from dsw.document_worker.utils import byte_size_format

from ..exceptions import JobError
from ..model import DocumentContext
from ..utils import JinjaEnvironment
from .extraction import extract_replies
from .tests import tests


LOG = logging.getLogger(__name__)


class DSWMarkdownExt(markdown.extensions.Extension):

    @typing.override
    def extendMarkdown(self, md):
        md.preprocessors.register(DSWMarkdownProcessor(md), 'dsw_markdown', 27)
        md.registerExtension(self)


class DSWMarkdownProcessor(markdown.preprocessors.Preprocessor):
    LI_RE = re.compile(r'^[ ]*((\d+\.)|[*+-])[ ]+.*')

    def __init__(self, md):
        super().__init__(md)

    def run(self, lines):
        prev_li = False
        new_lines = []

        for line in lines:
            # Add line break before the first list item
            if self.LI_RE.match(line):
                if not prev_li:
                    new_lines.append('')
                prev_li = True
            elif line == '':
                prev_li = False

            # Replace trailing un-escaped backslash with (supported) two spaces
            _line = line.rstrip('\\')
            if line[-1:] == '\\' and (len(line) - len(_line)) % 2 == 1:
                new_lines.append(f'{line[:-1]}  ')
                continue

            new_lines.append(line)

        return new_lines


class _JinjaEnv:

    def __init__(self):
        self._env: jinja2.Environment | None = None

    @property
    def env(self) -> jinja2.Environment:
        if self._env is None:
            self._env = JinjaEnvironment(
                loader=_base_jinja_loader,
                extensions=['jinja2.ext.do'],
            )
            self._env.filters.update(filters)
            self._env.tests.update(tests)
        return self._env

    def get_template(self, template_str: str) -> jinja2.Template:
        return self.env.from_string(source=template_str)


_alphabet = [chr(x) for x in range(ord('a'), ord('z') + 1)]
_alphabet_size = len(_alphabet)
_base_jinja_loader = jinja2.BaseLoader()
_j2_env = _JinjaEnv()
_empty_dict: dict[str, typing.Any] = {}
_romans = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'),
           (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]


def datetime_format(iso_timestamp: None | datetime.datetime | str, fmt: str):
    if iso_timestamp is None:
        return ''
    if not isinstance(iso_timestamp, datetime.datetime):
        iso_timestamp = dp.isoparse(iso_timestamp)
    return iso_timestamp.strftime(fmt)


def extract(obj, keys):
    return [obj[key] for key in keys if key in obj]


def of_alphabet(n: int) -> str:
    result = []
    while n >= 0:
        n, m = divmod(n, _alphabet_size)
        result.append(_alphabet[m])
        n = n - 1
    return ''.join(reversed(result))


def roman(n: int) -> str:
    result = ''
    while n > 0:
        for i, r in _romans:
            while n >= i:
                result += r
                n -= i
    return result


def render_markdown(md_text: str):
    if md_text is None:
        return ''
    return markupsafe.Markup(markdown.markdown(
        text=md_text,
        extensions=[
            DSWMarkdownExt(),
        ],
    ))


def dot(text: str):
    if text.endswith('.') or len(text.strip()) == 0:
        return text
    return text + '.'


def _has_value(reply: dict) -> bool:
    return bool(reply) and ('value' in reply) and ('value' in reply['value'])


def _get_value(reply: dict) -> typing.Any:
    return reply['value']['value']


def reply_str_value(reply: dict) -> str:
    if _has_value(reply):
        return str(_get_value(reply))
    return ''


def reply_int_value(reply: dict) -> int:
    if _has_value(reply):
        return int(_get_value(reply))
    return 0


def reply_float_value(reply: dict) -> float:
    if _has_value(reply):
        return float(_get_value(reply))
    return 0


def reply_items(reply: dict) -> list:
    if _has_value(reply) and isinstance(_get_value(reply), list):
        return _get_value(reply)
    return []


def find_reply(replies, path, cast_type='string'):
    if isinstance(path, list):
        path = reply_path(path)
    reply = replies.get(path, default=None)
    if not _has_value(reply):
        return None
    r = _get_value(reply)
    if cast_type == 'int':
        return r if isinstance(r, int) else int(r)
    if cast_type == 'float':
        return r if isinstance(r, float) else float(r)
    if cast_type == 'list':
        return r if isinstance(r, list) else list(r)
    return str(r)


def reply_path(uuids: list) -> str:
    return '.'.join(map(str, uuids))


def jinja2_render(template_str: str, variables=None, fail_safe=False, **kwargs):
    if variables is None:
        variables = _empty_dict
    LOG.debug('Jinja2-in-Jinja2 rendering requested')
    try:
        j2_template = _j2_env.get_template(template_str)
        LOG.debug('Jinja2-in-Jinja2 template prepared')
        result = j2_template.render(**variables, **kwargs)
        LOG.debug('Jinja2-in-Jinja2 result finished')
        return result
    except Exception as e:
        if fail_safe:
            return ''
        raise e  # re-raise


def to_context_obj(ctx, **options) -> DocumentContext:
    LOG.debug('DocumentContext object requested')
    result = DocumentContext(ctx=ctx, **options)
    LOG.debug('DocumentContext object created')
    result.resolve_links()
    LOG.debug('DocumentContext object links resolved')
    return result


class TemplateTriggeredError(JobError):
    """Error invoked from a template to report a problem to a user (not system)."""

    def __init__(self, title, message):
        super().__init__(
            job_id='',
            msg=f'{title}\n\n{message}',
            exc=None,
            skip_reporting=True,
        )


def raise_error(message, title='Document rendering error'):
    raise TemplateTriggeredError(
        title=title,
        message=message,
    )


filters = {
    'any': any,
    'all': all,
    'bytesize_format': byte_size_format,
    'datetime_format': datetime_format,
    'extract': extract,
    'of_alphabet': of_alphabet,
    'roman': roman,
    'markdown': render_markdown,
    'dot': dot,
    'reply_str_value': reply_str_value,
    'reply_int_value': reply_int_value,
    'reply_float_value': reply_float_value,
    'reply_items': reply_items,
    'find_reply': find_reply,
    'reply_path': reply_path,
    'to_context_obj': to_context_obj,
    'jinja2': jinja2_render,
    'error': raise_error,
    'extract_replies': extract_replies,
}
