"""Build a small knowledge model in Python and export it as a ``.km`` bundle.

    python create_km.py                       # writes example-km-1.0.0.km
    python create_km.py -o my.km --version 1.1.0

The bundle can be imported in the Data Stewardship Wizard (Knowledge Models › Import).
"""
import argparse
import json
import pathlib
import sys

from dsw.models.knowledge_model.builder import KnowledgeModelBuilder
from dsw.models.knowledge_model.bundle import compile_bundle
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.knowledge_model.validation import validate
from dsw.models.strictness import load


def build_knowledge_model() -> KnowledgeModelBuilder:
    builder = KnowledgeModelBuilder()

    before_submission = builder.phase('Before submitting the proposal')
    builder.phase('Before finishing the project')
    findability = builder.metric('Findability', abbreviation='F')
    reusability = builder.metric('Reusability', abbreviation='R')
    horizon = builder.tag('Horizon Europe', color='#f1c40f')

    chapter = builder.chapter('Data description', text='Tell us about the data of your project.')
    reuse = chapter.options_question('Will you reuse existing data?',
                                     required_phase=before_submission, tags=[horizon])
    reuse.url_reference('https://www.go-fair.org/fair-principles/', 'FAIR principles')
    yes = reuse.answer('Yes', metric_measures=[(findability, 1.0, 1.0), (reusability, 1.0, 1.0)])
    yes.value_question('Which data will you reuse?', text='Name the datasets and their sources.')
    reuse.answer('No', advice='Consider searching data repositories first.',
                 metric_measures=[(reusability, 0.0, 1.0)])

    datasets = chapter.list_question('Datasets you will produce')
    datasets.value_question('Name')
    datasets.value_question('Expected size in GB', value_type='NumberQuestionValueType')
    formats = datasets.multi_choice_question('Formats')
    for label in ('CSV', 'JSON', 'NetCDF', 'Other'):
        formats.choice(label)

    storage = builder.chapter('Storage')
    storage.value_question('Where will you store the data during the project?',
                           required_phase=before_submission)
    return builder


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('-o', '--output', type=pathlib.Path, help='output .km file')
    parser.add_argument('--organization-id', default='example')
    parser.add_argument('--km-id', default='example-km')
    parser.add_argument('--version', default='1.0.0')
    args = parser.parse_args()

    builder = build_knowledge_model()
    km = builder.build()
    errors = [issue for issue in validate(km) if issue.severity == 'error']
    for issue in errors:
        print(issue)
    if errors:
        return 1

    bundle = builder.to_bundle(
        organization_id=args.organization_id, km_id=args.km_id, version=args.version,
        name='Example knowledge model', description='Built with dsw-models',
        readme='# Example knowledge model\n\nBuilt with `dsw-models`.', license='CC0',
    )
    output = args.output or pathlib.Path(f'{args.km_id}-{args.version}.km')
    output.write_text(json.dumps(bundle.to_json_data(), indent=2), encoding='utf-8')

    # sanity check: the file loads strictly and compiles back to the same knowledge model
    reloaded = load(KnowledgeModelBundle, json.loads(output.read_text(encoding='utf-8')))
    if compile_bundle(reloaded) != km:
        print(f'{output} does not compile back to the built knowledge model')
        return 1
    events = len(bundle.packages[0].events)
    print(f'Wrote {output}: {bundle.id} with {events} event(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
