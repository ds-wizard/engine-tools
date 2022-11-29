from ...context import Context
from ...conversions import Pandoc, WkHtmlToPdf, RdfLibConvert
from ...documents import DocumentFile, FileFormats
from .base import Step, register_step


class WkHtmlToPdfStep(Step):
    NAME = 'wkhtmltopdf'
    INPUT_FORMAT = FileFormats.HTML
    OUTPUT_FORMAT = FileFormats.PDF

    def __init__(self, template, options: dict):
        super().__init__(template, options)
        self.wkhtmltopdf = WkHtmlToPdf(config=Context.get().app.cfg)

    def execute_first(self, context: dict) -> DocumentFile:
        return self.raise_exc(f'Step "{self.NAME}" cannot be first')

    def execute_follow(self, document: DocumentFile, context: dict) -> DocumentFile:
        if document.file_format != FileFormats.HTML:
            self.raise_exc(f'WkHtmlToPdf does not support {document.file_format.name} format as input')
        data = self.wkhtmltopdf(
            source_format=self.INPUT_FORMAT,
            target_format=self.OUTPUT_FORMAT,
            data=document.content,
            metadata=self.options,
            workdir=str(self.template.template_dir),
        )
        return DocumentFile(self.OUTPUT_FORMAT, data)


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

    OPTION_FROM = 'from'
    OPTION_TO = 'to'

    def __init__(self, template, options: dict):
        super().__init__(template, options)
        self.pandoc = Pandoc(config=Context.get().app.cfg)
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
            self.raise_exc(f'Unexpected input {document.file_format.name} as input for pandoc')
        data = self.pandoc(
            source_format=self.input_format,
            target_format=self.output_format,
            data=document.content,
            metadata=self.options,
            workdir=str(self.template.template_dir),
        )
        return DocumentFile(self.output_format, data)


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
        return DocumentFile(self.output_format, data)


register_step(WkHtmlToPdfStep.NAME, WkHtmlToPdfStep)
register_step(PandocStep.NAME, PandocStep)
register_step(RdfLibConvertStep.NAME, RdfLibConvertStep)
