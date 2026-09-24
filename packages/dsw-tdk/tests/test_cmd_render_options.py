import importlib.util
import pathlib

import click.testing

from dsw.tdk import main


def render(fixtures_path: pathlib.Path, output: pathlib.Path, *args: str):
    template_path = fixtures_path / 'test_render02'
    return click.testing.CliRunner().invoke(main, args=[
        '--no-config', '--no-dot-env',
        'render', template_path.as_posix(),
        '--context', (template_path / 'context.json').as_posix(),
        '-o', output.as_posix(), '--force',
        *args,
    ])


def test_no_globals_by_default(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    output = tmp_path / 'out.txt'
    result = render(fixtures_path, output, '-F', 'Globals')
    assert result.exit_code == 0, result.output
    assert output.read_text(encoding='utf-8').strip() == 'no secrets|no requests'


def test_secrets_and_requests(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    output = tmp_path / 'out.txt'
    result = render(fixtures_path, output, '-F', 'Globals',
                    '--secret', 'token=abc=123', '--allow-requests')
    if importlib.util.find_spec('requests') is None:  # without dsw-tdk[all]
        assert result.exit_code == 1
        assert 'install dsw-templating[http]' in result.output
        return
    assert result.exit_code == 0, result.output
    assert output.read_text(encoding='utf-8').strip() == 'abc=123|requests'


def test_secret_without_requests(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    output = tmp_path / 'out.txt'
    result = render(fixtures_path, output, '-F', 'Globals', '-s', 'token=x')
    assert result.exit_code == 0, result.output
    assert output.read_text(encoding='utf-8').strip() == 'x|no requests'


def test_invalid_secret(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    result = render(fixtures_path, tmp_path / 'out.txt', '-F', 'Globals', '-s', 'token')
    assert result.exit_code == 2
    assert '"token" is not NAME=VALUE' in result.output


def test_pandoc_needs_templates_and_filters(fixtures_path: pathlib.Path, tmp_path: pathlib.Path,
                                            monkeypatch):
    monkeypatch.delenv('PANDOC_TEMPLATES', raising=False)
    monkeypatch.delenv('PANDOC_FILTERS', raising=False)
    result = render(fixtures_path, tmp_path / 'out.docx', '-F', 'Word')
    assert result.exit_code == 1
    assert 'Pandoc filter "mine.lua" not found' in result.output


def test_pandoc_with_templates_and_filters(fixtures_path: pathlib.Path, tmp_path: pathlib.Path,
                                           monkeypatch):
    monkeypatch.setenv('PATH', str(tmp_path))  # no pandoc, whatever is installed
    template_path = fixtures_path / 'test_render02'
    monkeypatch.setenv('PANDOC_TEMPLATES', (template_path / 'pandoc-templates').as_posix())
    result = render(fixtures_path, tmp_path / 'out.docx', '-F', 'Word',
                    '--pandoc-filters', (template_path / 'pandoc-filters').as_posix())
    assert result.exit_code == 1
    # templates and filters were found, it got as far as running pandoc
    assert 'Executable "pandoc" not found, is it installed?' in result.output


def test_pandoc_template_missing(fixtures_path: pathlib.Path, tmp_path: pathlib.Path,
                                 monkeypatch):
    template_path = fixtures_path / 'test_render02'
    monkeypatch.delenv('PANDOC_TEMPLATES', raising=False)
    result = render(fixtures_path, tmp_path / 'out.docx', '-F', 'Word',
                    '--pandoc-filters', (template_path / 'pandoc-filters').as_posix())
    assert result.exit_code == 1
    assert 'Pandoc template "custom.docx" not found' in result.output
