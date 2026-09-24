import json
import pathlib
import zipfile

import click.testing

from dsw.models.document_template.metadata import DocumentTemplateBundle
from dsw.models.strictness import load
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


def _packaged_descriptor(fixtures_path: pathlib.Path, tmp_path: pathlib.Path,
                         fixture: str) -> tuple[int, str, dict]:
    runner = click.testing.CliRunner()
    template_path = fixtures_path / fixture
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        zip_file = pathlib.Path(isolated_dir) / 'my-template.zip'
        result = runner.invoke(main, args=['package', template_path.as_posix(),
                                           '-o', 'my-template.zip'])
        if not zip_file.exists():
            return result.exit_code, result.output, {}
        with zipfile.ZipFile(zip_file) as pkg:
            descriptor = json.loads(pkg.read('template/template.json'))
        return result.exit_code, result.output, descriptor


def test_package_matches_document_template_bundle(fixtures_path, tmp_path):
    """What `package` writes is exactly the bundle shape shared via dsw-models."""
    exit_code, _, descriptor = _packaged_descriptor(fixtures_path, tmp_path, 'test_example01')
    assert exit_code == 0
    bundle = load(DocumentTemplateBundle, descriptor)
    assert bundle.coordinate == descriptor['id']
    assert bundle.metamodel_version == '17.1'
    assert [f.file_name for f in bundle.files] == [f['fileName'] for f in descriptor['files']]


def test_package_keeps_allowed_package_options(fixtures_path, tmp_path):
    """`options` is optional on a package pattern: present when set, absent otherwise."""
    _, _, descriptor = _packaged_descriptor(fixtures_path, tmp_path, 'test_example01')
    for pattern in descriptor['allowedPackages']:
        assert set(pattern) >= {'orgId', 'kmId', 'minVersion', 'maxVersion'}
        assert 'options' not in pattern or isinstance(pattern['options'], dict)


def test_package_of_invalid_template_still_succeeds(fixtures_path, tmp_path):
    """`package` never ran TemplateValidator, so bundle mismatches warn rather than fail."""
    exit_code, output, descriptor = _packaged_descriptor(fixtures_path, tmp_path, 'test_faulty03')
    assert exit_code == 0
    assert 'does not match the document template bundle' in output
    assert descriptor['name'] is None  # written as assembled, exactly as before
