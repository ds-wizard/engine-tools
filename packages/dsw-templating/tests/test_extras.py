"""Optional dependencies: importing works without them, using a step does not."""
import pathlib
import subprocess
import sys

import pytest

from dsw.templating import MissingExtraError, TemplateError


EXTRA_MODULES = ('panflute', 'rdflib', 'requests', 'weasyprint', 'xlsxwriter')

IMPORT_ALL = f"""
import importlib, pkgutil, sys
for name in {EXTRA_MODULES!r}:
    sys.modules[name] = None  # makes any import of it fail
import dsw.templating
for mod in pkgutil.walk_packages(dsw.templating.__path__, 'dsw.templating.'):
    importlib.import_module(mod.name)
leaked = sorted(name for name in {EXTRA_MODULES!r} if sys.modules.get(name) is not None)
assert not leaked, leaked
print('ok')
"""


def block(monkeypatch, *modules: str):
    for module in modules:
        monkeypatch.setitem(sys.modules, module, None)


def jinja_format(template: str, *steps: dict) -> dict:
    return {
        'uuid': 'f',
        'name': 'Format',
        'steps': [
            {'name': 'jinja', 'options': {'template': template}},
            *steps,
        ],
    }


@pytest.fixture
def template_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / 'root.j2').write_text('{{ rdflib.Graph() }}', encoding='utf-8')
    return tmp_path


def test_import_without_extras():
    result = subprocess.run(
        [sys.executable, '-c', IMPORT_ALL],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'ok'


@pytest.mark.parametrize(('step', 'options', 'module', 'extra'), [
    ('weasyprint', {}, 'weasyprint', 'pdf'),
    ('excel', {}, 'xlsxwriter', 'excel'),
    ('rdflib-convert', {'from': 'turtle', 'to': 'jsonld'}, 'rdflib', 'rdf'),
])
def test_step_without_extra_fails_clearly(monkeypatch, make_template, template_dir,
                                          step, options, module, extra):
    block(monkeypatch, module)
    template = make_template(template_dir, formats=[
        jinja_format('root.j2', {'name': step, 'options': options}),
    ])
    with pytest.raises(TemplateError, match=rf'install dsw-templating\[{extra}\]'):
        template.prepare_format('f')


def test_requests_without_extra_fails_clearly(monkeypatch, make_template, template_dir):
    from dsw.templating import RenderSettings, RequestsSettings, TemplateSettings

    block(monkeypatch, 'requests')
    settings = RenderSettings(template=TemplateSettings(requests=RequestsSettings(enabled=True)))
    template = make_template(template_dir, formats=[jinja_format('root.j2')], settings=settings)
    with pytest.raises(TemplateError, match=r'install dsw-templating\[http\]'):
        template.prepare_format('f')


def test_rdflib_global_without_extra_fails_when_used(monkeypatch, make_template, template_dir):
    block(monkeypatch, 'rdflib')
    template = make_template(template_dir, formats=[jinja_format('root.j2')])
    with pytest.raises(MissingExtraError, match=r'install dsw-templating\[rdf\]'):
        template.render('f', {})
