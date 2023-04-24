import pytest

from click.testing import CliRunner

from dsw.tdk import main


def test_base_version_works():
    runner = CliRunner()
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0


def test_base_help_works():
    runner = CliRunner()
    result = runner.invoke(main, ['--help'])
    assert result.exit_code == 0


@pytest.mark.parametrize(
    'cmd', ['new', 'list', 'get', 'put', 'verify', 'package', 'unpackage']
)
def test_command_help_works(cmd):
    runner = CliRunner()
    result = runner.invoke(main, [cmd, '--help'])
    assert result.exit_code == 0
