_BYTE_SIZES = ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB"]


def _round_size(num: float) -> str:
    return str(round(num * 100) / 100)


def byte_size_format(num: float):
    for unit in _BYTE_SIZES:
        if abs(num) < 1000.0:
            return f'{_round_size(num)} {unit}'
        num /= 1000.0
    return f'{_round_size(num)} YB'
