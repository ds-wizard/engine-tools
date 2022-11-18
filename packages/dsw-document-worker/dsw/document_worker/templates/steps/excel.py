import base64
import datetime
import dateutil.parser
import io
import json
import pathlib

import xlsxwriter
from xlsxwriter.chart import Chart
from xlsxwriter.format import Format
from xlsxwriter.worksheet import Worksheet

from typing import Any

from ...documents import DocumentFile, FileFormats
from .base import Step, register_step, TMP_DIR, FormatStepException


_EMPTY_DICT = {}  # type: dict[str, Any]
_EMPTY_LIST = []  # type: list[Any]


def _b64img2io(b64bytes: str) -> io.BytesIO:
    # strip metadata (e.g. "data:image/jpeg;base64,...")
    if ',' in b64bytes:
        b64bytes = b64bytes.split(',')[1]
    # decode and return
    return io.BytesIO(base64.b64decode(b64bytes))


def _cell_writer_generic(worksheet: Worksheet, pos_args, item, cell_format):
    worksheet.write(
        *pos_args,
        **item,
        cell_format=cell_format,
    )


def _cell_writer_string(worksheet: Worksheet, pos_args, item, cell_format):
    worksheet.write_string(
        *pos_args,
        string=item.get('value', ''),
        cell_format=cell_format,
    )


def _cell_writer_number(worksheet: Worksheet, pos_args, item, cell_format):
    worksheet.write_number(
        *pos_args,
        number=item.get('value', 0),
        cell_format=cell_format,
    )


def _cell_writer_datetime(worksheet: Worksheet, pos_args, item, cell_format):
    try:
        value = dateutil.parser.parse(item['value'])
    except Exception:
        value = datetime.datetime.utcnow()
    worksheet.write_datetime(
        *pos_args,
        date=value,
        cell_format=cell_format,
    )


def _cell_writer_formula(worksheet: Worksheet, pos_args, item, cell_format):
    worksheet.write_formula(
        *pos_args,
        formula=item.get('value', ''),
        value=item.get('result', None),
        cell_format=cell_format,
    )


def _cell_writer_blank(worksheet: Worksheet, pos_args, item, cell_format):
    worksheet.write_blank(
        *pos_args,
        blank=None,
        cell_format=cell_format,
    )


def _cell_writer_boolean(worksheet: Worksheet, pos_args, item, cell_format):
    worksheet.write_boolean(
        *pos_args,
        boolean=item.get('value', False),
        cell_format=cell_format,
    )


def _cell_writer_url(worksheet: Worksheet, pos_args, item, cell_format):
    worksheet.write_url(
        *pos_args,
        url=item.get('url', ''),
        string=item.get('value', None),
        tip=item.get('tip', None),
        cell_format=cell_format,
    )


_CELL_WRITERS = {
    '': _cell_writer_generic,
    'string': _cell_writer_string,
    'number': _cell_writer_number,
    'datetime': _cell_writer_datetime,
    'formula': _cell_writer_formula,
    'blank': _cell_writer_blank,
    'boolean': _cell_writer_boolean,
    'url': _cell_writer_url,
}


