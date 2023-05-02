import pathlib

import click.testing

from dsw.tdk import main


def test_package_ok(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_example01'
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        zip_file = root_dir / 'my-template.zip'

        result = runner.invoke(main, args=['package', template_path.as_posix(), '-o', 'my-template.zip'])
        assert result.exit_code == 0
        assert zip_file.exists() and zip_file.is_file()


def test_package_without_force(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_example01'
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        zip_file = root_dir / 'my-template.zip'
        zip_file.write_bytes(b'foo')

        result = runner.invoke(main, args=['package', template_path.as_posix(), '-o', 'my-template.zip'])
        assert result.exit_code == 1
        assert zip_file.exists() and zip_file.is_file()
        assert zip_file.read_bytes() == b'foo'


def test_package_with_force(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_example01'
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        zip_file = root_dir / 'my-template.zip'
        zip_file.write_bytes(b'foo')

        result = runner.invoke(main, args=['package', template_path.as_posix(), '-o', 'my-template.zip', '-f'])
        assert result.exit_code == 0
        assert zip_file.exists() and zip_file.is_file()
        assert zip_file.read_bytes() != b'foo'


def test_package_faulty01(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_faulty01'
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        zip_file = root_dir / 'my-template.zip'

        result = runner.invoke(main, args=['package', template_path.as_posix(), '-o', 'my-template.zip'])
        assert result.exit_code == 1
        assert not zip_file.exists()
