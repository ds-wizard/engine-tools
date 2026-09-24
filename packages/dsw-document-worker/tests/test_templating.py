"""How the worker maps its configuration and errors onto dsw-templating."""
import pathlib
import types

import pytest

from dsw.document_worker.config import (
    CommandConfig,
    SecurityConfig,
    TemplateConfig,
    TemplateRequestsConfig,
    TemplatesConfig,
)
from dsw.document_worker.exceptions import JobError, create_job_error
from dsw.document_worker.templates.templates import render_settings
from dsw.templating import FormatStepError, TemplateTriggeredError
from dsw.templating.conversions import Pandoc
from dsw.templating.settings import bundled_pandoc_filters


def make_config(*templates: TemplateConfig):
    return types.SimpleNamespace(
        templates=TemplatesConfig(templates=list(templates)),
        security=SecurityConfig(
            allow_external_resources=False,
            allow_private_network=True,
            allowed_hosts=['example.org'],
            allowed_paths=['/data'],
            max_redirects=5,
        ),
        pandoc=CommandConfig(executable='pandoc', args='--standalone --wrap=none', timeout=30),
    )


def test_render_settings_from_config():
    template_cfg = TemplateConfig(
        ids=['org:tid'],
        requests=TemplateRequestsConfig(enabled=True, limit=7, timeout=2),
        secrets={'token': 'x'},
        send_sentry=False,
    )
    settings = render_settings(make_config(template_cfg), 'org:tid:1.0.0')
    assert settings.security.allow_external_resources is False
    assert settings.security.allow_private_network is True
    assert settings.security.allowed_hosts == ['example.org']
    assert settings.security.allowed_paths == ['/data']
    assert settings.security.max_redirects == 5
    assert settings.pandoc.command == ['pandoc', '--standalone', '--wrap=none']
    assert settings.pandoc.timeout == 30
    assert settings.template is not None
    assert settings.template.secrets == {'token': 'x'}
    assert settings.template.requests.enabled is True
    assert settings.template.requests.limit == 7
    assert settings.template.requests.timeout == 2


def test_render_settings_without_template_config():
    assert render_settings(make_config(), 'org:tid:1.0.0').template is None


def test_lua_filters_resolve_from_the_package(monkeypatch, tmp_path: pathlib.Path):
    monkeypatch.setenv('PANDOC_FILTERS', str(tmp_path / 'missing'))
    pandoc_settings = render_settings(make_config(), 'org:tid:1.0.0').pandoc
    for name in ('docx-landscape.lua', 'docx-pagebreak.lua', 'docx-toc.lua'):
        path = pandoc_settings.filter_path(name)
        assert path == bundled_pandoc_filters() / name
        assert path.is_file()
    args = Pandoc(pandoc_settings, ['docx-pagebreak.lua'], None)._extra_args()
    assert args == ['--lua-filter', str(bundled_pandoc_filters() / 'docx-pagebreak.lua')]


def test_deployment_filters_take_precedence(monkeypatch, tmp_path: pathlib.Path):
    (tmp_path / 'docx-toc.lua').write_text('-- custom', encoding='utf-8')
    monkeypatch.setenv('PANDOC_FILTERS', str(tmp_path))
    monkeypatch.setenv('PANDOC_TEMPLATES', str(tmp_path))
    pandoc_settings = render_settings(make_config(), 'org:tid:1.0.0').pandoc
    assert pandoc_settings.filter_path('docx-toc.lua') == tmp_path / 'docx-toc.lua'
    assert pandoc_settings.templates_dir == tmp_path


def test_template_triggered_error_is_a_job_error_not_reported():
    exc = TemplateTriggeredError(title='Oops', message='Bad input')
    job_error = create_job_error(job_id='doc', message='Failed to build final document', exc=exc)
    assert isinstance(job_error, JobError)
    assert job_error.skip_reporting
    assert job_error.db_message() == 'Oops\n\nBad input'


