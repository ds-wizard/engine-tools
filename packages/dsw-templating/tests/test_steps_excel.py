# cspell:ignore sqref
import io
import pathlib
import zipfile

import pytest

pytest.importorskip('xlsxwriter')

from dsw.templating.steps.excel import WorkbookBuilder  # noqa: E402


# 1x1 transparent PNG
PIXEL = ('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg==')


def build(tmp_path: pathlib.Path, sheet: dict, **data) -> zipfile.ZipFile:
    content = WorkbookBuilder.build_to_bytes(
        tmp_file=tmp_path / 'result.xlsx',
        input_data={'sheets': [{'name': 'Sheet1', **sheet}], **data},
    )
    return zipfile.ZipFile(io.BytesIO(content))


def sheet_xml(workbook: zipfile.ZipFile) -> str:
    return workbook.read('xl/worksheets/sheet1.xml').decode('utf-8')


def test_generic_cell(tmp_path):
    workbook = build(tmp_path, {'data': [
        {'type': 'cell', 'cell': 'A1', 'value': 'text'},
        {'type': 'cell', 'row': 1, 'col': 1, 'value': 42},
    ]})
    assert 'text' in workbook.read('xl/sharedStrings.xml').decode('utf-8')
    assert '<c r="B2"><v>42</v></c>' in sheet_xml(workbook)


def test_rich_string(tmp_path):
    workbook = build(
        tmp_path,
        {'data': [{
            'type': 'cell',
            'subtype': 'rich_string',
            'cell': 'A1',
            'format': 'center',
            'string_parts': ['plain ', '!fmt::bold', 'bold'],
        }]},
        formats={'bold': {'bold': True}, 'center': {'align': 'center'}},
    )
    strings = workbook.read('xl/sharedStrings.xml').decode('utf-8')
    assert 'plain ' in strings
    assert '<b/>' in strings


def test_image(tmp_path):
    workbook = build(tmp_path, {'data': [
        {'type': 'image', 'cell': 'A1', 'filename': 'a.png', 'b64bytes': PIXEL},
        {'type': 'image', 'row': 2, 'col': 2, 'filename': 'b.png', 'b64bytes': PIXEL},
    ]})
    assert len([n for n in workbook.namelist() if n.startswith('xl/media/')]) == 1


def test_repeat_columns(tmp_path):
    workbook = build(tmp_path, {'options': {'repeat_columns': {'first_col': 0, 'last_col': 1}}})
    assert "Sheet1!$A:$B" in workbook.read('xl/workbook.xml').decode('utf-8')


@pytest.mark.parametrize('key', ['col', 'column'])
def test_sparkline(tmp_path, key):
    workbook = build(tmp_path, {'options': {'sparklines': [
        {'row': 0, key: 3, 'options': {'range': 'Sheet1!A1:C1'}},
    ]}})
    assert '<xm:sqref>D1</xm:sqref>' in sheet_xml(workbook)
