import pathlib
import jinja2
import shutil
import zipfile

from typing import Any

from ...consts import DEFAULT_ENCODING
from ...context import Context
from ...documents import DocumentFile, FileFormats
from .base import Step, register_step, TMP_DIR


class EnrichDocxStep(Step):
    NAME = 'enrich-docx'
    INPUT_FORMAT = FileFormats.DOCX
    OUTPUT_FORMAT = FileFormats.DOCX

    def _jinja_exception_msg(self, e: jinja2.exceptions.TemplateSyntaxError):
        lines = [
            'Failed loading Jinja2 template due to syntax error:',
            f'- {e.message}',
            f'- Filename: {e.name}',
            f'- Line number: {e.lineno}',
        ]
        return '\n'.join(lines)

    def __init__(self, template, options: dict):
        super().__init__(template, options)
        self.rewrites = {k[8:]: v
                         for k, v in options.items()
                         if k.startswith('rewrite:')}
        # TODO: shared part with Jinja2Step
        try:
            self.j2_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(searchpath=template.template_dir),
                extensions=['jinja2.ext.do'],
            )
            self._add_j2_enhancements()
        except jinja2.exceptions.TemplateSyntaxError as e:
            self.raise_exc(self._jinja_exception_msg(e))
        except Exception as e:
            self.raise_exc(f'Failed loading Jinja2 template: {e}')

    def _add_j2_enhancements(self):
        # TODO: shared part with Jinja2Step
        from ..filters import filters
        from ..tests import tests
        from ...model.http import RequestsWrapper
        self.j2_env.filters.update(filters)
        self.j2_env.tests.update(tests)
        template_cfg = Context.get().app.cfg.templates.get_config(
            self.template.template_id,
        )
        if template_cfg is not None:
            global_vars = {'secrets': template_cfg.secrets}  # type: dict[str, Any]
            if template_cfg.requests.enabled:
                global_vars['requests'] = RequestsWrapper(
                    template_cfg=template_cfg,
                )
            self.j2_env.globals.update(global_vars)

    def _render_rewrite(self, rewrite_template: str, context: dict) -> str:
        try:
            j2_template = self.j2_env.get_template(rewrite_template)
            return j2_template.render(ctx=context)
        except jinja2.exceptions.TemplateSyntaxError as e:
            self.raise_exc(self._jinja_exception_msg(e))
        except Exception as e:
            self.raise_exc(f'Failed loading Jinja2 template: {e}')
        return ''

    def _static_rewrite(self, rewrite_file: str) -> str:
        try:
            path = self.template.template_dir / rewrite_file  # type: pathlib.Path
            return path.read_text(encoding=DEFAULT_ENCODING)
        except Exception as e:
            self.raise_exc(f'Failed loading Jinja2 template: {e}')
        return ''

    def _get_rewrite(self, rewrite: str, context: dict) -> str:
        if rewrite.startswith('static:'):
            return self._static_rewrite(rewrite[7:])
        elif rewrite.startswith('render:'):
            return self._render_rewrite(rewrite[7:], context)
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
            content = self._get_rewrite(rewrite, context)
            target = docx_dir / target_file
            target.write_text(content, encoding=DEFAULT_ENCODING)

        with zipfile.ZipFile(new_docx_file, mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target_docx:
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
