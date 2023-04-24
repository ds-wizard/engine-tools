import pathlib

import click.testing

from dsw.tdk import main


def test_new_no_dir(tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    inputs = ['Test template', 'dsw', 'test-template', '0.1.0', 'some description', 'CC0',
              'y', 'HTML', 'html', 'text/html', 'src/template.html.j2', 'n']
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        result = runner.invoke(main, args=['new'], input='\n'.join(inputs))
        assert not result.exception
        assert result.exit_code == 0
        paths = frozenset(map(lambda x: str(x.relative_to(isolated_dir).as_posix()), tmp_path.rglob('*')))
        assert 'dsw_test-template_0.1.0/template.json' in paths
        assert 'dsw_test-template_0.1.0/README.md' in paths
        assert 'dsw_test-template_0.1.0/src' in paths
        assert 'dsw_test-template_0.1.0/src/template.html.j2' in paths


def test_new_dir(tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    inputs = ['Test template', 'dsw', 'test-template', '0.1.0', 'some description', 'CC0',
              'y', 'HTML', 'html', 'text/html', 'src/template.html.j2', 'n']
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        result = runner.invoke(main, args=['new', 'my-template'], input='\n'.join(inputs))
        assert not result.exception
        assert result.exit_code == 0
        paths = frozenset(map(lambda x: str(x.relative_to(isolated_dir).as_posix()), tmp_path.rglob('*')))
        assert 'my-template/template.json' in paths
        assert 'my-template/README.md' in paths
        assert 'my-template/src' in paths
        assert 'my-template/src/template.html.j2' in paths


def test_new_without_force(tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    inputs = ['Test template', 'dsw', 'test-template', '0.1.0', 'some description', 'CC0',
              'y', 'HTML', 'html', 'text/html', 'src/template.html.j2', 'n']
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        template_json = root_dir / 'template.json'
        template_json.write_text('foo', encoding='utf-8')

        result = runner.invoke(main, args=['new', '.'], input='\n'.join(inputs))
        assert not result.exception
        assert result.exit_code == 0
        paths = frozenset(map(lambda x: str(x.relative_to(isolated_dir).as_posix()), tmp_path.rglob('*')))
        assert 'template.json' in paths
        assert 'README.md' in paths
        assert 'src' in paths
        assert 'src/template.html.j2' in paths
        assert template_json.read_text(encoding='utf-8') == 'foo'


def test_new_with_force(tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    inputs = ['Test template', 'dsw', 'test-template', '0.1.0', 'some description', 'CC0',
              'y', 'HTML', 'html', 'text/html', 'src/template.html.j2', 'n']
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        template_json = root_dir / 'template.json'
        template_json.write_text('foo', encoding='utf-8')

        result = runner.invoke(main, args=['new', '--force', '.'], input='\n'.join(inputs))
        assert not result.exception
        assert result.exit_code == 0
        paths = frozenset(map(lambda x: str(x.relative_to(isolated_dir).as_posix()), tmp_path.rglob('*')))
        assert 'template.json' in paths
        assert 'README.md' in paths
        assert 'src' in paths
        assert 'src/template.html.j2' in paths
        assert template_json.read_text(encoding='utf-8') != 'foo'
