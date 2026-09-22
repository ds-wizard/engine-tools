import io
import pathlib

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from dsw.config import InvalidConfigurationError, appconfig, read_config


SESSION_KEY = ('fw-staging-lambda', 'Default', 'application-yml')

START = {
    'ApplicationIdentifier': 'fw-staging-lambda',
    'EnvironmentIdentifier': 'Default',
    'ConfigurationProfileIdentifier': 'application-yml',
}


def _body(content: bytes) -> StreamingBody:
    return StreamingBody(io.BytesIO(content), len(content))


def _latest(content: bytes, next_token: str, interval: int = 60) -> dict:
    return {
        'Configuration': _body(content),
        'NextPollConfigurationToken': next_token,
        'NextPollIntervalInSeconds': interval,
    }


@pytest.fixture
def stubber(monkeypatch):
    client = boto3.client(
        'appconfigdata',
        region_name='eu-central-1',
        aws_access_key_id='test',
        aws_secret_access_key='test',  # noqa: S106
    )
    monkeypatch.setattr(appconfig, '_client', client)
    monkeypatch.setattr(appconfig, '_sessions', {})
    for var in (appconfig.VAR_APPLICATION, appconfig.VAR_ENVIRONMENT, appconfig.VAR_PROFILE):
        monkeypatch.delenv(var, raising=False)
    with Stubber(client) as s:
        yield s
        s.assert_no_pending_responses()


@pytest.fixture
def config_file(tmp_path) -> pathlib.Path:
    path = tmp_path / 'application.yml'
    path.write_text('general:\n  environment: local\n', encoding='utf-8')
    return path


def test_profile_for():
    assert appconfig.profile_for(pathlib.Path('/var/task/application.yml')) == 'application-yml'


def test_reads_local_file_without_app_config(stubber, config_file):
    assert read_config(config_file) == 'general:\n  environment: local\n'


def test_reads_from_app_config(stubber, config_file, monkeypatch):
    monkeypatch.setenv(appconfig.VAR_APPLICATION, 'fw-staging-lambda')
    stubber.add_response('start_configuration_session', {'InitialConfigurationToken': 't0'}, START)
    stubber.add_response('get_latest_configuration', _latest(b'remote: 1\n', 't1'), {'ConfigurationToken': 't0'})

    assert read_config(config_file) == 'remote: 1\n'


def test_overrides_environment_and_profile(stubber, config_file, monkeypatch):
    monkeypatch.setenv(appconfig.VAR_APPLICATION, 'fw-staging-lambda')
    monkeypatch.setenv(appconfig.VAR_ENVIRONMENT, 'Other')
    monkeypatch.setenv(appconfig.VAR_PROFILE, 'mailer-wizard')
    stubber.add_response(
        'start_configuration_session',
        {'InitialConfigurationToken': 't0'},
        {**START, 'EnvironmentIdentifier': 'Other', 'ConfigurationProfileIdentifier': 'mailer-wizard'},
    )
    stubber.add_response('get_latest_configuration', _latest(b'remote: 1\n', 't1'), {'ConfigurationToken': 't0'})

    assert read_config(config_file) == 'remote: 1\n'


def test_warm_call_within_interval_uses_cache(stubber, config_file, monkeypatch):
    monkeypatch.setenv(appconfig.VAR_APPLICATION, 'fw-staging-lambda')
    stubber.add_response('start_configuration_session', {'InitialConfigurationToken': 't0'}, START)
    stubber.add_response('get_latest_configuration', _latest(b'remote: 1\n', 't1'), {'ConfigurationToken': 't0'})

    read_config(config_file)
    assert read_config(config_file) == 'remote: 1\n'


def test_poll_after_interval_keeps_unchanged_and_picks_up_changes(stubber, config_file, monkeypatch):
    monkeypatch.setenv(appconfig.VAR_APPLICATION, 'fw-staging-lambda')
    stubber.add_response('start_configuration_session', {'InitialConfigurationToken': 't0'}, START)
    stubber.add_response('get_latest_configuration', _latest(b'remote: 1\n', 't1', 0), {'ConfigurationToken': 't0'})
    stubber.add_response('get_latest_configuration', _latest(b'', 't2', 0), {'ConfigurationToken': 't1'})
    stubber.add_response('get_latest_configuration', _latest(b'remote: 2\n', 't3', 0), {'ConfigurationToken': 't2'})

    assert read_config(config_file) == 'remote: 1\n'
    assert read_config(config_file) == 'remote: 1\n'
    assert read_config(config_file) == 'remote: 2\n'


def test_failed_poll_keeps_cached_config(stubber, config_file, monkeypatch):
    monkeypatch.setenv(appconfig.VAR_APPLICATION, 'fw-staging-lambda')
    stubber.add_response('start_configuration_session', {'InitialConfigurationToken': 't0'}, START)
    stubber.add_response('get_latest_configuration', _latest(b'remote: 1\n', 't1', 0), {'ConfigurationToken': 't0'})
    stubber.add_client_error('get_latest_configuration', 'InternalServerException')

    assert read_config(config_file) == 'remote: 1\n'
    assert read_config(config_file) == 'remote: 1\n'
    # The failed poll spent the token, so it is dropped rather than retried
    assert appconfig._sessions[SESSION_KEY].token is None


def test_expired_token_starts_a_new_session(stubber, config_file, monkeypatch):
    monkeypatch.setenv(appconfig.VAR_APPLICATION, 'fw-staging-lambda')
    stubber.add_response('start_configuration_session', {'InitialConfigurationToken': 't0'}, START)
    stubber.add_response('get_latest_configuration', _latest(b'remote: 1\n', 't1', 0), {'ConfigurationToken': 't0'})
    # A token is valid for 24 hours and only once; an idle warm Lambda hits this
    stubber.add_client_error('get_latest_configuration', 'BadRequestException')
    stubber.add_response('start_configuration_session', {'InitialConfigurationToken': 't2'}, START)
    stubber.add_response('get_latest_configuration', _latest(b'remote: 2\n', 't3', 0), {'ConfigurationToken': 't2'})

    assert read_config(config_file) == 'remote: 1\n'
    assert read_config(config_file) == 'remote: 1\n'
    assert read_config(config_file) == 'remote: 2\n'


def test_empty_initial_config_is_an_error(stubber, config_file, monkeypatch):
    monkeypatch.setenv(appconfig.VAR_APPLICATION, 'fw-staging-lambda')
    stubber.add_response('start_configuration_session', {'InitialConfigurationToken': 't0'}, START)
    stubber.add_response('get_latest_configuration', _latest(b'', 't1'), {'ConfigurationToken': 't0'})

    with pytest.raises(InvalidConfigurationError):
        read_config(config_file)
