import io
import pathlib
import zipfile

import pytest

from dsw.templating import (
    DocumentFile,
    FileFormats,
    PandocSettings,
    TemplateError,
    TemplateTriggeredError,
)
from dsw.templating.conversions import FormatConversionError, Pandoc
from dsw.templating.settings import bundled_pandoc_filters
from dsw.templating.steps.word import EnrichDocxStep


def html_format(template: str) -> dict:
    return {
        'uuid': 'f',
        'name': 'HTML',
        'steps': [{'name': 'jinja', 'options': {'template': template}}],
    }


class PathProjectFiles:

    def __init__(self, path: pathlib.Path):
        self.path = path

    def resolve(self, file_uuid, name, content_type):
        return self.path if self.path.exists() else None


def test_unknown_format(make_template, tmp_path):
    with pytest.raises(TemplateError, match='Format x not found'):
        make_template(tmp_path).render('x', {})


def test_project_file_from_path(make_template, tmp_path):
    (tmp_path / 'root.j2').write_text(
        "{% set f = assets({'uuid': 'u', 'fileName': 'a.txt', 'contentType': 'text/plain'}) %}"
        '{{ f.data.decode() if f else "missing" }}',
        encoding='utf-8',
    )
    source = tmp_path / 'outside.txt'
    template = make_template(tmp_path, formats=[html_format('root.j2')])

    def render(**kwargs):
        return template.render('f', {}, **kwargs).content.decode('utf-8')

    assert render() == 'missing'
    assert render(project_files=PathProjectFiles(source)) == 'missing'
    source.write_text('content', encoding='utf-8')
    assert render(project_files=PathProjectFiles(source)) == 'content'
    assert render() == 'missing'  # the resolver does not outlive its rendering


def test_error_filter_raises_template_triggered_error(make_template, tmp_path):
    (tmp_path / 'root.j2').write_text("{{ 'Bad input'|error('Oops') }}", encoding='utf-8')
    template = make_template(tmp_path, formats=[html_format('root.j2')])
    with pytest.raises(TemplateTriggeredError) as e:
        template.render('f', {})
    assert e.value.msg == 'Oops\n\nBad input'


def test_enrich_docx_rewrites(make_template, tmp_path):
    (tmp_path / 'custom.xml.j2').write_text('<p>{{ ctx.name }}|{{ content }}</p>',
                                            encoding='utf-8')
    (tmp_path / 'static.xml').write_text('<static/>', encoding='utf-8')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode='w') as docx:
        docx.writestr('word/document.xml', '<doc/>')
        docx.writestr('docProps/custom.xml', '<old/>')
    step = EnrichDocxStep(make_template(tmp_path), {
        'rewrite:docProps/custom.xml': 'render:custom.xml.j2',
        'rewrite:word/extra.xml': 'static:static.xml',
    })
    result = step.execute_follow(DocumentFile(FileFormats.DOCX, buffer.getvalue()), {'name': 'N'})
    with zipfile.ZipFile(io.BytesIO(result.content)) as docx:
        assert docx.read('docProps/custom.xml') == b'<p>N|&lt;old/&gt;</p>'
        assert docx.read('word/extra.xml') == b'<static/>'
        assert docx.read('word/document.xml') == b'<doc/>'


def test_bundled_pandoc_filters_are_packaged():
    names = {path.name for path in bundled_pandoc_filters().iterdir()}
    assert {'docx-landscape.lua', 'docx-pagebreak.lua', 'docx-toc.lua'} <= names


def test_pandoc_filter_lookup_order(tmp_path):
    custom = tmp_path / 'custom'
    custom.mkdir()
    (custom / 'docx-toc.lua').write_text('-- custom', encoding='utf-8')
    (custom / 'mine.py').write_text('', encoding='utf-8')
    settings = PandocSettings(
        command=['pandoc'],
        filter_dirs=[custom, bundled_pandoc_filters()],
        templates_dir=tmp_path,
    )
    pandoc = Pandoc(settings, ['docx-toc.lua', 'docx-pagebreak.lua', 'mine.py'], None)
    assert pandoc._extra_args() == [
        '--lua-filter', str(custom / 'docx-toc.lua'),
        '--lua-filter', str(bundled_pandoc_filters() / 'docx-pagebreak.lua'),
        '--filter', str(custom / 'mine.py'),
    ]
    with pytest.raises(RuntimeError, match='Pandoc filter "nope.lua" not found'):
        Pandoc(settings, ['nope.lua'], None)
    with pytest.raises(RuntimeError, match='Pandoc template "nope.tex" not found'):
        Pandoc(settings, [], 'nope.tex')


def test_missing_pandoc_is_reported(tmp_path):
    pandoc = Pandoc(PandocSettings(command=[str(tmp_path / 'no-pandoc')]), [], None)
    with pytest.raises(FormatConversionError, match='no-pandoc" not found, is it installed'):
        pandoc(source_format=FileFormats.HTML, target_format=FileFormats.DOCX,
               data=b'<p/>', metadata={}, workdir=str(tmp_path))


def test_docx_pagebreak_filter():
    panflute = pytest.importorskip('panflute')
    from dsw.templating import docx_pagebreak

    doc = panflute.Doc(panflute.Para(panflute.Str(r'\newpage')),
                       panflute.Para(panflute.Str(r'\toc2')),
                       panflute.Para(panflute.Str('text')), format='docx')
    blocks = docx_pagebreak.main(doc).content
    assert blocks[0].text == '<w:p><w:r><w:br w:type="page" /></w:r></w:p>'
    assert 'TOC \\o "1-2"' in blocks[1].text
    assert isinstance(blocks[2], panflute.Para)


def test_docx_pagebreak_filter_is_installed():
    import importlib.metadata

    scripts = importlib.metadata.entry_points(group='console_scripts')
    assert scripts['pandoc-docx-pagebreakpy'].value == 'dsw.templating.docx_pagebreak:main'


def test_docx_pagebreak_filter_without_extra(monkeypatch):
    import sys

    from dsw.templating import docx_pagebreak

    monkeypatch.setitem(sys.modules, 'panflute', None)
    with pytest.raises(SystemExit, match=r'install dsw-templating\[docx\]'):
        docx_pagebreak.main()
