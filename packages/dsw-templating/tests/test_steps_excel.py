# cspell:ignore sqref dxf
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


def test_active_sheet(tmp_path):
    content = WorkbookBuilder.build_to_bytes(
        tmp_file=tmp_path / 'result.xlsx',
        input_data={'sheets': [{'name': 'A'}, {'name': 'B'}], 'options': {'active_sheet': 1}},
    )
    workbook = zipfile.ZipFile(io.BytesIO(content))
    assert 'activeTab="1"' in workbook.read('xl/workbook.xml').decode('utf-8')


@pytest.mark.parametrize('freeze', ['B3', {'row': 2, 'col': 1}])
def test_freeze_panes(tmp_path, freeze):
    workbook = build(tmp_path, {'options': {'freeze_panes': freeze}})
    assert 'topLeftCell="B3" activePane="bottomRight" state="frozen"' in sheet_xml(workbook)


@pytest.mark.parametrize('autofilter', ['A1:C6', {'last_row': 5, 'last_col': 2}])
def test_filters(tmp_path, autofilter):
    workbook = build(tmp_path, {'options': {
        'autofilter': autofilter,
        'filter_column_lists': [{'col': 0, 'filters': ['x']}],
        'filter_columns': [{'col': 1, 'criteria': 'x > 5'}],
    }})
    xml = sheet_xml(workbook)
    assert '<autoFilter ref="A1:C6">' in xml
    assert '<filterColumn colId="0"><filters><filter val="x"/>' in xml
    assert '<customFilter operator="greaterThan" val="5"/>' in xml


@pytest.mark.parametrize('item', [
    {'range': 'A1:A2', 'options': {'type': 'no_blanks', 'format': 'bold'}},
    {'range': 'A1:A2', 'format': 'bold', 'options': {'type': 'no_blanks'}},
])
def test_conditional_format(tmp_path, item):
    workbook = build(
        tmp_path,
        {'options': {'conditional_formats': [item]}},
        formats={'bold': {'bold': True}},
    )
    assert '<cfRule type="notContainsBlanks" dxfId="0"' in sheet_xml(workbook)


def test_ranges_without_options(tmp_path):
    workbook = build(tmp_path, {'options': {
        'conditional_formats': [{'range': 'A1:A2'}],
        'data_validations': [{'range': 'A1'}],
        'tables': [{'range': 'A1:B3'}],
        'sparklines': [{'cell': 'D1'}],
    }})
    assert 'xl/tables/table1.xml' in workbook.namelist()
