import pathlib

from ...documents import DocumentFile


TMP_DIR = pathlib.Path('/tmp/docworker')


class FormatStepException(Exception):

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
        extras_str = self.options.get(self.OPTION_EXTRAS, '')  # type: str
        self.extras = set(extras_str.split(','))  # type: set[str]

    def requires_via_extras(self, requirement: str) -> bool:
        return requirement in self.extras

    def execute_first(self, context: dict) -> DocumentFile:
        return self.raise_exc('Called execute_follow on Step class')

    def execute_follow(self, document: DocumentFile, context: dict) -> DocumentFile:
        return self.raise_exc('Called execute_follow on Step class')

    def raise_exc(self, message: str):
        raise FormatStepException(message)

    @property
    def produces_only_pdf(self):
        return False


STEPS = dict()


def register_step(name: str, step_class: type):
    STEPS[name.lower()] = step_class


def create_step(template, name: str, options: dict) -> Step:
    name = name.lower()
    if name not in STEPS:
        raise KeyError(f'Unknown step name "{name}"')
    return STEPS[name](template, options)
