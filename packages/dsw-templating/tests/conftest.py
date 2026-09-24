import pathlib

import pytest

from dsw.templating import RenderSettings, Template, create_manager


@pytest.fixture
def make_template():
    """A template over a directory, with default settings and no project files."""
    def make(template_dir: pathlib.Path, **kwargs) -> Template:
        kwargs.setdefault('formats', [])
        kwargs.setdefault('coordinates', 'org:tid:1.0.0')
        kwargs.setdefault('settings', RenderSettings())
        kwargs.setdefault('plugins', create_manager())
        return Template(template_dir=template_dir, **kwargs)
    return make
