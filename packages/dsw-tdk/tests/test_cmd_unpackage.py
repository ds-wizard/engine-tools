import pathlib

import click.testing

from dsw.tdk import main


def test_unpackage_ok(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    zip_file = fixtures_path / 'my-template.zip'
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        template_dir = root_dir / 'extracted'

        result = runner.invoke(main, args=['unpackage', zip_file.as_posix(), '-o', template_dir.as_posix()])
        assert result.exit_code == 0
        assert (template_dir / 'template.json').exists()
        assert (template_dir / 'README.md').exists()


def test_unpackage_without_force(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    zip_file = fixtures_path / 'my-template.zip'
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        template_dir = root_dir / 'extracted'
        template_dir.mkdir()

        result = runner.invoke(main, args=['unpackage', zip_file.as_posix(), '-o', template_dir.as_posix()])
        assert result.exit_code == 1
        assert not (template_dir / 'template.json').exists()
        assert not (template_dir / 'README.md').exists()


def test_unpackage_with_force(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    zip_file = fixtures_path / 'my-template.zip'
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        template_dir = root_dir / 'extracted'
        template_dir.mkdir()

        result = runner.invoke(main, args=['unpackage', zip_file.as_posix(), '-f', '-o', template_dir.as_posix()])
        assert result.exit_code == 0
        assert (template_dir / 'template.json').exists()
        assert (template_dir / 'README.md').exists()


def test_unpackage_with_faulty(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    zip_file = fixtures_path / 'my-template-faulty.zip'
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        template_dir = root_dir / 'extracted'

        result = runner.invoke(main, args=['unpackage', zip_file.as_posix(), '-o', template_dir.as_posix()])
        assert result.exit_code == 1
