import pathlib
import shutil
import zipfile

import jinja2

from ...consts import DEFAULT_ENCODING
from ...documents import DocumentFile, FileFormats
from .base import register_step, TMP_DIR
from .template import JinjaPoweredStep


class EnrichDocxStep(JinjaPoweredStep):
    NAME = 'enrich-docx'
    INPUT_FORMAT = FileFormats.DOCX
    OUTPUT_FORMAT = FileFormats.DOCX

    def __init__(self, template, options: dict):
        super().__init__(template, options)
        self.rewrites = {k[8:]: v
                         for k, v in options.items()
                         if k.startswith('rewrite:')}

    def _render_rewrite(self, rewrite_template: str, context: dict,
                        existing_content: str | None) -> str:
        try:
            j2_template = self.j2_env.get_template(rewrite_template)
            return j2_template.render(
                ctx=context,
                content=existing_content,
            )
        except jinja2.exceptions.TemplateSyntaxError as e:
            self.raise_exc(self._jinja_exception_msg(e))
        except Exception as e:
            self.raise_exc(f'Failed loading Jinja2 template: {e}')
        return ''

    def _static_rewrite(self, rewrite_file: str) -> str:
        try:
            path: pathlib.Path = self.template.template_dir / rewrite_file
            return path.read_text(encoding=DEFAULT_ENCODING)
        except Exception as e:
            self.raise_exc(f'Failed loading Jinja2 template: {e}')
        return ''

    def _get_rewrite(self, rewrite: str, context: dict,
                     existing_content: str | None) -> str:
        if rewrite.startswith('static:'):
            return self._static_rewrite(rewrite[7:])
        if rewrite.startswith('render:'):
            return self._render_rewrite(rewrite[7:], context, existing_content)
        return ''

    def execute_first(self, context: dict) -> DocumentFile:
        return self.raise_exc(f'Step "{self.NAME}" cannot be first')

    def execute_follow(self, document: DocumentFile, context: dict) -> DocumentFile:
        if document.file_format != self.INPUT_FORMAT:
            self.raise_exc(f'Step "{self.NAME}" requires DOCX input')

        docx_file = TMP_DIR / 'original_file.docx'
        docx_file.write_bytes(document.content)
        new_docx_file = TMP_DIR / 'enriched_file.docx'
        docx_dir = TMP_DIR / 'enriched_file_docx'

        with zipfile.ZipFile(docx_file, mode='r') as source_docx:
            source_docx.extractall(docx_dir)

        for target_file, rewrite in self.rewrites.items():
            target = docx_dir / target_file
            existing_content = None
            if target.is_file() and target.exists():
                existing_content = target.read_text(encoding=DEFAULT_ENCODING)
            content = self._get_rewrite(rewrite, context, existing_content)
            target.write_text(content, encoding=DEFAULT_ENCODING)

        with zipfile.ZipFile(new_docx_file, mode='w',
                             compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9) as target_docx:
            for path in docx_dir.rglob('*'):
                if path.is_file():
                    target_docx.write(path, path.relative_to(docx_dir))

        new_content = new_docx_file.read_bytes()

        docx_file.unlink(missing_ok=True)
        new_docx_file.unlink(missing_ok=True)
        shutil.rmtree(docx_dir, ignore_errors=True)

        return DocumentFile(
            file_format=self.OUTPUT_FORMAT,
            content=new_content,
        )


register_step(EnrichDocxStep.NAME, EnrichDocxStep)
