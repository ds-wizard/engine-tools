import pathlib

import click.testing

from dsw.tdk import main


def test_creates_dot_env(tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    inputs = ['https://example.com', 'mySecretKey']
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)

        result = runner.invoke(main, args=['dot-env', root_dir.as_posix()], input='\n'.join(inputs))
        assert not result.exception
        assert result.exit_code == 0
        paths = frozenset(map(lambda x: str(x.relative_to(isolated_dir).as_posix()), tmp_path.rglob('*')))
        assert '.env' in paths


def test_dot_env_contents(tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    inputs = ['https://example.com', 'mySecretKey']
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        dot_env = root_dir / '.env'

        result = runner.invoke(main, args=['dot-env', root_dir.as_posix()], input='\n'.join(inputs))
        assert not result.exception
        assert result.exit_code == 0
        paths = frozenset(map(lambda x: str(x.relative_to(isolated_dir).as_posix()), tmp_path.rglob('*')))
        assert '.env' in paths
        contents = dot_env.read_text(encoding='utf-8')
        assert 'DSW_API_URL=https://example.com' in contents
        assert 'DSW_API_KEY=mySecretKey' in contents


def test_dot_env_no_force(tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    inputs = ['https://example.com', 'mySecretKey']
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        dot_env = root_dir / '.env'
        dot_env.write_text('test')

        result = runner.invoke(main, args=['dot-env', root_dir.as_posix()], input='\n'.join(inputs))
        assert result.exception
        assert result.exit_code == 1

        contents = dot_env.read_text(encoding='utf-8')
        assert 'test' in contents


def test_dot_env_overwrites(tmp_path: pathlib.Path):
    runner = click.testing.CliRunner()
    inputs = ['https://example.com', 'mySecretKey']
    with runner.isolated_filesystem(temp_dir=tmp_path) as isolated_dir:
        root_dir = pathlib.Path(isolated_dir)
        dot_env = root_dir / '.env'
        dot_env.write_text('test')

        result = runner.invoke(main, args=['dot-env', root_dir.as_posix(), '--force'], input='\n'.join(inputs))
        print(result.stdout)
        assert not result.exception
        assert result.exit_code == 0
        paths = frozenset(map(lambda x: str(x.relative_to(isolated_dir).as_posix()), tmp_path.rglob('*')))
        assert '.env' in paths
        contents = dot_env.read_text(encoding='utf-8')
        assert 'DSW_API_URL=https://example.com' in contents
        assert 'DSW_API_KEY=mySecretKey' in contents
