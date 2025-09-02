from .consts import CURRENT_METAMODEL_MAJOR, CURRENT_METAMODEL_MINOR


_BYTE_SIZES = ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB"]


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
    if major != CURRENT_METAMODEL_MAJOR:
        raise ValueError(f'Unsupported metamodel version: {metamodel_version} '
                         f'(expected major version {CURRENT_METAMODEL_MAJOR})')
    if minor < CURRENT_METAMODEL_MINOR:
        raise ValueError(f'Unsupported metamodel version: {metamodel_version} '
                         f'(expected at least {CURRENT_METAMODEL_MINOR} minor version)')
