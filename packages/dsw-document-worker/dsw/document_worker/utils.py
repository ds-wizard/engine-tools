import typing

import jinja2.sandbox

from . import consts


_BYTE_SIZES = ['B', 'kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB']


def _round_size(num: float) -> str:
    return str(round(num * 100) / 100)


def byte_size_format(num: float):
    for unit in _BYTE_SIZES:
        if abs(num) < 1000.0:
            return f'{_round_size(num)} {unit}'
        num /= 1000.0
    return f'{_round_size(num)} YB'


def check_metamodel_version(metamodel_version: str):
    version_parts = metamodel_version.split('.')
    try:
        major = int(version_parts[0]) if len(version_parts) > 0 else 0
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
    except ValueError as e:
        raise ValueError(f'Invalid metamodel version format: {metamodel_version}') from e
    if major != consts.CURRENT_METAMODEL_MAJOR:
        raise ValueError(f'Unsupported metamodel version: {metamodel_version} '
                         f'(expected major version {consts.CURRENT_METAMODEL_MAJOR})')
    if minor < consts.CURRENT_METAMODEL_MINOR:
        raise ValueError(f'Unsupported metamodel version: {metamodel_version} '
                         f'(expected at least {consts.CURRENT_METAMODEL_MINOR} minor version)')


class JinjaEnvironment(jinja2.sandbox.SandboxedEnvironment):

    def is_safe_attribute(self, obj: typing.Any, attr: str, value: typing.Any) -> bool:
        if attr in ['os', 'subprocess', 'eval', 'exec', 'popen', 'system']:
            return False
        if attr == '__setitem__' and isinstance(obj, dict):
            return True
        return super().is_safe_attribute(obj, attr, value)