class WorkbookBuilder:

    def __init__(self, workbook: xlsxwriter.Workbook):
        self.workbook = workbook
        self.sheets = list()  # type: list[Worksheet]
        self.formats = dict()  # type: dict[str, Format]
        self.charts = dict()  # type: dict[str, Chart]

    def _add_workbook_options(self, data: dict):
        # customized options not in regular 'constructor options'
        options = data.get('options', _EMPTY_DICT)
        if 'active_sheet' in options.keys():
            sheet_index = options['active_sheet']
            if 0 <= sheet_index < len(self.sheets):
                self.sheets[sheet_index].activate()
        if 'vba_name' in options.keys():
            self.workbook.set_vba_name(options['vba_name'])
        if 'size' in options.keys():
            self.workbook.set_size(
                width=options['size'].get('width'),
                height=options['size'].get('height'),
            )
        if 'tab_ratio' in options.keys():
            self.workbook.set_tab_ratio(options['tab_ratio'])

    def _add_workbook_properties(self, data: dict):
        props = data.get('properties', _EMPTY_DICT)
        if 'document' in props.keys():
            if 'created' in props['document']:
                props['document']['created'] = dateutil.parser.parse(
                    timestr=props['document']['created'],
                )
            self.workbook.set_properties(props['document'])
        if 'custom' in props.keys():
            for prop in props['custom']:
                name = prop.get('name', 'unnamed')
                value = prop.get('value', '')
                property_type = prop.get('type', None)
                if property_type == 'date':
                    value = dateutil.parser.parse(value)
                self.workbook.set_custom_property(
                    name=name,
                    value=value,
                    property_type=property_type,
                )

    def _add_workbook_definitions(self, data: dict):
        definitions = data.get('definitions', _EMPTY_DICT)
        for name, value in definitions.items():
            self.workbook.define_name(str(name), str(value))

    def _add_format(self, name: str, data: dict):
        self.formats[name] = self.workbook.add_format(data)

    def _add_chart(self, data: dict):
        name = data.get('name', '')
        options = data.get('options', _EMPTY_DICT)
        series_list = data.get('series', _EMPTY_LIST)
        chart = self.workbook.add_chart(options)
        if chart is None:
            return
        for series in series_list:
            chart.add_series(series)
        self._add_chart_axis(chart, data)
        self._add_chart_advanced(chart, data)
        self.charts[name] = chart

    def _add_chart_axis(self, chart: Chart, data: dict):
        axis = data.get('axis', _EMPTY_DICT)
        if 'x' in axis.keys():
            chart.set_x_axis(axis['x'])
        if 'x2' in axis.keys():
            chart.set_x2_axis(axis['x2'])
        if 'y' in axis.keys():
            chart.set_y_axis(axis['y'])
        if 'y2' in axis.keys():
            chart.set_y2_axis(axis['y2'])

    def _add_chart_basic(self, chart: Chart, data: dict):
        if 'size' in data.keys():
            chart.set_size(data['size'])
        if 'title' in data.keys():
            chart.set_title(data['title'])
        if 'legend' in data.keys():
            chart.set_legend(data['legend'])
        if 'chartarea' in data.keys():
            chart.set_chartarea(data['chartarea'])
        if 'plotarea' in data.keys():
            chart.set_plotarea(data['plotarea'])
        if 'style' in data.keys():
            chart.set_style(data['style'])
        if 'table' in data.keys():
            chart.set_table(data['table'])

    def _add_chart_advanced(self, chart: Chart, data: dict):
        if 'combine' in data.keys():
            other = data['combine']
            if other in self.charts.keys():
                chart.combine(self.charts[other])
        if 'up_down_bars' in data.keys():
            chart.set_up_down_bars(data['up_down_bars'])
        if 'drop_lines' in data.keys():
            chart.set_drop_lines(data['drop_lines'])
        if 'high_low_lines' in data.keys():
            chart.set_high_low_lines(data['high_low_lines'])
        if 'show_blanks_as' in data.keys():
            chart.show_blanks_as(data['show_blanks_as'])
        if 'show_hidden_data' in data.keys():
            chart.show_hidden_data()

    def _add_chartsheet(self, data: dict):
        name = data.get('name', None)
        chart_name = data.get('chart', '')
        if chart_name not in self.charts.keys():
            return  # ignore if chart is missing
        sheet = self.workbook.add_chartsheet(name)
        sheet.set_chart(self.charts[chart_name])
        self.sheets.append(sheet)
        self._setup_worksheet_common(sheet, data)

    def _add_worksheet(self, data: dict):
        name = data.get('name', None)
        sheet = self.workbook.add_worksheet(name)
        self.sheets.append(sheet)
        self._setup_worksheet_common(sheet, data)
        self._setup_worksheet_data(sheet, data)
        self._add_data_to_worksheet(sheet, data)

    def _add_object_to_worksheet(self, worksheet: Worksheet, item: dict):
        item_type = item.get('type', None)
        if item_type == 'chart':
            self._add_data_chart(worksheet, item)
        elif item_type == 'comment':
            self._add_data_comment(worksheet, item)
        elif item_type == 'textbox':
            self._add_data_textbox(worksheet, item)
        elif item_type == 'button':
            self._add_data_button(worksheet, item)
        elif item_type == 'image':
            self._add_data_image(worksheet, item)

    def _add_data_to_worksheet(self, worksheet: Worksheet, data: dict):
        for item in data.get('data', _EMPTY_LIST):
            item_type = item.get('type', None)
            if item_type is None:
                continue
            elif item_type == 'cell':
                self._add_data_cell(worksheet, item)
            elif item_type == 'row':
                self._add_data_row(worksheet, item)
            elif item_type == 'column':
                self._add_data_column(worksheet, item)
            elif item_type == 'grid':
                self._add_data_grid(worksheet, item)
            elif item_type == 'array_formula':
                self._add_data_array_formula(worksheet, item)
            else:
                self._add_object_to_worksheet(worksheet, item)

    def _add_data_cell(self, worksheet: Worksheet, item: dict):
        subtype = item.get('subtype', '')
        cell_format = self.formats.get(item.get('format', ''), None)
        if 'cell' in item.keys():
            pos_args = [item['cell']]
        else:
            pos_args = [
                item.get('row', 0),
                item.get('col', 0),
            ]
        item.pop('type', None)
        item.pop('subtype', None)
        item.pop('format', None)
        item.pop('cell', None)
        item.pop('row', None)
        item.pop('col', None)
        if subtype in _CELL_WRITERS.keys():
            _CELL_WRITERS[subtype](worksheet, pos_args, item, cell_format)
        elif subtype == 'rich_string':
            parts = []
            for p in item.get('string_parts', []):
                if not isinstance(p, str):
                    continue
                if p.startswith('!fmt::'):
                    format_name = p[6:]
                    parts.append(self.formats.get(format_name, ''))
                else:
                    parts.append(p)
            worksheet.write_rich_string(
                *pos_args,
                string_parts=parts,
                cell_format=cell_format,
            )

    def _add_data_row(self, worksheet: Worksheet, item: dict):
        cell_format = self.formats.get(item.get('format', ''), None)
        if 'cell' in item.keys():
            worksheet.write_row(
                item['cell'],
                data=item.get('data', []),
                cell_format=cell_format,
            )
        else:
            worksheet.write_row(
                row=item.get('row', 0),
                col=item.get('col', 0),
                data=item.get('data', []),
                cell_format=cell_format,
            )

    def _add_data_column(self, worksheet: Worksheet, item: dict):
        cell_format = self.formats.get(item.get('format', ''), None)
        if 'cell' in item.keys():
            worksheet.write_column(
                item['cell'],
                data=item.get('data', []),
                cell_format=cell_format,
            )
        else:
            worksheet.write_column(
                row=item.get('row', 0),
                col=item.get('col', 0),
                data=item.get('data', []),
                cell_format=cell_format,
            )

    def _add_data_grid(self, worksheet: Worksheet, item: dict):
        cell_format = self.formats.get(item.get('format', ''), None)
        grid = item.get('data', [])
        rows = len(grid)
        start_row = item.get('row', 0)
        start_col = item.get('col', 0)
        for row_index in range(rows):
            worksheet.write_row(
                row=start_row + row_index,
                col=start_col,
                data=grid[row_index],
                cell_format=cell_format,
            )

    def _add_data_chart(self, worksheet: Worksheet, item: dict):
        chart = self.charts.get(item.get('chart', ''), None)
        if chart is None:
            return
        if 'cell' in item.keys():
            worksheet.insert_chart(
                item['cell'],
                chart=chart,
                options=item.get('options', None),
            )
        else:
            worksheet.insert_chart(
                row=item.get('row', 0),
                col=item.get('col', 0),
                chart=chart,
                options=item.get('options', None),
            )

    @staticmethod
    def _add_data_comment(worksheet: Worksheet, item: dict):
        if 'cell' in item.keys():
            worksheet.write_comment(
                item['cell'],
                comment=item.get('comment', ''),
                options=item.get('options', None),
            )
        else:
            worksheet.write_comment(
                row=item.get('row', 0),
                col=item.get('col', 0),
                comment=item.get('comment', ''),
                options=item.get('options', None),
            )

    @staticmethod
    def _add_data_textbox(worksheet: Worksheet, item: dict):
        if 'cell' in item.keys():
            worksheet.insert_textbox(
                item['cell'],
                text=item.get('text', ''),
                options=item.get('options', None),
            )
        else:
            worksheet.insert_textbox(
                row=item.get('row', 0),
                col=item.get('col', 0),
                text=item.get('text', ''),
                options=item.get('options', None),
            )

    @staticmethod
    def _add_data_button(worksheet: Worksheet, item: dict):
        if 'cell' in item.keys():
            worksheet.insert_button(
                item['cell'],
                options=item.get('options', None),
            )
        else:
            worksheet.insert_button(
                row=item.get('row', 0),
                col=item.get('col', 0),
                options=item.get('options', None),
            )

    @staticmethod
    def _add_data_image(worksheet: Worksheet, item: dict):
        bytes_io = io.BytesIO()
        if 'b64bytes' in item.keys():
            if 'options' not in item.keys():
                item['options'] = dict()
            bytes_io = _b64img2io(item['b64bytes'])
            item['options']['image_data'] = bytes_io
        if 'cell' in item.keys():
            worksheet.insert_image(
                item['cell'],
                filename=item.get('filename', ''),
                options=item.get('options', None),
            )
        else:
            worksheet.insert_image(
                row=item.get('row', 0),
                col=item.get('col', 0),
                filename=item.get('filename', ''),
                options=item.get('options', None),
            )
        # TODO: check closed io at the end (cannot close before closing Excel)

    def _add_data_array_formula(self, worksheet: Worksheet, item: dict):
        method = worksheet.write_array_formula
        if item.get('dynamic', False):
            method = worksheet.write_dynamic_array_formula
        cell_format = self.formats.get(item.get('format', ''), None)
        if 'range' in item.keys():
            method(
                item['range'],
                formula=item.get('formula', ''),
                cell_format=cell_format,
                value=item.get('value', 0),
            )
        else:
            method(
                first_row=item.get('first_row', 0),
                first_col=item.get('first_col', 0),
                last_row=item.get('last_row', 0),
                last_col=item.get('last_col', 0),
                formula=item.get('formula', ''),
                cell_format=cell_format,
                value=item.get('value', 0),
            )

    @classmethod
    def _setup_worksheet_print(cls, worksheet: Worksheet, data: dict):
        if 'orientation' in data.keys():
            if data['orientation'] == 'landscape':
                worksheet.set_landscape()
            elif data['orientation'] == 'portrait':
                worksheet.set_portrait()
        if 'paper' in data.keys():
            worksheet.set_paper(data['paper'])
        if 'margins' in data.keys():
            worksheet.set_margins(**data['margins'])
        if 'header' in data.keys():
            options = data['header'].get('options', None)
            cls._fix_footer_header_images(options)
            worksheet.set_header(
                header=data['header'].get('content', ''),
                options=options,
            )
        if 'footer' in data.keys():
            options = data['footer'].get('options', None)
            cls._fix_footer_header_images(options)
            worksheet.set_footer(
                footer=data['footer'].get('content', ''),
                options=options,
            )
        if data.get('center_horizontally', False):
            worksheet.center_horizontally()
        if data.get('center_vertically', False):
            worksheet.center_vertically()

    @staticmethod
    def _fix_footer_header_images(options):
        if not isinstance(options, dict):
            return
        for key in ('image_data_left', 'image_data_center', 'image_data_right'):
            if key in options.keys():
                options[key] = _b64img2io(options[key])

    @classmethod
    def _setup_worksheet_common(cls, worksheet: Worksheet, data: dict):
        data = data.get('options', None)
        if data is None:
            return
        if data.get('select', False):
            worksheet.select()
        if data.get('hide', False):
            worksheet.hide()
        if data.get('first_sheet', False):
            worksheet.set_first_sheet()
        if 'protect' in data.keys():
            worksheet.protect(
                password=data['protect'].get('password', ''),
                options=data['protect'].get('options', None),
            )
        if 'zoom' in data.keys():
            worksheet.set_zoom(data['zoom'])
        if 'tab_color' in data.keys():
            worksheet.set_tab_color(data['tab_color'])
        if data.get('page_view', False):
            worksheet.set_page_view()
        cls._setup_worksheet_print(worksheet, data)

    def _setup_worksheet_data(self, worksheet: Worksheet, data: dict):
        data = data.get('options', None)
        if data is None:
            return
        self._setup_worksheet_basic(worksheet, data)
        self._setup_worksheet_printing(worksheet, data)
        self._setup_worksheet_special_ranges(worksheet, data)
        self._setup_worksheet_repeats(worksheet, data)
        self._setup_worksheet_paging(worksheet, data)
        self._setup_worksheet_panes(worksheet, data)
        self._setup_worksheet_filters(worksheet, data)
        self._setup_worksheet_merge_ranges(worksheet, data)
        self._setup_worksheet_data_validations(worksheet, data)
        self._setup_worksheet_conditional_formats(worksheet, data)
        self._setup_worksheet_tables(worksheet, data)
        self._setup_worksheet_sparklines(worksheet, data)
        self._setup_worksheet_row_sizing(worksheet, data)
        self._setup_worksheet_col_sizing(worksheet, data)
        self._setup_worksheet_background(worksheet, data)

    @staticmethod
    def _setup_worksheet_basic(worksheet: Worksheet, data: dict):
        if 'comments_author' in data.keys():
            worksheet.set_comments_author(data['comments_author'])
        if data.get('hide_zero', False):
            worksheet.hide_zero()
        if data.get('hide_row_col_headers', False):
            worksheet.hide_row_col_headers()
        if data.get('right_to_left', False):
            worksheet.right_to_left()
        if 'hide_gridlines' in data.keys():
            worksheet.hide_gridlines(data['hide_gridlines'])
        if 'ignore_errors' in data.keys():
            worksheet.ignore_errors(data['ignore_errors'])
        if 'vba_name' in data.keys():
            worksheet.set_vba_name(data['vba_name'])

    @staticmethod
    def _setup_worksheet_printing(worksheet: Worksheet, data: dict):
        if data.get('print_row_col_headers', False):
            worksheet.print_row_col_headers()
        if 'print_area' in data.keys():
            area = data['print_area']
            if isinstance(area, dict):
                worksheet.print_area(**area)
            else:
                worksheet.print_area(area)
        if data.get('print_across', False):
            worksheet.print_across()
        if 'fit_to_pages' in data.keys():
            worksheet.fit_to_pages(
                width=data['fit_to_pages'].get('width', 1),
                height=data['fit_to_pages'].get('height', 1),
            )
        if 'start_page' in data.keys():
            worksheet.set_start_page(data['start_page'])
        if 'print_scale' in data.keys():
            worksheet.set_print_scale(data['print_scale'])
        if data.get('print_black_and_white', False):
            worksheet.print_black_and_white()

    @staticmethod
    def _setup_worksheet_special_ranges(worksheet: Worksheet, data: dict):
        if 'unprotect_ranges' in data.keys():
            for r in data['unprotect_ranges']:
                worksheet.unprotect_range(
                    cell_range=r.get('range', 'A1'),
                    range_name=r.get('name', None),
                )
        if 'top_left_cell' in data.keys():
            if isinstance(data['top_left_cell'], str):
                worksheet.set_top_left_cell(data['top_left_cell'])
            else:
                worksheet.set_top_left_cell(
                    row=data['top_left_cell'].get('row', 0),
                    col=data['top_left_cell'].get('col', 0),
                )
        if 'selection' in data.keys():
            if isinstance(data['selection'], str):
                worksheet.set_selection(data['selection'])
            else:
                first_row = data['selection'].get('first_row', 0)
                first_col = data['selection'].get('first_col', 0)
                worksheet.set_selection(
                    first_row=first_row,
                    first_col=first_col,
                    last_row=data['selection'].get('last_row', first_row),
                    last_col=data['selection'].get('last_col', first_col),
                )

    @staticmethod
    def _setup_worksheet_repeats(worksheet: Worksheet, data: dict):
        if 'repeat_rows' in data.keys():
            worksheet.repeat_rows(
                first_row=data['repeat_rows'].get('first_row', 0),
                last_row=data['repeat_rows'].get('last_row', None),
            )
        if 'repeat_columns' in data.keys():
            worksheet.repeat_columns(
                first_row=data['repeat_columns'].get('first_col', 0),
                last_row=data['repeat_columns'].get('last_col', None),
            )
        if 'default_row' in data.keys():
            worksheet.set_default_row(
                height=data['default_row'].get('height', 15),
                hide_unused_rows=data['default_row'].get('hide_unused_rows', False),
            )

    @staticmethod
    def _setup_worksheet_paging(worksheet: Worksheet, data: dict):
        if 'h_pagebreaks' in data.keys():
            worksheet.set_h_pagebreaks(data['h_pagebreaks'])
        if 'v_pagebreaks' in data.keys():
            worksheet.set_v_pagebreaks(data['v_pagebreaks'])
        if 'outline_settings' in data.keys():
            worksheet.outline_settings(
                visible=data['outline_settings'].get('visible', True),
                symbols_below=data['outline_settings'].get('symbols_below', True),
                symbols_right=data['outline_settings'].get('symbols_right', True),
                auto_style=data['outline_settings'].get('auto_style', False),
            )

    @staticmethod
    def _setup_worksheet_panes(worksheet: Worksheet, data: dict):
        if 'split_panes' in data.keys():
            worksheet.split_panes(
                x=data['split_panes'].get('x', 0),
                y=data['split_panes'].get('y', 0),
                top_row=data['split_panes'].get('top_row', 0),
                left_col=data['split_panes'].get('left_col', 0),
            )
        if 'freeze_panes' in data.keys():
            worksheet.split_panes(
                x=data['split_panes'].get('x', 0),
                y=data['split_panes'].get('y', 0),
                top_row=data['split_panes'].get('top_row', 0),
                left_col=data['split_panes'].get('left_col', 0),
            )

    @staticmethod
    def _setup_worksheet_filters(worksheet: Worksheet, data: dict):
        if 'filter_column_lists' in data.keys():
            for f in data['filter_column_list']:
                worksheet.filter_column_list(
                    col=f.get('col', 0),
                    filters=f.get('filters', _EMPTY_LIST),
                )
        if 'filter_columns' in data.keys():
            for f in data['filter_column_list']:
                worksheet.filter_column(
                    col=f.get('col', 0),
                    criteria=f.get('criteria', _EMPTY_LIST),
                )
        if 'autofilter' in data.keys():
            if isinstance(data['autofilter'], str):
                worksheet.set_selection(data['autofilter'])
            else:
                worksheet.autofilter(
                    first_row=data['autofilter'].get('first_row', 0),
                    first_col=data['autofilter'].get('first_col', 0),
                    last_row=data['autofilter'].get('last_row', 0),
                    last_col=data['autofilter'].get('last_col', 0),
                )

    def _setup_worksheet_merge_ranges(self, worksheet: Worksheet, data: dict):
        if 'merge_ranges' in data.keys():
            for item in data['merge_ranges']:
                cell_format = self.formats.get(item.get('format', ''), None)
                if 'range' in item.keys():
                    worksheet.merge_range(
                        item['range'],
                        data=item.get('data', ''),
                        cell_format=cell_format,
                    )
                else:
                    worksheet.merge_range(
                        first_row=item.get('first_row', 0),
                        first_col=item.get('first_col', 0),
                        last_row=item.get('last_row', 0),
                        last_col=item.get('last_col', 0),
                        data=item.get('data', ''),
                        cell_format=cell_format,
                    )

    @staticmethod
    def _setup_worksheet_data_validations(worksheet: Worksheet, data: dict):
        if 'data_validations' in data.keys():
            for item in data['data_validations']:
                if 'range' in item.keys():
                    worksheet.data_validation(
                        item['range'],
                        options=item.get('options', ''),
                    )
                else:
                    worksheet.data_validation(
                        first_row=item.get('first_row', 0),
                        first_col=item.get('first_col', 0),
                        last_row=item.get('last_row', 0),
                        last_col=item.get('last_col', 0),
                        options=item.get('options', ''),
                    )

    def _setup_worksheet_conditional_formats(self, worksheet: Worksheet, data: dict):
        if 'conditional_formats' in data.keys():
            for item in data['conditional_formats']:
                if 'format' in item.keys():
                    item['format'] = self.formats.get(item['format'], None)
                if 'range' in item.keys():
                    worksheet.conditional_format(
                        item['range'],
                        options=item.get('options', ''),
                    )
                else:
                    worksheet.conditional_format(
                        first_row=item.get('first_row', 0),
                        first_col=item.get('first_col', 0),
                        last_row=item.get('last_row', 0),
                        last_col=item.get('last_col', 0),
                        options=item.get('options', ''),
                    )

    def _setup_worksheet_tables(self, worksheet: Worksheet, data: dict):
        if 'tables' in data.keys():
            for item in data['tables']:
                self._replace_nested_formats(
                    data=item,
                    keys=frozenset(['format', 'header_format']),
                )
                if 'range' in item.keys():
                    worksheet.add_table(
                        item['range'],
                        options=item.get('options', ''),
                    )
                else:
                    worksheet.add_table(
                        first_row=item.get('first_row', 0),
                        first_col=item.get('first_col', 0),
                        last_row=item.get('last_row', 0),
                        last_col=item.get('last_col', 0),
                        options=item.get('options', ''),
                    )

    @staticmethod
    def _setup_worksheet_sparklines(worksheet: Worksheet, data: dict):
        if 'sparklines' in data.keys():
            for item in data['sparklines']:
                if 'cell' in item.keys():
                    worksheet.add_sparkline(
                        item['cell'],
                        options=item.get('options', ''),
                    )
                else:
                    worksheet.add_sparkline(
                        row=item.get('row', 0),
                        column=item.get('column', 0),
                        options=item.get('options', ''),
                    )

    def _setup_worksheet_row_sizing(self, worksheet: Worksheet, data: dict):
        if 'row_pixels' in data.keys():
            for item in data['row_pixels']:
                if 'format' in item.keys():
                    item['format'] = self.formats.get(item['format'], None)
                worksheet.set_row_pixels(
                    row=item.get('row', 0),
                    height=item.get('height', 15),
                    cell_format=item.get('format', None),
                    options=item.get('options', None),
                )
        if 'rows' in data.keys():
            for item in data['rows']:
                if 'format' in item.keys():
                    item['format'] = self.formats.get(item['format'], None)
                worksheet.set_row(
                    row=item.get('row', 0),
                    height=item.get('height', 15),
                    cell_format=item.get('format', None),
                    options=item.get('options', None),
                )

    def _setup_worksheet_col_sizing(self, worksheet: Worksheet, data: dict):
        if 'column_pixels' in data.keys():
            for item in data['column_pixels']:
                if 'format' in item.keys():
                    item['format'] = self.formats.get(item['format'], None)
                first_col = item.get('first_col', item.get('col', 0))
                worksheet.set_column_pixels(
                    first_col=first_col,
                    last_col=item.get('last_col', first_col),
                    width=item.get('width', 70),
                    cell_format=item.get('format', None),
                    options=item.get('options', None),
                )
        if 'columns' in data.keys():
            for item in data['columns']:
                if 'format' in item.keys():
                    item['format'] = self.formats.get(item['format'], None)
                first_col = item.get('first_col', item.get('col', 0))
                worksheet.set_column(
                    first_col=first_col,
                    last_col=item.get('last_col', first_col),
                    width=item.get('width', 70),
                    cell_format=item.get('format', None),
                    options=item.get('options', None),
                )

    @staticmethod
    def _setup_worksheet_background(worksheet: Worksheet, data: dict):
        if 'background' in data.keys():
            if 'filename' in data['background'].keys():
                worksheet.set_background(
                    filename=data['background']['filename'],
                    is_byte_stream=False,
                )
            elif 'b64bytes' in data['background'].keys():
                bytes_io = _b64img2io(data['background']['b64bytes'])
                worksheet.set_background(
                    bytes_io,
                    is_byte_stream=True,
                )

    def _replace_nested_formats(self, data: dict, keys: frozenset[str]):
        if not isinstance(data, dict):
            return
        for key, value in data.items():
            if key in keys and isinstance(value, str):
                data[key] = self.formats.get(value, None)
            elif isinstance(value, dict):
                self._replace_nested_formats(value, keys)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._replace_nested_formats(item, keys)

    def build(self, data: dict):
        self._add_workbook_properties(data)
        self._add_workbook_options(data)
        self._add_workbook_definitions(data)

        for vba_project in data.get('vba_projects', _EMPTY_LIST):
            self.workbook.add_vba_project(
                vba_project=vba_project['project'],
                is_stream=vba_project.get('is_stream', False),
            )

        for name, format_data in data.get('formats', _EMPTY_DICT).items():
            self._add_format(name, format_data)

        for chart_data in data.get('charts', _EMPTY_LIST):
            self._add_chart(chart_data)

        for sheet_data in data.get('sheets', _EMPTY_LIST):
            if sheet_data.get('type', '') == 'chart':
                self._add_chartsheet(sheet_data)
            else:
                self._add_worksheet(sheet_data)

    @staticmethod
    def build_to_bytes(tmp_file: pathlib.Path, input_data: dict) -> bytes:
        options = input_data.get('options', None)
        tmp_file.unlink(missing_ok=True)
        with xlsxwriter.Workbook(str(tmp_file), options) as workbook:
            builder = WorkbookBuilder(workbook=workbook)
            builder.build(data=input_data)
        data = tmp_file.read_bytes()
        tmp_file.unlink()
        return data

    @staticmethod
    def is_xlsm(input_data: dict) -> bool:
        # Check if any VBA projects (macros) are included
        return len(input_data.get('vba_projects', _EMPTY_LIST)) > 0


