"""Hash of a document context (``hash``, document context metamodel 19.0).

``hash`` = ``"sha256:"`` + the hexadecimal SHA-256 of the canonical JSON of the context without
``hash``, without ``document`` and, when ``project`` is set, without ``knowledgeModel`` (a
project's knowledge model is determined by its package). The backend stores it as
``document.context_hash`` and uses it as the cache key of previews and as the ``ETag`` of the
document context endpoints.

The canonical JSON follows RFC 8785 as the backend writes it: object keys sorted by UTF-16 code
units, no whitespace, every number formatted as an ECMAScript double, strings escaping only
``"``, ``\\`` and control characters. Port of the backend ``DocumentContextHash`` and
``Shared.Util.JSON.Canonical``; the shared fixtures in the tests pin both to the same values.
"""
from __future__ import annotations

import hashlib
import json
import math
import typing


HASH_PREFIX = 'sha256:'

_MAX_PLAIN_EXPONENT = 21
_MIN_PLAIN_EXPONENT = -6


def compute_context_hash(context: typing.Mapping[str, typing.Any]) -> str:
    """The ``hash`` of a document context given as parsed JSON."""
    return HASH_PREFIX + hashlib.sha256(canonical_json(_strip_for_hash(context))).hexdigest()


def _strip_for_hash(context: typing.Mapping[str, typing.Any]) -> dict[str, typing.Any]:
    stripped = {key: value for key, value in context.items() if key not in ('hash', 'document')}
    if stripped.get('project') is not None:
        stripped.pop('knowledgeModel', None)
    return stripped


def canonical_json(value: typing.Any) -> bytes:
    """Canonical JSON (RFC 8785) of parsed JSON data, as UTF-8."""
    parts: list[str] = []
    _build(value, parts)
    return ''.join(parts).encode('utf-8')


def _build(value: typing.Any, parts: list[str]) -> None:
    if isinstance(value, dict):
        _build_object(value, parts)
    elif isinstance(value, list | tuple):
        _build_array(value, parts)
    else:
        parts.append(_format_scalar(value))


def _build_object(value: dict[str, typing.Any], parts: list[str]) -> None:
    parts.append('{')
    for index, key in enumerate(sorted(value, key=_utf16_sort_key)):
        if index:
            parts.append(',')
        parts.extend((_format_string(key), ':'))
        _build(value[key], parts)
    parts.append('}')


def _build_array(value: list[typing.Any] | tuple[typing.Any, ...], parts: list[str]) -> None:
    parts.append('[')
    for index, item in enumerate(value):
        if index:
            parts.append(',')
        _build(item, parts)
    parts.append(']')


def _format_scalar(value: typing.Any) -> str:
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int | float):
        return format_number(float(value))
    if isinstance(value, str):
        return _format_string(value)
    raise TypeError(f'{type(value).__name__} is not JSON data')


def _utf16_sort_key(key: str) -> bytes:
    # big-endian code units compare byte by byte in code unit order
    return _well_formed(key).encode('utf-16-be')


def _well_formed(text: str) -> str:
    # a lone surrogate (JSON "\ud800") reaches the backend as U+FFFD
    return text.encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'replace')


def _format_string(text: str) -> str:
    # the escapes of the backend are exactly those of json.dumps without ensure_ascii
    return json.dumps(_well_formed(text), ensure_ascii=False)


def format_number(value: float) -> str:
    """``value`` as ECMAScript ``Number.prototype.toString`` writes it."""
    if not math.isfinite(value):
        raise ValueError(f'{value} is not a JSON number')
    if value == 0:
        return '0'
    if value < 0:
        return '-' + format_number(-value)
    # repr() gives the shortest digits that round-trip, as ECMAScript requires
    mantissa, _, exponent = repr(value).partition('e')
    integer, _, fraction = mantissa.partition('.')
    all_digits = integer + fraction
    significant = all_digits.lstrip('0')
    # value = 0.<digits> * 10^n, in the terms of the ECMAScript algorithm
    n = len(integer) + int(exponent or 0) - (len(all_digits) - len(significant))
    digits = significant.rstrip('0')
    k = len(digits)
    if k <= n <= _MAX_PLAIN_EXPONENT:
        return digits + '0' * (n - k)
    if 0 < n <= _MAX_PLAIN_EXPONENT:
        return f'{digits[:n]}.{digits[n:]}'
    if _MIN_PLAIN_EXPONENT < n <= 0:
        return f"0.{'0' * -n}{digits}"
    e = n - 1
    mantissa = digits if k == 1 else f'{digits[0]}.{digits[1:]}'
    return f"{mantissa}e{'+' if e >= 0 else '-'}{abs(e)}"
