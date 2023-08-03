import pathlib

import pytest
import click.testing

from dsw.tdk import main


@pytest.mark.vcr
def test_get_released(tmp_path: pathlib.Path, dsw_env: dict):
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        template_dir = root_dir / 'dsw_questionnaire-report_2.8.0'
        result = runner.invoke(main, args=['get', 'dsw:questionnaire-report:2.8.0'], env=dsw_env)
        assert result.exit_code == 0
        assert (template_dir / 'template.json').exists()
        assert (template_dir / 'README.md').exists()


@pytest.mark.vcr
def test_get_draft(tmp_path: pathlib.Path, dsw_env: dict):
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        template_dir = root_dir / 'myorg_questionnaire-report_2.9.0'
        result = runner.invoke(main, args=['get', 'myorg:questionnaire-report:2.9.0'], env=dsw_env)
        assert result.exit_code == 0
        assert (template_dir / 'template.json').exists()
        assert (template_dir / 'README.md').exists()


@pytest.mark.vcr
def test_get_released_custom_dir(tmp_path: pathlib.Path, dsw_env: dict):
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        template_dir = root_dir / 'foo'
        result = runner.invoke(main, args=['get', 'dsw:questionnaire-report:2.8.0', 'foo'], env=dsw_env)
        assert result.exit_code == 0
        assert (template_dir / 'template.json').exists()
        assert (template_dir / 'README.md').exists()


@pytest.mark.vcr
def test_get_draft_custom_dir(tmp_path: pathlib.Path, dsw_env: dict):
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        template_dir = root_dir / 'foo'
        result = runner.invoke(main, args=['get', 'myorg:questionnaire-report:2.9.0', 'foo'], env=dsw_env)
        assert result.exit_code == 0
        assert (template_dir / 'template.json').exists()
        assert (template_dir / 'README.md').exists()


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
