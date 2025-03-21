import pathlib

import click.testing

from dsw.tdk import main


def test_verify_ok(fixtures_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_example01'
    result = runner.invoke(main, args=['verify', template_path.as_posix()])
    assert result.exit_code == 0
    assert 'The template is valid!' in result.output
    assert 'Test template 01' in result.output


def test_verify_missing_attrs(fixtures_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_faulty01'
    result = runner.invoke(main, args=['verify', template_path.as_posix()])
    assert result.exit_code == 1
    assert 'Could not load local template' in result.output
    assert 'Unable to load template using' in result.output


def test_verify_no_readme(fixtures_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_faulty02'
    result = runner.invoke(main, args=['verify', template_path.as_posix()])
    assert result.exit_code == 1
    assert 'Could not load local template' in result.output
    assert 'README file "README.md" cannot be loaded' in result.output


def test_verify_invalid(fixtures_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_faulty03'
    result = runner.invoke(main, args=['verify', template_path.as_posix()])
    assert result.exit_code == 0
    assert 'The template is invalid!' in result.output
    assert 'template_id: Template ID may contain only letters, numbers,' in result.output
    assert 'organization_id: Organization ID may contain only letters, numbers,' in result.output
    assert 'version: Version must be in semver format' in result.output
    assert 'name: Missing but it is required' in result.output
    assert 'description: Missing but it is required' in result.output
    assert 'metamodel_version: It must be positive integer' in result.output
