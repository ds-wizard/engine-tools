import gzip
import json
import pathlib

import pytest


FIXTURES_DIR = pathlib.Path(__file__).parent / 'fixtures'
REFERENCE_DIR = FIXTURES_DIR / 'reference'
SYNTHETIC_DIR = FIXTURES_DIR / 'synthetic'

REFERENCE_BUNDLES = sorted(path.name for path in REFERENCE_DIR.glob('*.km.gz'))


def load_reference(name: str):
    with gzip.open(REFERENCE_DIR / name, 'rt', encoding='utf-8') as file:
        return json.load(file)


def load_synthetic(name: str):
    return json.loads((SYNTHETIC_DIR / name).read_text(encoding='utf-8'))


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    return FIXTURES_DIR


def assert_same_json(expected, actual, path='$'):
    """Compare JSON data, reporting the first differing path (dict key order is ignored)."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        assert set(expected) == set(actual), (
            f'{path}: keys differ, missing {sorted(set(expected) - set(actual))}, '
            f'extra {sorted(set(actual) - set(expected))}'
        )
        for key, value in expected.items():
            assert_same_json(value, actual[key], f'{path}.{key}')
    elif isinstance(expected, list) and isinstance(actual, list):
        assert len(expected) == len(actual), f'{path}: length {len(expected)} != {len(actual)}'
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            assert_same_json(left, right, f'{path}[{index}]')
    else:
        assert expected == actual, f'{path}: {expected!r} != {actual!r}'
