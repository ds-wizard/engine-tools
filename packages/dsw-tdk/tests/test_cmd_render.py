# cspell:ignore Plán správy
import json
import pathlib

import click.testing

from dsw.tdk import main


def render(fixtures_path: pathlib.Path, tmp_path: pathlib.Path, *args: str):
    template_path = fixtures_path / 'test_render01'
    runner = click.testing.CliRunner()
    return runner.invoke(main, args=[
        'render', template_path.as_posix(),
        '--context', (template_path / 'context.json').as_posix(),
        *args,
    ])


def test_render_json(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    output = tmp_path / 'out.json'
    result = render(fixtures_path, tmp_path, '--format', 'JSON Data', '-o', output.as_posix())
    assert result.exit_code == 0, result.output
    assert 'rendered (application/json' in result.output
    assert json.loads(output.read_text(encoding='utf-8'))['document']['name'] == 'My Plan'


def test_render_adds_worker_defaults(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    output = tmp_path / 'out.json'
    result = render(fixtures_path, tmp_path, '--format', 'JSON Data', '-o', output.as_posix())
    assert result.exit_code == 0, result.output
    context = json.loads(output.read_text(encoding='utf-8'))
    assert context['config']['serviceName'] == 'Data Stewardship Wizard'
    assert context['config']['appTitle'] == 'My Wizard'  # kept from the context
    assert context['config']['primaryColor'] == '#0033aa'  # default for a missing one
    assert context['config']['logoUrl'] == 'https://wizard.example.org/assets/logo.svg'
    assert context['extras'] == {}


def test_render_fills_requested_extras(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    output = tmp_path / 'out.json'
    result = render(fixtures_path, tmp_path, '--format', 'Project JSON', '-o', output.as_posix())
    assert result.exit_code == 0, result.output
    assert 'Extra "project" is not in the context' in result.output
    assert 'Extra "submissions" is not in the context' in result.output
    context = json.loads(output.read_text(encoding='utf-8'))
    assert context['extras'] == {'project': None, 'submissions': []}


def test_render_html_by_uuid_with_translations_and_project_files(
        fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    template_path = fixtures_path / 'test_render01'
    output = tmp_path / 'out.html'
    result = render(
        fixtures_path, tmp_path,
        '--format', 'a9293d08-59a4-4e6b-ae62-7a6a570b031c',
        '--po', (template_path / 'cs.po').as_posix(),
        '--project-files', (template_path / 'project-files').as_posix(),
        '-o', output.as_posix(),
    )
    assert result.exit_code == 0, result.output
    content = output.read_text(encoding='utf-8')
    assert '<h1>Plán správy dat</h1>' in content
    assert '<p lang="cs">My Plan</p>' in content
    assert 'src="data:image/png;base64,' in content
    assert '<p>Attached notes</p>' in content


def test_render_html_without_translations_and_project_files(
        fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    output = tmp_path / 'out.html'
    result = render(fixtures_path, tmp_path, '--format', 'html document', '-o', output.as_posix())
    assert result.exit_code == 0, result.output
    content = output.read_text(encoding='utf-8')
    assert '<h1>Data Management Plan</h1>' in content
    assert '<p>no attachment</p>' in content
    assert 'WARNING' in result.output  # the project file cannot be fetched


def test_render_default_output_name(fixtures_path: pathlib.Path, tmp_path: pathlib.Path,
                                    monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = render(fixtures_path, tmp_path, '--format', 'JSON Data')
    assert result.exit_code == 0, result.output
    assert (tmp_path / 'render01.json').is_file()


def test_render_existing_output_without_force(fixtures_path: pathlib.Path,
                                              tmp_path: pathlib.Path):
    output = tmp_path / 'out.json'
    output.write_text('original', encoding='utf-8')
    result = render(fixtures_path, tmp_path, '--format', 'JSON Data', '-o', output.as_posix())
    assert result.exit_code == 1
    assert 'already exists' in result.output
    assert output.read_text(encoding='utf-8') == 'original'
    result = render(fixtures_path, tmp_path, '--format', 'JSON Data', '-o', output.as_posix(),
                    '--force')
    assert result.exit_code == 0, result.output


def test_render_requires_format_choice(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    result = render(fixtures_path, tmp_path)
    assert result.exit_code == 1
    assert 'choose one of: "JSON Data", "HTML Document", "Project JSON", "Excluded"' \
        in result.output


def test_render_unknown_format(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    result = render(fixtures_path, tmp_path, '--format', 'PDF')
    assert result.exit_code == 1
    assert 'Format "PDF" not found' in result.output


def test_render_uses_only_template_files(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    # src/excluded.html.j2 is not in _tdk.files, so the server would not have it either
    result = render(fixtures_path, tmp_path, '--format', 'Excluded',
                    '-o', (tmp_path / 'out.html').as_posix())
    assert result.exit_code == 1
    assert 'Failed to render the document' in result.output
    assert 'src/excluded.html.j2' in result.output


def test_render_context_defaults_override(fixtures_path: pathlib.Path, tmp_path: pathlib.Path,
                                          monkeypatch):
    monkeypatch.setenv('DOCUMENT_CONTEXT_SERVICE_URL', 'https://fair-wizard.com')
    monkeypatch.setenv('DOCUMENT_CONTEXT_SERVICE_NAME', 'From environment')
    output = tmp_path / 'out.json'
    result = render(fixtures_path, tmp_path, '--format', 'JSON Data', '-o', output.as_posix(),
                    '-D', 'serviceName=FAIR Wizard',
                    '--context-default', 'defaultPrimaryColor=#123456',
                    '-D', 'defaultAppTitle=FW')
    assert result.exit_code == 0, result.output
    config = json.loads(output.read_text(encoding='utf-8'))['config']
    assert config['serviceName'] == 'FAIR Wizard'  # option wins over the environment
    assert config['serviceUrl'] == 'https://fair-wizard.com'  # from the environment
    assert config['primaryColor'] == '#123456'  # missing in the context
    assert config['appTitle'] == 'My Wizard'  # the context wins over a default
    assert config['serviceNameShort'] == 'DSW'  # untouched default


def test_render_context_defaults_from_dot_env(fixtures_path: pathlib.Path,
                                              tmp_path: pathlib.Path, monkeypatch):
    monkeypatch.delenv('DOCUMENT_CONTEXT_SERVICE_NAME', raising=False)
    dot_env = tmp_path / '.env'
    dot_env.write_text('DOCUMENT_CONTEXT_SERVICE_NAME=Dot Env Wizard\n', encoding='utf-8')
    template_path = fixtures_path / 'test_render01'
    output = tmp_path / 'out.json'
    result = click.testing.CliRunner().invoke(main, args=[
        '--dot-env', dot_env.as_posix(), '--no-config',
        'render', template_path.as_posix(), '-c', (template_path / 'context.json').as_posix(),
        '-F', 'JSON Data', '-o', output.as_posix(),
    ])
    monkeypatch.delenv('DOCUMENT_CONTEXT_SERVICE_NAME', raising=False)  # set by load_dotenv
    assert result.exit_code == 0, result.output
    config = json.loads(output.read_text(encoding='utf-8'))['config']
    assert config['serviceName'] == 'Dot Env Wizard'


def test_render_context_defaults_invalid(fixtures_path: pathlib.Path, tmp_path: pathlib.Path):
    result = render(fixtures_path, tmp_path, '-F', 'JSON Data', '-D', 'serviceName')
    assert result.exit_code == 2
    assert '"serviceName" is not NAME=VALUE' in result.output
    result = render(fixtures_path, tmp_path, '-F', 'JSON Data', '-D', 'appTitle=X')
    assert result.exit_code == 2
    assert 'Unknown context default appTitle' in result.output
    assert 'defaultAppTitle' in result.output
