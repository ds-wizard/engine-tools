import datetime
import logging

from typing import Any, Union, Optional

import dateutil.parser as dp
import jinja2
import markupsafe
import markdown

from ..exceptions import JobException
from ..model import DocumentContext
from .tests import tests


LOG = logging.getLogger(__name__)


class _JinjaEnv:

    def __init__(self):
        self._env = None  # type: Optional[jinja2.Environment]

    @property
    def env(self) -> jinja2.Environment:
        if self._env is None:
            self._env = jinja2.Environment(
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
_empty_dict = {}  # type: dict[str, Any]
_romans = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'),
           (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]


def datetime_format(iso_timestamp: Union[None, datetime.datetime, str], fmt: str):
    if iso_timestamp is None:
        return ''
    if not isinstance(iso_timestamp, datetime.datetime):
        iso_timestamp = dp.isoparse(iso_timestamp)
    return iso_timestamp.strftime(fmt)


def extract(obj, keys):
    return [obj[key] for key in keys if key in obj.keys()]


def of_alphabet(number: int):
    result = ''
    while number >= 0:
        number, remainder = divmod(number, _alphabet_size)
        result = result + _alphabet[remainder]
        if number == 0:
            break
    return result


def roman(number: int) -> str:
    result = ''
    while number > 0:
        for i, remainder in _romans:
            while number >= i:
                result += remainder
                number -= i
    return result


def xmarkdown(md_text: str):
    if md_text is None:
        return ''
    return markupsafe.Markup(markdown.markdown(
        text=md_text,
        extensions=[
            'mdx_breakless_lists',
        ]
    ))


def dot(text: str):
    if text.endswith('.') or len(text.strip()) == 0:
        return text
    return text + '.'


def _has_value(reply: dict) -> bool:
    return bool(reply) and ('value' in reply.keys()) and ('value' in reply['value'].keys())


def _get_value(reply: dict) -> Any:
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


def find_reply(replies, path, xtype='string'):
    if isinstance(path, list):
        path = reply_path(path)
    reply = replies.get(path, default=None)
    if not _has_value(reply):
        return None
    value = _get_value(reply)
    if xtype == 'int':
        return value if isinstance(value, int) else int(value)
    if xtype == 'float':
        return value if isinstance(value, float) else float(value)
    if xtype == 'list':
        return value if isinstance(value, list) else list(value)
    return str(value)


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
    except Exception as exc:
        if fail_safe:
            return ''
        raise exc  # re-raise


def to_context_obj(ctx, **options) -> DocumentContext:
    LOG.debug('DocumentContext object requested')
    result = DocumentContext(ctx, **options)
    LOG.debug('DocumentContext object created')
    result._resolve_links()
    LOG.debug('DocumentContext object links resolved')
    return result


class TemplateRenderingError(JobException):

    def __init__(self, title, message):
        super().__init__(
            job_id='',
            msg=f'{title}\n\n{message}',
            exc=None,
        )


def raise_error(message, title='Document rendering error'):
    raise TemplateRenderingError(
        title=title,
        message=message,
    )


filters = {
    'any': any,
    'all': all,
    'datetime_format': datetime_format,
    'extract': extract,
    'of_alphabet': of_alphabet,
    'roman': roman,
    'markdown': xmarkdown,
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
}
