from __future__ import annotations

import datetime
import json
import typing
import zoneinfo

import jinja2
import jinja2.exceptions

from dsw.models.document_context.graph import ProjectFile

from ..consts import DEFAULT_ENCODING, JINJA_EXTENSIONS, JINJA_I18N_TRIMMED
from ..documents import DocumentFile, FileFormat, FileFormats
from ..exceptions import optional
from ..filters import filters
from ..http import RequestsWrapper
from ..tests import tests
from ..urls import UrlPolicy
from ..utils import JinjaEnvironment
from .base import Step, register_step


if typing.TYPE_CHECKING:
    from gettext import NullTranslations

    from ..locales import RenderContext


class JSONStep(Step):
    NAME = 'json'
    OUTPUT_FORMAT = FileFormats.JSON

    def execute_first(self, context: dict) -> DocumentFile:
        return DocumentFile(
            self.OUTPUT_FORMAT,
            json.dumps(context, indent=2, sort_keys=True).encode(DEFAULT_ENCODING),
            DEFAULT_ENCODING,
        )

    def execute_follow(self, document: DocumentFile, context: dict) -> DocumentFile:
        return self.raise_exc(f'Step "{self.NAME}" cannot process other files')


class JinjaPoweredStep(Step):
    OPTION_JINJA_EXT = 'jinja-ext'

    def __init__(self, template, options):
        super().__init__(template, options)
        self.jinja_ext = frozenset(
            opt.strip() for opt in self.options.get(self.OPTION_JINJA_EXT, '').split(',')
        )

        try:
            self.j2_env = JinjaEnvironment(
                loader=jinja2.FileSystemLoader(searchpath=template.template_dir),
                extensions=[
                    *JINJA_EXTENSIONS,
                    'jinja2.ext.i18n',
                ],
                autoescape=True,
            )
            if 'debug' in self.jinja_ext:
                self.j2_env.add_extension('jinja2.ext.debug')
            self._apply_policies(options)
            self._add_j2_enhancements()
            self._install_translations(None)

            self.template.plugins.hook.enrich_jinja_env(
                jinja_env=self.j2_env,
                options=options,
            )
        except jinja2.exceptions.TemplateSyntaxError as e:
            self.raise_exc(self._jinja_exception_msg(e))
        except Exception as e:
            self.raise_exc(f'Failed loading Jinja2 template: {e}')

    def _jinja_exception_msg(self, e: jinja2.exceptions.TemplateSyntaxError):
        lines = [
            'Failed loading Jinja2 template due to syntax error:',
            f'- {e.message}',
            f'- Filename: {e.name}',
            f'- Line number: {e.lineno}',
        ]
        return '\n'.join(lines)

    def _apply_policies(self, options: dict):
        # https://jinja.palletsprojects.com/en/3.0.x/api/#policies
        policies: dict[str, typing.Any] = {
            'policy.urlize.target': '_blank',
            'ext.i18n.trimmed': JINJA_I18N_TRIMMED,
            'json.dumps_kwargs': {
                'allow_nan': False,
                'ensure_ascii': False,
            },
        }
        if 'policy.truncate.leeway' in options:
            policies['truncate.leeway'] = options['policy.truncate.leeway']
        if 'policy.urlize.rel' in options:
            policies['urlize.rel'] = options['policy.urlize.rel']
        if 'policy.urlize.target' in options:
            policies['urlize.target'] = options['policy.urlize.target']
        if 'policy.urlize.extra_schemes' in options:
            policies['urlize.extra_schemes'] = options['policy.urlize.extra_schemes'].split(',')
        for key in options:
            if not key.startswith('policy.json.dumps_kwargs.'):
                continue
            name = key[len('policy.json.dumps_kwargs.'):]
            if name in ['allow_nan', 'skipkeys', 'sort_keys', 'ensure_ascii', 'check_circular']:
                policies['json.dumps_kwargs'][name] = options[key].lower() == 'true'
            else:
                policies['json.dumps_kwargs'][name] = options[key]
        self.j2_env.policies.update(policies)

    def before_render(self, render_ctx: RenderContext) -> None:
        super().before_render(render_ctx)
        self._install_translations(render_ctx.translations)

    def _install_translations(self, translations: NullTranslations | None):
        # https://jinja.palletsprojects.com/en/3.1.x/extensions/#i18n-extension
        if translations is None:
            install_null = getattr(self.j2_env, 'install_null_translations', None)
            if callable(install_null):
                install_null(newstyle=True)
            return
        install = getattr(self.j2_env, 'install_gettext_translations', None)
        if callable(install):
            install(translations, newstyle=True)

    @property
    def _j2_filters(self) -> typing.MutableMapping[str, typing.Any]:
        return typing.cast(
            'typing.MutableMapping[str, typing.Any]',
            self.j2_env.filters,
        )

    @property
    def _j2_tests(self) -> typing.MutableMapping[str, typing.Any]:
        return typing.cast(
            'typing.MutableMapping[str, typing.Any]',
            self.j2_env.tests,
        )

    @property
    def _j2_globals(self) -> typing.MutableMapping[str, typing.Any]:
        return typing.cast(
            'typing.MutableMapping[str, typing.Any]',
            self.j2_env.globals,
        )

    def _add_j2_enhancements(self):
        self._j2_filters.update(filters)
        self._j2_tests.update(tests)
        settings = self.template.settings
        template_cfg = settings.template
        self._j2_globals.update({
            'rdflib': optional('rdflib', 'rdf'),
            'json': json,
            'datetime': datetime,
            'zoneinfo': zoneinfo,
        })
        if template_cfg is not None:
            global_vars: dict[str, typing.Any] = {'secrets': template_cfg.secrets}
            if template_cfg.requests.enabled:
                global_vars['requests'] = RequestsWrapper(
                    settings=template_cfg.requests,
                    policy=UrlPolicy(settings.security),
                )
            self.j2_env.globals.update(global_vars)


