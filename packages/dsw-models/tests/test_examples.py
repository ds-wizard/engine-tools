import json
import pathlib
import subprocess
import sys

import pytest

EXAMPLES = pathlib.Path(__file__).parent.parent / 'examples'
SMP_BUNDLE = pathlib.Path(__file__).parent / 'fixtures' / 'reference' / 'dsw_smp_1.2.4.km.gz'


def run(script: str, *args: str | pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(EXAMPLES / script), *map(str, args)],
                          capture_output=True, text=True, check=False)


def test_create_and_validate(tmp_path):
    output = tmp_path / 'example.km'
    created = run('create_km.py', '-o', output)
    assert created.returncode == 0, created.stderr
    validated = run('validate_km.py', output)
    assert validated.returncode == 0, validated.stdout + validated.stderr
    assert '0 error(s), 0 warning(s), 0 info(s)' in validated.stdout


def test_validate_reference_bundle():
    result = run('validate_km.py', SMP_BUNDLE)
    assert result.returncode == 0, result.stderr
    assert 'dsw:smp:1.2.4: 7 package(s)' in result.stdout


def test_diff_built_in_versions():
    result = run('diff_kms.py')
    assert result.returncode == 0, result.stderr
    for event_type in ('AddAnswerEvent', 'DeleteAnswerEvent', 'EditKnowledgeModelEvent',
                       'EditChapterEvent', 'EditQuestionEvent'):
        assert event_type in result.stdout
    assert '5 event(s)' in result.stdout


def test_diff_bundle_versions():
    result = run('diff_kms.py', SMP_BUNDLE, '--from', 'dsw:smp:1.2.3', '--json')
    assert result.returncode == 0, result.stderr
    events = json.loads(result.stdout)
    assert [event['content']['eventType'] for event in events] == ['EditQuestionEvent']


@pytest.mark.parametrize('kind', ['km-bundle', 'km-tree', 'template-json', 'document-context'])
def test_generate_schema(kind):
    result = run('generate_schema.py', kind)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['$schema'] == 'https://json-schema.org/draft/2020-12/schema'
