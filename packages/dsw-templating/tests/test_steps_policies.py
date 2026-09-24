import pathlib

import pytest

from dsw.templating import Template
from dsw.templating.steps.template import Jinja2Step


ROOT_FILE = 'src/root.j2'


@pytest.fixture
def template_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / ROOT_FILE
    root.parent.mkdir(parents=True, exist_ok=True)
    root.write_text('{{ ctx }}', encoding='utf-8')
    return tmp_path


def make_step(template_dir: pathlib.Path, **options) -> Jinja2Step:
    template = Template(template_dir=template_dir, formats=[], coordinates='org:tid:1.0.0')
    return Jinja2Step(template, {'template': ROOT_FILE, **options})


def test_extra_schemes_applied(template_dir):
    step = make_step(template_dir, **{'policy.urlize.extra_schemes': 'ftp:,tel:'})
    assert step.j2_env.policies['urlize.extra_schemes'] == ['ftp:', 'tel:']


def test_extra_schemes_does_not_clobber_truncate_leeway(template_dir):
    step = make_step(template_dir, **{
        'policy.urlize.extra_schemes': 'ftp:',
        'policy.truncate.leeway': '7',
    })
    assert step.j2_env.policies['truncate.leeway'] == '7'


def test_truncate_leeway_default_kept_without_extra_schemes(template_dir):
    step = make_step(template_dir, **{'policy.urlize.extra_schemes': 'ftp:'})
    assert step.j2_env.policies['truncate.leeway'] == 5
