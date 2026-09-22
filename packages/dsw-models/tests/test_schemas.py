import json
import time

import jsonschema
import pytest
from conftest import REFERENCE_DIR, load_reference, load_synthetic

from dsw.models import schemas
from dsw.models.knowledge_model import convert, flat
from dsw.models.knowledge_model.bundle import compile_bundle
from dsw.models.knowledge_model.package import KnowledgeModelBundle
from dsw.models.strictness import load


def validator(schema):
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


ALL_SCHEMAS = {
    'bundle': lambda **kw: schemas.knowledge_model_bundle_schema(**kw),
    'flat': lambda **kw: schemas.knowledge_model_schema('flat', **kw),
    'tree': lambda **kw: schemas.knowledge_model_schema('tree', **kw),
    'template-local': lambda **kw: schemas.template_json_schema('local', **kw),
    'template-bundle': lambda **kw: schemas.template_json_schema('bundle', **kw),
    'document-context': lambda **kw: schemas.document_context_schema(**kw),
    'project-events': lambda **kw: schemas.project_events_schema(**kw),
}


@pytest.mark.parametrize('mode', ['validation', 'serialization'])
@pytest.mark.parametrize('name', ALL_SCHEMAS)
def test_schemas_are_valid(name, mode):
    schema = ALL_SCHEMAS[name](schema_id=f'https://example.org/{name}.json', mode=mode)
    validator(schema)
    assert schema['$schema'] == schemas.DIALECT
    assert schema['$id'] == f'https://example.org/{name}.json'
    assert not any(key.startswith('EditEventField') for key in schema.get('$defs', {}))


@pytest.mark.parametrize('representation', ['flat', 'tree'])
def test_compact_schema(representation):
    schema = schemas.knowledge_model_schema(representation, compact=True)
    validator(schema)
    assert schema['title'] == f'Knowledge Model ({representation})'
    assert 'title' not in schema['$defs']['Chapter']
    assert 'discriminator' not in json.dumps(schema)


def test_compact_tree_schema_uuids_optional():
    schema = schemas.knowledge_model_schema('tree', compact=True)
    assert 'uuid' not in schema['$defs']['Chapter'].get('required', [])


def test_fixtures_validate():
    km_data = load_synthetic('knowledge_model.json')
    km = load(flat.KnowledgeModel, km_data)
    tree_data = convert.flat_to_tree(km).to_json_data()
    cases = [
        ('flat', km_data),
        ('tree', tree_data),
        ('template-bundle', load_synthetic('template_bundle.json')),
        ('document-context', load_synthetic('document_context.json')),
        ('project-events', load_synthetic('project_events.json')),
    ]
    cases += [('template-local', json.loads(path.read_text(encoding='utf-8')))
              for path in sorted((REFERENCE_DIR / 'templates').glob('*.json'))]
    for name, data in cases:
        validator(ALL_SCHEMAS[name]()).validate(data)
    validator(schemas.knowledge_model_schema('tree', compact=True)).validate(tree_data)
    validator(schemas.knowledge_model_schema('flat', compact=True)).validate(km_data)


def test_model_output_validates_in_serialization_mode():
    km = load(flat.KnowledgeModel, load_synthetic('knowledge_model.json'))
    validator(ALL_SCHEMAS['flat'](mode='serialization')).validate(km.to_json_data())


def test_reference_bundle_and_compiled_model_validate():
    data = load_reference('dsw_smp_1.2.4.km.gz')
    started = time.perf_counter()
    validator(ALL_SCHEMAS['bundle']()).validate(data)
    km = compile_bundle(load(KnowledgeModelBundle, data))
    validator(ALL_SCHEMAS['flat']()).validate(km.to_json_data())
    assert time.perf_counter() - started < 30


def test_schema_rejects_what_models_reject():
    bundle_validator = validator(ALL_SCHEMAS['bundle']())
    data = load_reference('dsw_smp_1.2.4.km.gz')
    event = data['packages'][0]['events'][0]
    event['content']['unknown'] = 1
    assert not bundle_validator.is_valid({**data, 'packages': [{**data['packages'][0], 'events': [event]}]})
    edit = next(e for e in data['packages'][1]['events'] if e['content']['eventType'].startswith('Edit'))
    field = next(key for key, value in edit['content'].items() if isinstance(value, dict) and 'changed' in value)
    edit['content'].pop('unknown', None)
    edit['content'][field] = {'changed': True}
    package = {**data['packages'][1], 'events': [edit]}
    assert not bundle_validator.is_valid({**data, 'packages': [package]})
