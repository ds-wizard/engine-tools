from __future__ import annotations

import typing

import jinja2.sandbox


_BYTE_SIZES = ['B', 'kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB']


def _round_size(num: float) -> str:
    return str(round(num * 100) / 100)


def byte_size_format(num: float):
    for unit in _BYTE_SIZES:
        if abs(num) < 1000.0:
            return f'{_round_size(num)} {unit}'
        num /= 1000.0
    return f'{_round_size(num)} YB'


class JinjaEnvironment(jinja2.sandbox.SandboxedEnvironment):

    def is_safe_attribute(self, obj: typing.Any, attr: str, value: typing.Any) -> bool:
        if attr in ['os', 'subprocess', 'eval', 'exec', 'popen', 'system']:
            return False
        if attr == '__setitem__' and isinstance(obj, dict):
            return True
        return super().is_safe_attribute(obj, attr, value)
