import json
import typing

import gettext
import jinja2
import jinja2.exceptions
import jinja2.sandbox
import rdflib

from ...consts import DEFAULT_ENCODING
from ...context import Context
from ...documents import DocumentFile, FileFormat, FileFormats
from ...model.http import RequestsWrapper
from ..filters import filters
from ..tests import tests
from .base import Step, register_step


class JSONStep(Step):
    NAME = 'json'
    OUTPUT_FORMAT = FileFormats.JSON

    def execute_first(self, context: dict) -> DocumentFile:
        return DocumentFile(
            self.OUTPUT_FORMAT,
            json.dumps(context, indent=2, sort_keys=True).encode(DEFAULT_ENCODING),
            DEFAULT_ENCODING
        )

    def execute_follow(self, document: DocumentFile, context: dict) -> DocumentFile:
        return self.raise_exc(f'Step "{self.NAME}" cannot process other files')


class JinjaEnvironment(jinja2.sandbox.SandboxedEnvironment):

    def is_safe_attribute(self, obj: typing.Any, attr: str, value: typing.Any) -> bool:
        if attr in ['os', 'subprocess', 'eval', 'exec', 'popen', 'system']:
            return False
        if attr == '__setitem__' and isinstance(obj, dict):
            return True
        return super().is_safe_attribute(obj, attr, value)


class JinjaPoweredStep(Step):
    OPTION_JINJA_EXT = 'jinja-ext'
    OPTION_I18N_DIR = 'i18n-dir'
    OPTION_I18N_DOMAIN = 'i18n-domain'
    OPTION_I18N_LANG = 'i18n-lang'

    def __init__(self, template, options):
        super().__init__(template, options)
        self.jinja_ext = frozenset(
            map(lambda x: x.strip(), self.options.get(self.OPTION_JINJA_EXT, '').split(','))
        )
        self.i18n_dir = self.options.get(self.OPTION_I18N_DIR, None)
        self.i18n_domain = self.options.get(self.OPTION_I18N_DOMAIN, 'default')
        self.i18n_lang = self.options.get(self.OPTION_I18N_LANG, None)

        try:
            self.j2_env = JinjaEnvironment(
                loader=jinja2.FileSystemLoader(searchpath=template.template_dir),
                extensions=[
                    'jinja2.ext.do',
                    'jinja2.ext.loopcontrols',
                ],
            )
            if 'i18n' in self.jinja_ext:
                self._add_j2_i18n(template)
            if 'debug' in self.jinja_ext:
                self.j2_env.add_extension('jinja2.ext.debug')
            self._apply_policies(options)
            self._add_j2_enhancements()

            Context.get().app.pm.hook.enrich_jinja_env(
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
            values = options['policy.urlize.extra_schemes'].split(',')
            policies['truncate.leeway'] = values
        if 'policy.ext.i18n.trimmed' in options:
            value = options['policy.ext.i18n.trimmed'].lower() == 'true'
            policies['ext.i18n.trimmed'] = value
        for key in options:
            if not key.startswith('policy.json.dumps_kwargs.'):
                continue
            name = key[len('policy.json.dumps_kwargs.'):]
            if name in ['allow_nan', 'skipkeys', 'sort_keys', 'ensure_ascii', 'check_circular']:
                policies['json.dumps_kwargs'][name] = options[key].lower() == 'true'
            else:
                policies['json.dumps_kwargs'][name] = options[key]
        self.j2_env.policies.update(policies)

    def _add_j2_i18n(self, template):
        # https://jinja.palletsprojects.com/en/3.1.x/extensions/#i18n-extension
        self.j2_env.add_extension('jinja2.ext.i18n')
        if self.i18n_dir is not None and self.i18n_lang is not None:
            locale_path = template.template_dir / self.i18n_dir
            translations = gettext.translation(
                domain=self.i18n_domain,
                localedir=locale_path,
                languages=map(lambda x: x.strip(), self.i18n_lang.split(',')),
            )
            # pylint: disable-next=no-member
            self.j2_env.install_gettext_translations(translations, newstyle=True)  # type: ignore
        else:
            # pylint: disable-next=no-member
            self.j2_env.install_null_translations(newstyle=True)  # type: ignore

    def _add_j2_enhancements(self):
        self.j2_env.filters.update(filters)
        self.j2_env.tests.update(tests)
        template_cfg = Context.get().app.cfg.templates.get_config(
            self.template.template_id,
        )
        self.j2_env.globals.update({'rdflib': rdflib, 'json': json})
        if template_cfg is not None:
            global_vars: dict[str, typing.Any] = {'secrets': template_cfg.secrets}
            if template_cfg.requests.enabled:
                global_vars['requests'] = RequestsWrapper(
                    template_cfg=template_cfg,
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
        def asset_fetcher(file_name):
            return self.template.fetch_asset(file_name)

        def asset_path(file_name):
            return self.template.asset_path(file_name)

        jinja_args.update({
            'assets': asset_fetcher,
            'asset_path': asset_path,
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