@pytest.mark.parametrize('exc', [RuntimeError('boom'), None])
def test_other_errors_are_wrapped(exc):
    job_error = create_job_error(job_id='doc', message='Failed', exc=exc)
    assert not job_error.skip_reporting
    assert job_error.exc is exc


class FakeStorage:

    def __init__(self):
        self.project_files: list[str] = []

    def download_template_asset(self, *, tenant_uuid, template_uuid, file_name, target_path):
        target_path.write_bytes(b'asset')
        return True

    def download_project_file(self, *, tenant_uuid, project_uuid, file_uuid, target_path):
        self.project_files.append(f'{project_uuid}/{file_uuid}')
        target_path.write_bytes(b'project file')
        return True


@pytest.fixture
def worker_context(tmp_path: pathlib.Path):
    from dsw.document_worker.context import Context

    original = Context._instance
    s3 = FakeStorage()
    Context.initialize(db=None, s3=s3, config=make_config(), workdir=tmp_path)
    yield s3
    Context._instance = original


def test_worker_template_renders_from_db_composite(worker_context, tmp_path: pathlib.Path):
    from dsw.document_worker.templates.templates import Template, TemplateComposite

    root = types.SimpleNamespace(
        uuid='f1', file_name='root.j2', updated_at=1,
        content="{{ assets('logo.png').data.decode() }}|"
                "{{ assets({'uuid': 'p1', 'fileName': 'a.txt', 'contentType': 'text/plain'})"
                '.data.decode() }}|{{ ctx.name }}',
    )
    asset = types.SimpleNamespace(uuid='a1', file_name='logo.png', content_type='image/png',
                                  updated_at=1)
    db_template = types.SimpleNamespace(
        uuid='t1',
        coordinates='org:tid:1.0.0',
        formats=[{'uuid': 'f', 'name': 'HTML', 'steps': [
            {'name': 'jinja', 'options': {'template': 'root.j2'}},
        ]}],
    )
    template = Template(
        tenant_uuid='tenant',
        template_dir=tmp_path / 'tenant' / 't1',
        db_template=TemplateComposite(template=db_template, files={'f1': root},
                                      assets={'a1': asset}),
    )
    template.prepare_fs()
    assert template.prepare_format('f')
    template.prepare_locale(language='en', locale=None)
    document = template.render(format_uuid='f', project_uuid='p', context={'name': 'N'})
    assert document.content == b'asset|project file|N'
    assert worker_context.project_files == ['p/p1']
    # a document without a project cannot reach project files
    with pytest.raises(FormatStepError, match="'None' has no attribute 'data'"):
        template.render(format_uuid='f', project_uuid=None, context={'name': 'N'})


def test_context_config_uses_worker_configuration():
    from dsw.document_worker.config import DocumentContextConfig
    from dsw.document_worker.worker import Job

    job = types.SimpleNamespace(
        doc_context={'config': {'clientUrl': 'https://fw.example.org', 'appTitle': 'Mine'}},
        ctx=types.SimpleNamespace(app=types.SimpleNamespace(cfg=types.SimpleNamespace(
            context=DocumentContextConfig(
                service_name='FAIR Wizard', service_name_short='FW',
                service_url='https://fair-wizard.com', service_domain_name='fair-wizard.com',
                default_primary_color='#111111', default_illustrations_color='#222222',
                default_logo_url='{{clientUrl}}/logo.png', default_app_title='FW',
                default_app_title_short='FWs',
            ),
        ))),
    )
    Job._enrich_context_config(job)
    assert job.doc_context['config'] == {
        'clientUrl': 'https://fw.example.org',
        'serviceName': 'FAIR Wizard',
        'serviceNameShort': 'FW',
        'serviceUrl': 'https://fair-wizard.com',
        'serviceDomainName': 'fair-wizard.com',
        'appTitle': 'Mine',
        'appTitleShort': 'FWs',
        'primaryColor': '#111111',
        'illustrationsColor': '#222222',
        'logoUrl': 'https://fw.example.org/logo.png',
    }