class Jinja2Step(JinjaPoweredStep):
    NAME = 'jinja'
    DEFAULT_FORMAT = FileFormats.HTML

    OPTION_ROOT_FILE = 'template'
    OPTION_CONTENT_TYPE = 'content-type'
    OPTION_EXTENSION = 'extension'

    def __init__(self, template, options: dict):
        super().__init__(template, options)
        self.root_file = self.options[self.OPTION_ROOT_FILE]
        self.content_type = self.options.get(self.OPTION_CONTENT_TYPE,
                                             self.DEFAULT_FORMAT.content_type)
        self.extension = self.options.get(self.OPTION_EXTENSION,
                                          self.DEFAULT_FORMAT.file_extension)

        self.output_format = FileFormat(self.extension, self.content_type, self.extension)
        try:
            self.j2_root_template = self.j2_env.get_template(self.root_file)
        except jinja2.exceptions.TemplateSyntaxError as e:
            self.raise_exc(self._jinja_exception_msg(e))
        except Exception as e:
            self.raise_exc(f'Failed loading Jinja2 template: {e}')

    def _execute(self, **jinja_args):
        def assets(source: str | ProjectFile | dict):
            if isinstance(source, ProjectFile):
                return self.template.fetch_project_file(source)
            if isinstance(source, dict):
                return self.template.fetch_project_file_dict(source)
            if isinstance(source, str):
                return self.template.fetch_asset(source)
            return None

        jinja_args.update({
            'assets': assets,
        })

        content = b''
        try:
            content = self.j2_root_template.render(**jinja_args).encode(DEFAULT_ENCODING)
        except jinja2.exceptions.TemplateSyntaxError as e:
            self.raise_exc(self._jinja_exception_msg(e))
        except jinja2.exceptions.TemplateRuntimeError as e:
            self.raise_exc(f'Failed rendering Jinja2 template due to'
                           f' {type(e).__name__}\n'
                           f'- {str(e)}')
        return DocumentFile(
            file_format=self.output_format,
            content=content,
            encoding=DEFAULT_ENCODING,
        )

    def execute_first(self, context: dict) -> DocumentFile:
        return self._execute(ctx=context)

    def execute_follow(self, document: DocumentFile, context: dict) -> DocumentFile:
        return self._execute(ctx=context, document=document)


register_step(JSONStep.NAME, JSONStep)
register_step(Jinja2Step.NAME, Jinja2Step)
