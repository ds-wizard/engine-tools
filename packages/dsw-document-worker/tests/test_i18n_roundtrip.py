"""Extraction and rendering must agree on every msgid.

The POT file is generated per document template while a Jinja environment is
built per step, so any setting that changes a msgid has to be fixed for both.
These tests render with a catalog built from what the extractor actually
produced: if the two sides ever disagree, the lookup misses and the assertion
on the translated output fails.
"""
import gettext
import pathlib
import types

import polib
import pytest

from dsw.document_worker.pot import extract_messages
from dsw.document_worker.templates.locales import RenderContext
from dsw.document_worker.templates.steps.template import Jinja2Step


ROOT_FILE = 'src/root.j2'

SOURCE = """<p>
  {% trans %}
    Hello there
  {% endtrans %}
</p>
<pre>{% trans notrimmed %}
  keep
  this
{% endtrans %}</pre>
<p>
  {% trans count = ctx['n'] %}
    one item
  {% pluralize %}
    many items
  {% endtrans %}
</p>
"""


def build_catalog(source: str, translate) -> gettext.GNUTranslations:
    """Compile a catalog keyed by the msgids the extractor produced."""
    po = polib.POFile()
    po.metadata = {
        'Content-Type': 'text/plain; charset=utf-8',
        'Language': 'cs',
        'Plural-Forms': 'nplurals=2; plural=(n != 1);',
    }
    for _lineno, message, _comments, _context in extract_messages(source):
        if isinstance(message, tuple):
            po.append(polib.POEntry(
                msgid=message[0],
                msgid_plural=message[1],
                msgstr_plural={0: translate(message[0]), 1: translate(message[1])},
            ))
        else:
            po.append(polib.POEntry(msgid=message, msgstr=translate(message)))
    return po


@pytest.fixture
def step(fake_context, tmp_path: pathlib.Path) -> Jinja2Step:
    root = tmp_path / ROOT_FILE
    root.parent.mkdir(parents=True, exist_ok=True)
    root.write_text(SOURCE, encoding='utf-8')
    template = types.SimpleNamespace(
        template_dir=tmp_path,
        coordinates='org:tid:1.0.0',
    )
    return Jinja2Step(template, {'template': ROOT_FILE})


def install(step: Jinja2Step, tmp_path: pathlib.Path, translate) -> None:
    mo_path = tmp_path / 'messages.mo'
    build_catalog(SOURCE, translate).save_as_mofile(str(mo_path))
    with mo_path.open('rb') as fp:
        step.before_render(RenderContext(translations=gettext.GNUTranslations(fp),
                                         language='cs'))


def render(step: Jinja2Step, **ctx) -> str:
    return step.execute_first(ctx).content.decode('utf-8')


def test_extracted_msgids_are_trimmed():
    messages = [m for _, m, _, _ in extract_messages(SOURCE)]
    assert 'Hello there' in messages
    assert ('one item', 'many items') in messages


def test_notrimmed_block_keeps_its_whitespace():
    messages = [m for _, m, _, _ in extract_messages(SOURCE)]
    assert '\n  keep\n  this\n' in messages


def test_every_extracted_msgid_is_found_at_render_time(step, tmp_path):
    install(step, tmp_path, lambda msgid: f'<{msgid}>')
    output = render(step, n=1)
    assert '<Hello there>' in output
    assert '<\n  keep\n  this\n>' in output
    assert '<one item>' in output


def test_plural_lookup_agrees(step, tmp_path):
    install(step, tmp_path, lambda msgid: f'<{msgid}>')
    assert '<many items>' in render(step, n=5)


def test_reindenting_the_template_keeps_the_msgid(fake_context, tmp_path):
    reindented = SOURCE.replace('    Hello there', '            Hello there')
    assert reindented != SOURCE
    original = [m for _, m, _, _ in extract_messages(SOURCE)]
    changed = [m for _, m, _, _ in extract_messages(reindented)]
    assert original == changed
