# cspell:ignore Plán správy
"""Golden outputs of a small fixture template, one per built-in step chain.

Deterministic outputs are compared byte for byte with ``fixtures/golden``; for
archives and spreadsheets the relevant members are compared instead, as the
containers carry timestamps (and the line endings of XML members are normalized). Run with ``UPDATE_GOLDEN=1`` to rewrite them.
"""
import gettext
import io
import json
import os
import pathlib
import shutil
import zipfile

import polib
import pytest

from dsw.templating import (
    FileFormats,
    RenderContext,
    RenderSettings,
    Template,
    create_manager,
    hookimpl,
)


FIXTURES = pathlib.Path(__file__).parent / 'fixtures'
GOLDEN = FIXTURES / 'golden'
UPDATE = os.getenv('UPDATE_GOLDEN') == '1'

FORMAT_JSON = '11111111-0000-0000-0000-000000000001'
FORMAT_HTML = '11111111-0000-0000-0000-000000000002'
FORMAT_ZIP = '11111111-0000-0000-0000-000000000003'
FORMAT_XLSX = '11111111-0000-0000-0000-000000000004'
FORMAT_PDF = '11111111-0000-0000-0000-000000000005'
FORMAT_DOCX = '11111111-0000-0000-0000-000000000006'


class EnrichingPlugin:

    @hookimpl
    def enrich_document_context(self, context: dict) -> None:
        context.setdefault('extras', {})['plugin'] = 'Enriched by a plugin'


class FakeProjectFiles:

    def __init__(self):
        self.requested: list[str] = []

    def resolve(self, file_uuid: str, name: str, content_type: str) -> bytes | None:
        self.requested.append(file_uuid)
        return b'Project file content'


def assert_golden(name: str, data: bytes):
    path = GOLDEN / name
    if name.endswith('.xml'):
        # XlsxWriter ends the XML declaration with the platform line separator
        data = data.replace(b'\r\n', b'\n')
    if UPDATE:
        path.write_bytes(data)
    assert data == path.read_bytes(), f'{name} differs from its golden file'


@pytest.fixture
def template(tmp_path: pathlib.Path) -> Template:
    template_dir = tmp_path / 'template'
    shutil.copytree(FIXTURES / 'template', template_dir)
    plugins = create_manager()
    plugins.register(EnrichingPlugin())
    return Template.from_directory(template_dir, settings=RenderSettings(), plugins=plugins)


@pytest.fixture
def context() -> dict:
    return json.loads((FIXTURES / 'context.json').read_text(encoding='utf-8'))


@pytest.fixture
def render_ctx(tmp_path: pathlib.Path) -> RenderContext:
    po = polib.POFile()
    po.metadata = {'Content-Type': 'text/plain; charset=utf-8', 'Language': 'cs'}
    po.append(polib.POEntry(msgid='Data Management Plan', msgstr='Plán správy dat'))
    mo_path = tmp_path / 'messages.mo'
    po.save_as_mofile(str(mo_path))
    with mo_path.open('rb') as fp:
        return RenderContext(translations=gettext.GNUTranslations(fp), language='cs')


def test_template_from_directory(template):
    assert template.coordinates == 'dsw:golden:1.0.0'
    assert template.has_format(FORMAT_HTML)
    asset = template.fetch_asset('assets/logo.png')
    assert asset is not None
    assert asset.content_type == 'image/png'
    assert template.fetch_asset('assets/missing.png') is None


def test_json(template, context):
    document = template.render(FORMAT_JSON, context)
    assert document.file_format == FileFormats.JSON
    assert document.encoding == 'utf-8'
    assert_golden('document.json', document.content)


def test_html(template, context, render_ctx):
    project_files = FakeProjectFiles()
    document = template.render(FORMAT_HTML, context,
                               render_ctx=render_ctx, project_files=project_files)
    assert document.file_format == FileFormats.HTML
    assert project_files.requested == ['22222222-0000-0000-0000-000000000001']
    assert_golden('document.html', document.content)


def test_html_without_translations_and_project_files(template, context):
    content = template.render(FORMAT_HTML, context).content.decode('utf-8')
    assert '<h1>Data Management Plan</h1>' in content
    assert 'notes.txt' not in content  # no project files, the template renders on


def test_zip(template, context, render_ctx):
    document = template.render(FORMAT_ZIP, context,
                               render_ctx=render_ctx, project_files=FakeProjectFiles())
    assert document.file_format == FileFormats.ZIP
    with zipfile.ZipFile(io.BytesIO(document.content)) as archive:
        assert archive.namelist() == ['report.html']
        assert archive.getinfo('report.html').compress_type == zipfile.ZIP_DEFLATED
        assert_golden('document.html', archive.read('report.html'))


def test_excel(template, context):
    pytest.importorskip('xlsxwriter')
    document = template.render(FORMAT_XLSX, context)
    assert document.file_format == FileFormats.XLSX
    with zipfile.ZipFile(io.BytesIO(document.content)) as workbook:
        assert_golden('sheet1.xml', workbook.read('xl/worksheets/sheet1.xml'))
        assert_golden('sharedStrings.xml', workbook.read('xl/sharedStrings.xml'))


def test_pdf(template, context):
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError) as e:  # OSError: Pango is not installed
        pytest.skip(f'WeasyPrint is not usable: {e}')
    document = template.render(FORMAT_PDF, context, project_files=FakeProjectFiles())
    assert document.file_format == FileFormats.PDF
    assert document.content.startswith(b'%PDF-')


def test_docx(template, context):
    if shutil.which('pandoc') is None:
        pytest.skip('pandoc is not installed')
    document = template.render(FORMAT_DOCX, context, project_files=FakeProjectFiles())
    assert document.file_format == FileFormats.DOCX
    with zipfile.ZipFile(io.BytesIO(document.content)) as docx:
        assert 'Golden Plan' in docx.read('docProps/custom.xml').decode('utf-8')
        # the bundled Lua filter turned the class into an OOXML page break
        assert 'w:type="page"' in docx.read('word/document.xml').decode('utf-8')
