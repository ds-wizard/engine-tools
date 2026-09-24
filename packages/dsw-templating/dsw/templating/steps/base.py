from __future__ import annotations

import typing

from ..locales import RenderContext


if typing.TYPE_CHECKING:
    from gettext import NullTranslations

    from ..documents import DocumentFile


class FormatStepError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class Step:
    NAME = ''
    OPTION_EXTRAS = 'extras'

    def __init__(self, template, options: dict[str, str]):
        self.template = template
        self.options = options

        extras_str: str = self.options.get(self.OPTION_EXTRAS, '')
        self.extras: set[str] = set(extras_str.split(','))
        self.render_ctx = RenderContext.null()

    @staticmethod
    def initialize_step():
        pass

    def requires_via_extras(self, requirement: str) -> bool:
        return requirement in self.extras

    def before_render(self, render_ctx: RenderContext) -> None:
        self.render_ctx = render_ctx

    @property
    def translations(self) -> NullTranslations:
        return self.render_ctx.translations

    @property
    def language(self) -> str | None:
        return self.render_ctx.language

    def gettext(self, message: str) -> str:
        return self.translations.gettext(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        return self.translations.ngettext(singular, plural, n)

    def pgettext(self, context: str, message: str) -> str:
        return self.translations.pgettext(context, message)

    def execute_first(self, context: dict) -> DocumentFile:
        return self.raise_exc('Called execute_follow on Step class')

    def execute_follow(self, document: DocumentFile, context: dict) -> DocumentFile:
        return self.raise_exc('Called execute_follow on Step class')

    def raise_exc(self, message: str):
        raise FormatStepError(message)


STEPS: dict[str, type[Step]] = {}


def register_step(name: str, step_class: type[Step]):
    step_class.initialize_step()
    STEPS[name.lower()] = step_class


def create_step(template, name: str, options: dict) -> Step:
    name = name.lower()
    if name not in STEPS:
        raise KeyError(f'Unknown step name "{name}"')
    return STEPS[name](template, options)