class ExcelStep(Step):
    NAME = 'excel'

    def __init__(self, template, options: dict):
        super().__init__(template, options)

    def execute_first(self, context: dict) -> DocumentFile:
        return self.raise_exc(f'Step "{self.NAME}" cannot be first')

    def _get_data(self, document: DocumentFile) -> dict:
        if document.file_format != FileFormats.JSON:
            self.raise_exc(f'Step "{self.NAME}" requires JSON input'
                           f'with instructions from the previous step')
        data = _EMPTY_DICT
        try:
            data = json.loads(
                s=document.content.decode(encoding=document.encoding),
            )
            if not isinstance(data, dict):
                raise RuntimeError('Not a valid JSON object')
        except Exception as e:
            self.raise_exc(f'Failed to parse JSON for Excel: {str(e)}')
        return data

    def execute_follow(self, document: DocumentFile) -> DocumentFile:
        input_data = self._get_data(document)
        is_xlsm = WorkbookBuilder.is_xlsm(input_data)
        file_format = FileFormats.XLSX
        if is_xlsm:
            file_format = FileFormats.XLSM
        try:
            data = WorkbookBuilder.build_to_bytes(
                tmp_file=TMP_DIR / f'result.{file_format.file_extension}',
                input_data=input_data,
            )
            return DocumentFile(
                file_format=file_format,
                content=data,
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise FormatStepException(f'Failed to construct Excel document '
                                      f'due to: {str(e)}')


register_step(ExcelStep.NAME, ExcelStep)
