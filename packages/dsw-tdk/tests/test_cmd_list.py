import pytest
import click.testing

from dsw.tdk import main


@pytest.mark.vcr
def test_list_simple(dsw_env: dict):
    runner = click.testing.CliRunner()
    result = runner.invoke(main, args=['list'], env=dsw_env)
    assert result.exit_code == 0
    assert 'dsw:questionnaire-report:2.8.0' in result.output
    assert 'myorg:questionnaire-report:2.9.0' in result.output


@pytest.mark.vcr
def test_list_drafts_only(dsw_env: dict):
    runner = click.testing.CliRunner()
    result = runner.invoke(main, args=['list', '-d'], env=dsw_env)
    assert result.exit_code == 0
    assert 'dsw:questionnaire-report:2.8.0' not in result.output
    assert 'myorg:questionnaire-report:2.9.0' in result.output


@pytest.mark.vcr
def test_list_released_only(dsw_env: dict):
    runner = click.testing.CliRunner()
    result = runner.invoke(main, args=['list', '-r'], env=dsw_env)
    assert result.exit_code == 0
    assert 'dsw:questionnaire-report:2.8.0' in result.output
    assert 'myorg:questionnaire-report:2.9.0' not in result.output


@pytest.mark.vcr
def test_put_bad_token(dsw_api_url: str):
    env_vars = {
        'DSW_API_URL': dsw_api_url,
        'DSW_API_KEY': 'foo',
    }
    runner = click.testing.CliRunner()
    result = runner.invoke(main, args=['list'], env=env_vars)
    assert result.exit_code == 1


@pytest.mark.vcr
def test_put_bad_url(dsw_api_key: str):
    env_vars = {
        'DSW_API_URL': 'http://localhost:33333',
        'DSW_API_KEY': dsw_api_key,
    }
    runner = click.testing.CliRunner()
    result = runner.invoke(main, args=['list'], env=env_vars)
    assert result.exit_code == 1
