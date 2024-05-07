from ...consts import DEFAULT_ENCODING
from ...context import Context
from ...conversions import Pandoc, RdfLibConvert
from ...documents import DocumentFile, FileFormats
from .base import Step, register_step


class WeasyPrintStep(Step):
    NAME = 'weasyprint'
    INPUT_FORMAT = FileFormats.HTML
    OUTPUT_FORMAT = FileFormats.PDF

    def __init__(self, template, options: dict):
        import weasyprint
        super().__init__(template, options)
        # PDF options
        self.wp_options = weasyprint.DEFAULT_OPTIONS
        self.wp_update_options(options)
        self.wp_zoom = float(options.get('pdf.zoom', '1'))

    def wp_update_options(self, options: dict):
        optimize_size = tuple(options.get('render.optimize_size', 'fonts').split(','))
        self.wp_options.update({
            'pdf_identifier': options.get('pdf.identifier', 'false').lower() == 'true',
            'pdf_variant': options.get('pdf.variant', None),
            'pdf_version': options.get('pdf.version', None),
            'pdf_forms': options.get('render.forms', 'false').lower() == 'true',
            'uncompressed_pdf': options.get('pdf.uncompressed', 'false').lower() == 'true',
            'custom_metadata': options.get('pdf.custom_metadata', 'false').lower() == 'true',
            'presentational_hints': options.get('render.presentational_hints', 'false').lower() == 'true',
            'optimize_images': 'images' in optimize_size,
            'jpeg_quality': int(options.get('render.jpeg_quality', '95')),
            'dpi': int(options.get('render.dpi', '96')),
        })

    def execute_first(self, context: dict) -> DocumentFile:
        return self.raise_exc(f'Step "{self.NAME}" cannot be first')

    def execute_follow(self, document: DocumentFile, context: dict) -> DocumentFile:
        import weasyprint
        if document.file_format != FileFormats.HTML:
            self.raise_exc(f'WeasyPrint does not support {document.file_format.name} format as input')
        file_uri = self.template.template_dir / '_file.html'
        wp_html = weasyprint.HTML(
            string=document.content.decode(DEFAULT_ENCODING),
            encoding=DEFAULT_ENCODING,
            media_type='print',
            base_url=file_uri.as_uri(),
        )
        data = wp_html.write_pdf(
            zoom=self.wp_zoom,
            font_config=None,  # not used now (should be in CSS)
            counter_style=None,  # not used now (should be in CSS)
            options=self.options,
        )
        return DocumentFile(
            file_format=self.OUTPUT_FORMAT,
            content=data,
        )

    @property
    def produces_only_pdf(self):
        return True


class PandocStep(Step):
    NAME = 'pandoc'

    INPUT_FORMATS = frozenset([
        FileFormats.DOCX,
        FileFormats.EPUB,
        FileFormats.HTML,
        FileFormats.LaTeX,
        FileFormats.Markdown,
        FileFormats.ODT,
        FileFormats.RST,
    ])
    OUTPUT_FORMATS = frozenset([
        FileFormats.ADoc,
        FileFormats.DocBook4,
        FileFormats.DocBook5,
        FileFormats.DOCX,
        FileFormats.EPUB,
        FileFormats.HTML,
        FileFormats.LaTeX,
        FileFormats.Markdown,
        FileFormats.ODT,
        FileFormats.RST,
        FileFormats.RTF,
    ])
    OUTPUT_ENCODINGS = {
        FileFormats.ADoc: DEFAULT_ENCODING,
        FileFormats.DocBook4: None,
        FileFormats.DocBook5: None,
        FileFormats.DOCX: None,
        FileFormats.EPUB: None,
        FileFormats.HTML: DEFAULT_ENCODING,
        FileFormats.LaTeX: DEFAULT_ENCODING,
        FileFormats.Markdown: DEFAULT_ENCODING,
        FileFormats.ODT: None,
        FileFormats.RST: DEFAULT_ENCODING,
        FileFormats.RTF: None,
    }

    OPTION_FROM = 'from'
    OPTION_TO = 'to'
    OPTION_FILTERS = 'filters'
    OPTION_TEMPLATE = 'template'

    def __init__(self, template, options: dict):
        super().__init__(template, options)
        self.input_format = FileFormats.get(options[self.OPTION_FROM])
        self.output_format = FileFormats.get(options[self.OPTION_TO])
        if self.input_format not in self.INPUT_FORMATS:
            self.raise_exc(f'Unknown input format "{self.input_format.name}"')
        if self.output_format not in self.OUTPUT_FORMATS:
            self.raise_exc(f'Unknown output format "{self.output_format.name}"')
        self.pandoc = Pandoc(
            config=Context.get().app.cfg,
            filter_names=self._extract_filter_names(options.get(self.OPTION_FILTERS, '')),
            template_name=options.get(self.OPTION_TEMPLATE, None)
        )

    @staticmethod
    def _extract_filter_names(filters: str) -> list[str]:
        names = list()
        for name in filters.split(','):
            name = name.strip()
            if name:
                names.append(name)
        return names

    def execute_first(self, context: dict) -> DocumentFile:
        return self.raise_exc(f'Step "{self.NAME}" cannot be first')

    def execute_follow(self, document: DocumentFile, context: dict) -> DocumentFile:
        if document.file_format != self.input_format:
            self.raise_exc(f'Unexpected input {document.file_format.name} as input for pandoc')
        data = self.pandoc(
            source_format=self.input_format,
            target_format=self.output_format,
            data=document.content,
            metadata=self.options,
            workdir=str(self.template.template_dir),
        )
        return DocumentFile(
            file_format=self.output_format,
            content=data,
            encoding=self.OUTPUT_ENCODINGS[self.output_format],
        )


class RdfLibConvertStep(Step):
    NAME = 'rdflib-convert'

    INPUT_FORMATS = [
        FileFormats.RDF_XML,
        FileFormats.N3,
        FileFormats.NTRIPLES,
        FileFormats.TURTLE,
        FileFormats.TRIG,
        FileFormats.JSONLD,
    ]

    OUTPUT_FORMATS = INPUT_FORMATS

    OPTION_FROM = 'from'
    OPTION_TO = 'to'

    def __init__(self, template, options: dict):
        super().__init__(template, options)
        self.rdflib_convert = RdfLibConvert(config=Context.get().app.cfg)
        self.input_format = FileFormats.get(options[self.OPTION_FROM])
        self.output_format = FileFormats.get(options[self.OPTION_TO])
        if self.input_format not in self.INPUT_FORMATS:
            self.raise_exc(f'Unknown input format "{self.input_format.name}"')
        if self.output_format not in self.OUTPUT_FORMATS:
            self.raise_exc(f'Unknown output format "{self.output_format.name}"')

    def execute_first(self, context: dict) -> DocumentFile:
        return self.raise_exc(f'Step "{self.NAME}" cannot be first')

    def execute_follow(self, document: DocumentFile, context: dict) -> DocumentFile:
        if document.file_format != self.input_format:
            self.raise_exc(f'Unexpected input {document.file_format.name} '
                           f'as input for rdflib-convert '
                           f'(expecting {self.input_format.name})')
        data = self.rdflib_convert(
            self.input_format, self.output_format, document.content, self.options
        )
        return DocumentFile(
            file_format=self.output_format,
            content=data,
            encoding=DEFAULT_ENCODING,
        )


register_step(PandocStep.NAME, PandocStep)
register_step(RdfLibConvertStep.NAME, RdfLibConvertStep)
register_step(WeasyPrintStep.NAME, WeasyPrintStep)
