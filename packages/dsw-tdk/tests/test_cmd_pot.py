import pathlib
import shutil

import click.testing

from dsw.tdk import main


def test_pot_ok(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_example01'
    output = tmp_path / 'template.pot'
    result = runner.invoke(main, args=['pot', template_path.as_posix(),
                                       '-o', output.as_posix()])
    assert result.exit_code == 0
    assert 'created' in result.output

    content = output.read_text(encoding='utf-8')
    assert 'Project-Id-Version: test:example01:1.0.0 1.0.0' in content
    assert 'Language: en' in content
    assert 'Plural-Forms: nplurals=2; plural=(n != 1);' in content
    assert 'charset=utf-8' in content
    assert '#. main heading of the example' in content
    assert '#: src/template.json.j2:9' in content
    assert 'msgid "This is example"' in content
    assert 'msgid "Hello"' in content


def test_pot_existing_without_force(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_example01'
    output = tmp_path / 'template.pot'
    output.write_text('original', encoding='utf-8')
    result = runner.invoke(main, args=['pot', template_path.as_posix(),
                                       '-o', output.as_posix()])
    assert result.exit_code == 1
    assert 'Failed to create the POT file' in result.output
    assert output.read_text(encoding='utf-8') == 'original'


def test_pot_existing_with_force(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = fixtures_path / 'test_example01'
    output = tmp_path / 'template.pot'
    output.write_text('original', encoding='utf-8')
    result = runner.invoke(main, args=['pot', template_path.as_posix(),
                                       '-o', output.as_posix(), '--force'])
    assert result.exit_code == 0
    assert 'msgid "This is example"' in output.read_text(encoding='utf-8')


def test_pot_skips_unparseable_file(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    template_path = tmp_path / 'project'
    shutil.copytree(fixtures_path / 'test_example01', template_path)
    (template_path / 'src' / 'broken.j2').write_text('{% if %}', encoding='utf-8')
    output = tmp_path / 'template.pot'

    result = runner.invoke(main, args=['pot', template_path.as_posix(),
                                       '-o', output.as_posix()])
    assert result.exit_code == 0
    assert 'Skipped file src/broken.j2 that could not be parsed' in result.output

    content = output.read_text(encoding='utf-8')
    assert 'Skipped files that could not be parsed: src/broken.j2' in content
    assert 'msgid "This is example"' in content
