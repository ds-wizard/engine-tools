import contextlib
import pdfrw  # type: ignore
import io
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


class PdfWaterMarker:

    _watermark = None
    _underneath = True

    @classmethod
    def initialize(cls, watermark_top: bool, watermark_filename: Optional[str]):
        cls.set_watermark_top(watermark_top)
        cls.set_watermark_file(watermark_filename)

    @classmethod
    def set_watermark_top(cls, watermark_top: bool):
        cls._underneath = not watermark_top

    @classmethod
    def set_watermark_file(cls, watermark_filename: Optional[str]):
        if watermark_filename is None:
            cls._watermark = None
        cls._watermark = pdfrw.PageMerge().add(
            pdfrw.PdfReader(fname=watermark_filename).pages[0],
        )[0]

    @classmethod
    def set_watermark_bytes(cls, watermark_pdf: Optional[bytes]):
        if watermark_pdf is None:
            cls._watermark = None
        cls._watermark = pdfrw.PageMerge().add(
            pdfrw.PdfReader(fdata=watermark_pdf).pages[0],
        )[0]

    @classmethod
    def create_watermark(cls, doc_pdf: bytes) -> bytes:
        if cls._watermark is None:
            return doc_pdf
        trailer = pdfrw.PdfFileReader(fdata=doc_pdf)
        for page in trailer.pages:
            pdfrw.PageMerge(page).add(
                cls._watermark,
                prepend=cls._underneath,
            ).render()
        stream = io.BytesIO()
        pdfrw.PdfWriter(stream, trailer=trailer).write()
        result_pdf = stream.getvalue()
        stream.close()
        return result_pdf
