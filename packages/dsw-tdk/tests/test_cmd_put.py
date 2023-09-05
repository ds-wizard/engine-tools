import pathlib

import click.testing
import pytest

from dsw.tdk import main


@pytest.mark.vcr
def test_put_ok(fixtures_path: pathlib.Path, dsw_env: dict):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_example01'
    result = runner.invoke(main, args=['put', template_path.as_posix()], env=dsw_env)
    print(result.stdout)
    assert result.exit_code == 0


@pytest.mark.vcr
def test_put_faulty(fixtures_path: pathlib.Path, dsw_env: dict):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_faulty01'
    result = runner.invoke(main, args=['put', template_path.as_posix()], env=dsw_env)
    assert result.exit_code == 1


@pytest.mark.vcr
def test_put_published(fixtures_path: pathlib.Path, dsw_env: dict):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_example02'
    result = runner.invoke(main, args=['put', template_path.as_posix()], env=dsw_env)
    assert result.exit_code == 1


@pytest.mark.vcr
def test_put_bad_token(fixtures_path: pathlib.Path, dsw_api_url: str):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_example01'
    env_vars = {
        'DSW_API_URL': dsw_api_url,
        'DSW_API_KEY': 'foo',
    }
    result = runner.invoke(main, args=['put', template_path.as_posix()], env=env_vars)
    assert result.exit_code == 1


@pytest.mark.vcr
def test_put_bad_url(fixtures_path: pathlib.Path, dsw_api_key: str):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_example01'
    env_vars = {
        'DSW_API_URL': 'http://localhost:33333',
        'DSW_API_KEY': dsw_api_key,
    }
    result = runner.invoke(main, args=['put', template_path.as_posix()], env=env_vars)
    assert result.exit_code == 1
