import contextlib
import signal

from typing import Optional

_BYTE_SIZES = ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB"]


def _round_size(num: float) -> str:
    return str(round(num * 100) / 100)


def byte_size_format(num: float):
    for unit in _BYTE_SIZES:
        if abs(num) < 1000.0:
            return f'{_round_size(num)} {unit}'
        num /= 1000.0
    return f'{_round_size(num)} YB'


class JobTimeoutError(TimeoutError):
    pass


def _raise_timeout(signum, frame):
    raise JobTimeoutError


@contextlib.contextmanager
def timeout(t: Optional[int]):
    if t is not None:
        signal.signal(signal.SIGALRM, _raise_timeout)
        signal.alarm(t)
    reached_timeout = False
    try:
        yield
    except JobTimeoutError:
        reached_timeout = True
    finally:
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
    if reached_timeout:
        raise TimeoutError
