import os
import pathlib

import pytest
import vcr

from dsw.tdk.config import CONFIG

TESTS_DIR = pathlib.Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / 'fixtures'
CASSETTES_DIR = TESTS_DIR / 'cassettes'
DUMMY_TOKEN = 'dummy-token'


FILTER_HEADERS = [('authorization', f'Bearer {DUMMY_TOKEN}')]
# the bundle download passes the token in the query (?Authorization=Bearer%20<token>)
FILTER_QUERY_PARAMETERS = [('Authorization', f'Bearer {DUMMY_TOKEN}'),
                           ('authorization', f'Bearer {DUMMY_TOKEN}')]


def _serializable_request(request):
    # multipart uploads (aiohttp.FormData) cannot be stored; requests are not matched on body
    if not isinstance(request.body, str | bytes | None):
        request.body = None
    return request


vcr.default_vcr = vcr.VCR(
    cassette_library_dir=CASSETTES_DIR,
    filter_headers=FILTER_HEADERS,
    filter_query_parameters=FILTER_QUERY_PARAMETERS,
    before_record_request=_serializable_request,
)
vcr.use_cassette = vcr.default_vcr.use_cassette


@pytest.fixture(scope='module')
def vcr_config():
    """The configuration pytest-recording records and replays with (not vcr.default_vcr)."""
    return {
        'filter_headers': FILTER_HEADERS,
        'filter_query_parameters': FILTER_QUERY_PARAMETERS,
        'before_record_request': _serializable_request,
    }


@pytest.fixture(scope='session')
def dsw_api_url():
    # the cassettes were recorded against a Wizard 5.0 instance (fair-wizard-e2e-tests, wizard-5.0,
    # single-workspace tenant); set DSW_API_URL and DSW_API_KEY to re-record them
    value = os.environ.get('DSW_API_URL', 'http://single.fair-wizard.localhost:3000/api')
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


@pytest.fixture(autouse=True)
def fresh_config():
    """CONFIG is a module-level singleton the commands fill in; every test starts from scratch."""
    CONFIG.__init__()
