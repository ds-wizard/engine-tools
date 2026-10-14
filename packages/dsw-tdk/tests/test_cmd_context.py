import json
import pathlib

import click.testing
import pytest

from dsw.tdk import main


# recorded against the single-workspace tenant of the 5.0 testbed (see conftest.py)
PROJECT = '6ada95e3-97aa-4674-996c-db68574119b8'
KM_EDITOR = '4dbec435-71de-4915-a185-f3c8842f66c1'


def get_context(tmp_path: pathlib.Path, dsw_env: dict, *args: str):
    runner = click.testing.CliRunner()
    output = tmp_path / 'context.json'
    result = runner.invoke(main, args=['--no-config', 'get-context', *args, '-o', str(output)],
                           env=dsw_env)
    return result, output


@pytest.mark.vcr
def test_get_context_of_project(tmp_path, dsw_env):
    result, output = get_context(tmp_path, dsw_env, '--project', PROJECT)
    assert result.exit_code == 0, result.output
    context = json.loads(output.read_text())
    assert context['project']['uuid'] == PROJECT
    assert context['document'] is None
    assert f'ETag {context["hash"]}' in result.output  # the ETag is the hash


@pytest.mark.vcr
def test_get_context_of_km_editor(tmp_path, dsw_env):
    result, output = get_context(tmp_path, dsw_env, '--km-editor', KM_EDITOR)
    assert result.exit_code == 0, result.output
    context = json.loads(output.read_text())
    assert context['project'] is None
    assert context['knowledgeModelEditor']['uuid'] == KM_EDITOR


@pytest.mark.vcr
def test_get_context_of_unknown_event(tmp_path, dsw_env):
    result, output = get_context(tmp_path, dsw_env, '--project', PROJECT,
                                 '--event', '99999999-9999-9999-9999-999999999999')
    assert result.exit_code == 1
    assert '404' in result.output
    assert not output.exists()


@pytest.mark.parametrize('args', [
    [],
    ['--project', PROJECT, '--km-editor', KM_EDITOR],
    ['--km-editor', KM_EDITOR, '--event', '99999999-9999-9999-9999-999999999999'],
])
def test_get_context_needs_one_source(tmp_path, dsw_env, args):
    result, _ = get_context(tmp_path, dsw_env, *args)
    assert result.exit_code == 2


def test_get_context_keeps_existing_file(tmp_path, dsw_env):
    (tmp_path / 'context.json').write_text('{}')
    result, output = get_context(tmp_path, dsw_env, '--project', PROJECT)
    assert result.exit_code == 1
    assert output.read_text() == '{}'


@pytest.mark.vcr('test_get_context_of_project.yaml')
def test_validate_context(tmp_path, dsw_env):
    _, output = get_context(tmp_path, dsw_env, '--project', PROJECT)
    runner = click.testing.CliRunner()

    result = runner.invoke(main, args=['validate-context', str(output)])
    assert result.exit_code == 0, result.output
    assert 'valid' in result.output

    context = json.loads(output.read_text())
    context['questionnaire']['phaseUuid'] = '99999999-9999-9999-9999-999999999999'
    output.write_text(json.dumps(context))
    result = runner.invoke(main, args=['validate-context', str(output)])
    assert result.exit_code == 1
    assert 'ERROR' in result.output and '/questionnaire/phaseUuid' in result.output
    assert '/hash' in result.output  # edited by hand

    result = runner.invoke(main, args=['validate-context', str(output), '--fix-hash'])
    assert result.exit_code == 1  # the phase is still wrong
    assert 'hash rewritten' in result.output
    assert '/hash' not in result.output.split('hash rewritten')[1]
