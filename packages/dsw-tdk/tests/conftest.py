import os
import pathlib

import pytest
import vcr

TESTS_DIR = pathlib.Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / 'fixtures'
CASSETTES_DIR = TESTS_DIR / 'cassettes'
DUMMY_TOKEN = 'dummy-token'


vcr.default_vcr = vcr.VCR(
    cassette_library_dir=CASSETTES_DIR,
    filter_headers=[('authorization', f'Bearer {DUMMY_TOKEN}')],
    filter_query_parameters=[('authorization', DUMMY_TOKEN)],
)
vcr.use_cassette = vcr.default_vcr.use_cassette


@pytest.fixture(scope='session')
def dsw_api_url():
    value = os.environ.get('DSW_API_URL', 'http://localhost:3000')
    return value


@pytest.fixture(scope='session')
def dsw_api_key():
    value = os.environ.get('DSW_API_KEY', DUMMY_TOKEN)
    return value


@pytest.fixture(scope='session')
def dsw_env(dsw_api_url: str, dsw_api_key: str):
    return {
        'DSW_API_URL': dsw_api_url,
        'DSW_API_KEY': dsw_api_key,
    }


@pytest.fixture(scope='session')
def fixtures_path():
    return FIXTURES_DIR
