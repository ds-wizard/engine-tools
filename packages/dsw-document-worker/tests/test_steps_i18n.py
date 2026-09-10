import gettext
import pathlib
import types

import polib
import pytest

from dsw.document_worker.templates.locales import RenderContext
from dsw.document_worker.templates.steps.template import Jinja2Step


ROOT_FILE = 'src/root.j2'
ROOT_CONTENT = "{% trans %}Hello{% endtrans %}|{{ _('World') }}"


@pytest.fixture
def template_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / ROOT_FILE
    root.parent.mkdir(parents=True, exist_ok=True)
    root.write_text(ROOT_CONTENT, encoding='utf-8')
    return tmp_path


@pytest.fixture
def step(fake_context, template_dir: pathlib.Path) -> Jinja2Step:
    template = types.SimpleNamespace(
        template_dir=template_dir,
        coordinates='org:tid:1.0.0',
    )
    return Jinja2Step(template, {'template': ROOT_FILE})


def make_translations(tmp_path: pathlib.Path,
                      translations: dict[str, str]) -> gettext.GNUTranslations:
    po = polib.POFile()
    po.metadata = {'Content-Type': 'text/plain; charset=utf-8', 'Language': 'cs'}
    for msgid, msgstr in translations.items():
        po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
    mo_path = tmp_path / 'messages.mo'
    po.save_as_mofile(str(mo_path))
    with mo_path.open('rb') as fp:
        return gettext.GNUTranslations(fp)


def render(step: Jinja2Step) -> str:
    return step.execute_first({}).content.decode('utf-8')


def test_renders_untranslated_by_default(step):
    assert render(step) == 'Hello|World'


def test_renders_translated_after_before_render(step, tmp_path):
    translations = make_translations(tmp_path, {'Hello': 'Ahoj', 'World': 'Svete'})
    step.before_render(RenderContext(translations=translations, language='cs'))
    assert render(step) == 'Ahoj|Svete'


def test_locale_does_not_leak_to_next_document(step, tmp_path):
    translations = make_translations(tmp_path, {'Hello': 'Ahoj', 'World': 'Svete'})
    step.before_render(RenderContext(translations=translations, language='cs'))
    assert render(step) == 'Ahoj|Svete'

    step.before_render(RenderContext.null())
    assert render(step) == 'Hello|World'


def test_translation_helpers_on_step(step, tmp_path):
    translations = make_translations(tmp_path, {'Hello': 'Ahoj'})
    step.before_render(RenderContext(translations=translations, language='cs'))
    assert step.language == 'cs'
    assert step.gettext('Hello') == 'Ahoj'
    assert step.translations is translations


def test_legacy_i18n_options_are_ignored(fake_context, template_dir):
    template = types.SimpleNamespace(
        template_dir=template_dir,
        coordinates='org:tid:1.0.0',
    )
    step = Jinja2Step(template, {
        'template': ROOT_FILE,
        'jinja-ext': 'i18n',
        'i18n-dir': 'locale',
        'i18n-lang': 'cs',
        'i18n-domain': 'default',
    })
    assert render(step) == 'Hello|World'
