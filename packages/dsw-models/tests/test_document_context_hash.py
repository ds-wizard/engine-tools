"""Port of the backend ``DocumentContextHashSpec``; the fixtures and hashes are shared with it."""
import math
import struct

import pytest
from conftest import load_synthetic
from hypothesis import given
from hypothesis import strategies as st

from dsw.models.document_context.hash import canonical_json, compute_context_hash, format_number


PROJECT_FIXTURE = 'document_context_hash_fixture.json'
KM_EDITOR_FIXTURE = 'document_context_km_editor_fixture.json'
WORKER_FIXTURE = 'document_context_worker_fixture.json'
EDGE_FIXTURE = 'document_context_hash_edge_fixture.json'

PROJECT_HASH = 'sha256:138582554e1abfd6ab46579d563f9ee19b7935de6908f0314556c577ffb15e65'
KM_EDITOR_HASH = 'sha256:08c62b1530cb7a6f526e5bd1e941d72a921665285df1c4d5454997b1ad9806b7'
EDGE_HASH = 'sha256:7357368c501cc707de06a6b915939c073e77438b053e46ebc03a82a595e1190c'


@pytest.mark.parametrize(('fixture', 'expected'), [
    (PROJECT_FIXTURE, PROJECT_HASH),
    (KM_EDITOR_FIXTURE, KM_EDITOR_HASH),
    (WORKER_FIXTURE, PROJECT_HASH),
    (EDGE_FIXTURE, EDGE_HASH),
])
def test_pinned_hashes(fixture, expected):
    ctx = load_synthetic(fixture)
    assert compute_context_hash(ctx) == expected
    assert ctx['hash'] == expected


@pytest.mark.parametrize('change', [
    {'document': 'anything'},
    {'document': None},
    {'hash': 'sha256:0'},
    {'knowledgeModel': None},  # a project's knowledge model is not hashed
])
def test_ignored_parts(change):
    assert compute_context_hash({**load_synthetic(PROJECT_FIXTURE), **change}) == PROJECT_HASH


@pytest.mark.parametrize('key', ['document', 'hash'])
def test_ignored_parts_may_be_missing(key):
    ctx = load_synthetic(PROJECT_FIXTURE)
    del ctx[key]
    assert compute_context_hash(ctx) == PROJECT_HASH


def test_knowledge_model_is_hashed_without_project():
    ctx = load_synthetic(KM_EDITOR_FIXTURE)
    assert ctx['project'] is None
    assert compute_context_hash({**ctx, 'knowledgeModel': None}) != KM_EDITOR_HASH


def test_reply_change_changes_hash():
    ctx = load_synthetic(PROJECT_FIXTURE)
    ctx['questionnaire']['replies'] = dict.fromkeys(ctx['questionnaire']['replies'])
    assert compute_context_hash(ctx) != PROJECT_HASH


def test_input_is_not_modified():
    ctx = load_synthetic(PROJECT_FIXTURE)
    compute_context_hash(ctx)
    assert ctx == load_synthetic(PROJECT_FIXTURE)


@pytest.mark.parametrize(('value', 'expected'), [
    ({'b': 1, 'a': [True, False, None]}, '{"a":[true,false,null],"b":1}'),
    # UTF-16 order puts the astral 😀 (a surrogate pair, 0xD83D…) before U+FF5E ～
    ({'～': 1, '😀': 2, 'é': 3, 'a': 4, 'A': 5}, '{"A":5,"a":4,"é":3,"😀":2,"～":1}'),
    ('"\\\b\f\n\r\t\x00\x1f\x7f €', '"\\"\\\\\\b\\f\\n\\r\\t\\u0000\\u001f\x7f €"'),
    ('\ud800', '"�"'),  # a lone surrogate, as the backend decodes it
    ([[], {}, [{}]], '[[],{},[{}]]'),
])
def test_canonical_json(value, expected):
    assert canonical_json(value) == expected.encode('utf-8')


@pytest.mark.parametrize(('value', 'expected'), [
    (0.0, '0'), (-0.0, '0'), (1.0, '1'), (-42.25, '-42.25'), (0.5, '0.5'), (123.456, '123.456'),
    (100.0, '100'), (1e20, '100000000000000000000'), (1e21, '1e+21'), (1.5e21, '1.5e+21'),
    (1e-6, '0.000001'), (1.5e-6, '0.0000015'), (1e-7, '1e-7'), (1.5e-7, '1.5e-7'),
    (2.0 ** 53, '9007199254740992'), (333333333.3333332, '333333333.3333332'),
    (5e-324, '5e-324'), (1.7976931348623157e308, '1.7976931348623157e+308'),
    (0.1 + 0.2, '0.30000000000000004'), (123e-20, '1.23e-18'),
])
def test_format_number(value, expected):
    assert format_number(value) == expected


def test_integers_are_doubles():
    assert canonical_json([2 ** 53 + 1, 10 ** 21]) == b'[9007199254740992,1e+21]'


@pytest.mark.parametrize('value', [math.inf, -math.inf, math.nan])
def test_non_finite_numbers_are_rejected(value):
    with pytest.raises(ValueError, match='not a JSON number'):
        format_number(value)


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_format_number_round_trips(value):
    text = format_number(value)
    assert float(text) == value or (value == 0 and text == '0')
    assert struct.pack('>d', float(text)) == struct.pack('>d', value) or value == 0
