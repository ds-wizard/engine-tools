import collections

from dsw.tdk.model import Template
from dsw.tdk.validation import TemplateValidator


def load(**extra) -> Template:
    data = collections.OrderedDict({
        'organizationId': 'test',
        'templateId': 'example',
        'version': '1.0.0',
        'name': 'Test template',
        'description': 'Testing',
        'license': 'Apache-2.0',
        'readme': 'Readme',
        'metamodelVersion': '18.3',
        'formats': [],
        **extra,
    })
    return Template.load_local(data)


def errors_for(template: Template, field: str) -> list[str]:
    return [e.message for e in TemplateValidator.collect_errors(template)
            if e.field_name == field]


def test_language_defaults_when_absent():
    assert load().language == 'en'


def test_language_is_used_when_given():
    assert load(language='cs').language == 'cs'


def test_empty_language_is_not_silently_defaulted():
    template = load(language='')
    assert template.language == ''
    assert errors_for(template, 'language') != []


def test_new_template_defaults_to_en():
    assert Template().language == 'en'
