import datetime
import dateutil.parser as dp
import jinja2
import markupsafe
import markdown

from typing import Any, Union, Optional

from ..exceptions import JobException
from ..model import DocumentContext
from ..logging import LOGGER


class _JinjaEnv:

    def __init__(self):
        self._env = None  # type: Optional[jinja2.Environment]

    @property
    def env(self) -> jinja2.Environment:
        if self._env is None:
            from .tests import tests
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
_empty_dict = dict()  # type: dict[str, Any]
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


def of_alphabet(n: int):
    result = ''
    while n >= 0:
        n, m = divmod(n, _alphabet_size)
        result = result + _alphabet[m]
        if n == 0:
            break
    return result


def roman(n: int) -> str:
    result = ''
    while n > 0:
        for i, r in _romans:
            while n >= i:
                result += r
                n -= i
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
    r = _get_value(reply)
    if xtype == 'int':
        return r if isinstance(r, int) else int(r)
    if xtype == 'float':
        return r if isinstance(r, float) else float(r)
    if xtype == 'list':
        return r if isinstance(r, list) else list(r)
    return str(r)


def reply_path(uuids: list) -> str:
    return '.'.join(map(str, uuids))


def jinja2_render(template_str: str, vars=None, fail_safe=False, **kwargs):
    if vars is None:
        vars = _empty_dict
    LOGGER.debug('Jinja2-in-Jinja2 rendering requested')
    try:
        j2_template = _j2_env.get_template(template_str)
        LOGGER.debug('Jinja2-in-Jinja2 template prepared')
        result = j2_template.render(**vars, **kwargs)
        LOGGER.debug('Jinja2-in-Jinja2 result finished')
        return result
    except Exception as e:
        if fail_safe:
            return ''
        raise e  # re-raise


def to_context_obj(ctx, **options) -> DocumentContext:
    LOGGER.debug('DocumentContext object requested')
    result = DocumentContext(ctx, **options)
    LOGGER.debug('DocumentContext object created')
    result._resolve_links()
    LOGGER.debug('DocumentContext object links resolved')
    return result


class TemplateRenderingError(JobException):

    def __init__(self, title, message):
        self.message = f'{title}\n\n{message}'

    def __str__(self):
        return self.message


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
