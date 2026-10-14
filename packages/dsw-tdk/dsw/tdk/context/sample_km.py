"""The sample knowledge model of `generate-context --sample` (``samples/sample-km.json``).

It is small but covers every question type, value type and validation kind, file questions with
limits, follow-ups, nested lists and item select, phases, tags, metrics with measures, references
and experts, so generated contexts exercise every part of a template. The JSON file is built from
:func:`build_sample_km` (``python -m dsw.tdk.context.sample_km``); a test keeps the two in sync.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import typing
import uuid

from dsw.models.knowledge_model import common as v
from dsw.models.knowledge_model.builder import KnowledgeModelBuilder


if typing.TYPE_CHECKING:
    from dsw.models.knowledge_model.package import KnowledgeModelBundle


SAMPLE_KM_PATH = pathlib.Path(__file__).parent.parent / 'samples' / 'sample-km.json'
SAMPLE_KM_ID = 'tdk.sample'
SAMPLE_KM_VERSION = '1.0.0'

_CREATED_AT = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)


def _uuids():
    counter = iter(range(1, 1_000_000))
    return lambda: uuid.uuid5(uuid.NAMESPACE_URL, f'https://tdk.example.org/sample-km/{next(counter)}')


def build_sample_km() -> KnowledgeModelBuilder:
    b = KnowledgeModelBuilder(uuid_factory=_uuids())
    planning = b.phase('Before submitting the proposal')
    running = b.phase('Before finishing the project')
    b.phase('After finishing the project')
    findability = b.metric('Findability', abbreviation='F')
    reusability = b.metric('Reusability', abbreviation='R')
    horizon = b.tag('Horizon Europe', color='#f1c40f')
    sensitive = b.tag('Sensitive data', color='#c0392b')
    guide = b.resource_collection('Guidance')
    page = guide.page('Licenses', 'Choose an open license where you can.')
    search = b.api_integration('Repository search', request_url='https://repo.example.org/search?q=${q}',
                               response_list_field='items', response_item_template='{{item.name}}')

    # chapter 1: options with follow-ups, multi-choice, references, experts, metrics
    project = b.chapter('Project', text='About the **project**.')
    reuse = project.options_question('Will you reuse existing data?', required_phase=planning,
                                     tags=[horizon], text='Data *already* collected by others.')
    reuse.url_reference('https://www.go-fair.org/fair-principles/', 'FAIR principles')
    reuse.resource_page_reference(page)
    reuse.expert('Data Steward', 'steward@example.org')
    yes = reuse.answer('Yes', metric_measures=[(findability, 1.0, 1.0), (reusability, 1.0, 1.0)])
    yes.value_question('Which data will you reuse?', value_type='TextQuestionValueType')
    which = yes.options_question('Is the data openly available?')
    which.answer('Yes', metric_measures=[(reusability, 1.0, 0.5)])
    restricted = which.answer('No', advice='Check the license before you reuse it.')
    restricted.value_question('Who grants access?', required_phase=running)
    reuse.answer('No', metric_measures=[(reusability, 0.0, 1.0)])
    topics = project.multi_choice_question('Which topics does the project cover?', tags=[sensitive])
    for label in ('Health', 'Climate', 'Social science', 'Engineering'):
        topics.choice(label)
    empty_options = project.options_question('An options question without answers')
    empty_options.cross_reference(reuse, 'See the reuse question.')

    # chapter 2: every value type and validation kind
    values = b.chapter('Values')
    values.value_question('Acronym', validations=[
        v.MinLengthQuestionValidation(value=2), v.MaxLengthQuestionValidation(value=12)])
    values.value_question('Abstract', value_type='TextQuestionValueType')
    values.value_question('Budget in EUR', value_type='NumberQuestionValueType', validations=[
        v.MinNumberQuestionValidation(value=0), v.MaxNumberQuestionValidation(value=1000000)])
    values.value_question('Start date', value_type='DateQuestionValueType', validations=[
        v.FromDateQuestionValidation(value='2025-01-01'),
        v.ToDateQuestionValidation(value='2030-12-31')])
    values.value_question('Kick-off meeting', value_type='DateTimeQuestionValueType', validations=[
        v.FromDateTimeQuestionValidation(value='2025-01-01T08:00:00Z'),
        v.ToDateTimeQuestionValidation(value='2030-12-31T18:00:00Z')])
    values.value_question('Daily stand-up', value_type='TimeQuestionValueType', validations=[
        v.FromTimeQuestionValidation(value='08:00'), v.ToTimeQuestionValidation(value='12:00')])
    values.value_question('Contact email', value_type='EmailQuestionValueType')
    values.value_question('Project website', value_type='UrlQuestionValueType', validations=[
        v.DomainQuestionValidation(value='example.org')])
    values.value_question('Project colour', value_type='ColorQuestionValueType')
    values.value_question('PI ORCID', validations=[v.OrcidQuestionValidation()])
    values.value_question('Data DOI', validations=[v.DoiQuestionValidation()])
    values.value_question('Grant number', validations=[
        v.RegexQuestionValidation(value=r'^[0-9]{6,9}$')])
    values.value_question('Unsatisfiable code', validations=[
        v.RegexQuestionValidation(value=r'^ZZZ-[0-9]{4}-QQQ$')])
    values.integration_question('Target repository', integration=search)

    # chapter 3: nested lists, item select and files
    data = b.chapter('Datasets')
    datasets = data.list_question('Datasets you will produce', required_phase=planning)
    datasets.value_question('Name', required_phase=planning)
    datasets.value_question('Expected size in GB', value_type='NumberQuestionValueType')
    personal = datasets.options_question('Does it contain personal data?', tags=[sensitive])
    personal.answer('No')
    consent = personal.answer('Yes')
    consent.file_question('Consent form', max_size=1_000_000, file_types='application/pdf')
    files = datasets.list_question('Files of the dataset')
    files.value_question('File name')
    formats = files.list_question('Formats of the file')
    formats.value_question('Format')
    data.item_select_question('Main dataset', list_question=datasets)
    data.file_question('Data management plan', max_size=5_000_000,
                       file_types='application/pdf, application/vnd.oasis.opendocument.text')
    data.file_question('Any attachment')
    return b


def sample_km_bundle() -> KnowledgeModelBundle:
    return build_sample_km().to_bundle(
        id=SAMPLE_KM_ID, version=SAMPLE_KM_VERSION, name='TDK Sample Knowledge Model',
        description='Covers every question and value type for generating document contexts',
        license='CC0-1.0', clock=lambda: _CREATED_AT)


def render_sample_km() -> str:
    return json.dumps(sample_km_bundle().to_json_data(), indent=2, ensure_ascii=False) + '\n'


if __name__ == '__main__':
    SAMPLE_KM_PATH.write_text(render_sample_km(), encoding='utf-8')
    print(SAMPLE_KM_PATH)  # noqa: T201
