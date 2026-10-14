import json

import pydantic
import pytest
from conftest import REFERENCE_DIR, assert_same_json, load_synthetic

from dsw.models.document_template.metadata import DocumentTemplateBundle, DocumentTemplateMetadata
from dsw.models.strictness import load
from dsw.models.versions import MetamodelVersion


TEMPLATES = sorted((REFERENCE_DIR / 'templates').glob('*.json'))


@pytest.mark.parametrize('path', TEMPLATES, ids=lambda path: path.stem)
def test_reference_local_descriptor_round_trip(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    metadata = load(DocumentTemplateMetadata, data)
    assert metadata.parsed_metamodel_version == MetamodelVersion(18, 0)
    assert metadata.tdk is not None
    assert metadata.id == f"{data['organizationId']}.{data['templateId']}"
    # 18.0 descriptors predate `language` and the single `id`; the model writes the 5.0 shape
    expected = {**data, 'id': metadata.id, 'language': 'en'}
    del expected['organizationId'], expected['templateId']
    for pattern in expected['allowedPackages']:
        org_id, km_id = pattern.pop('orgId'), pattern.pop('kmId')
        pattern['id'] = f'{org_id}.{km_id}' if org_id and km_id else None
    assert_same_json(expected, metadata.to_json_data())
    assert_same_json(expected, load(DocumentTemplateMetadata, expected).to_json_data())


def test_local_descriptor_without_optional_sections():
    data = json.loads((REFERENCE_DIR / 'templates' / 'smp-template.json').read_text(encoding='utf-8'))
    del data['_tdk']
    metadata = load(DocumentTemplateMetadata, data)
    assert metadata.language == 'en'
    assert '_tdk' not in metadata.to_json_data()


def test_bundle_descriptor_round_trip():
    data = load_synthetic('template_bundle.json')
    bundle = load(DocumentTemplateBundle, data)
    assert bundle.reference == 'example.my-template:1.0.0'
    assert_same_json(data, bundle.to_json_data())


def test_bundle_descriptor_updated_at_is_optional():
    data = load_synthetic('template_bundle.json')
    del data['updatedAt']
    assert 'updatedAt' not in load(DocumentTemplateBundle, data).to_json_data()


@pytest.mark.parametrize('value', [18, '18.x', '18.3.1'])
def test_metamodel_version_must_be_string(value):
    data = load_synthetic('template_bundle.json')
    data['metamodelVersion'] = value
    with pytest.raises(pydantic.ValidationError):
        load(DocumentTemplateBundle, data)


def test_package_pattern_uses_backend_keys():
    data = load_synthetic('template_bundle.json')
    data['allowedPackages'][0]['organizationId'] = 'dsw'
    with pytest.raises(pydantic.ValidationError, match='Unknown keys for PackagePattern: organizationId'):
        load(DocumentTemplateBundle, data)


@pytest.mark.parametrize(('legacy', 'expected'), [
    ({'orgId': 'dsw', 'kmId': 'root'}, 'dsw.root'),
    ({'orgId': 'dsw', 'kmId': None}, None),
    ({'orgId': None, 'kmId': None}, None),
    ({'id': 'dsw.root', 'orgId': None, 'kmId': None}, 'dsw.root'),
])
def test_package_pattern_reads_legacy_keys(legacy, expected):
    data = load_synthetic('template_bundle.json')
    data['allowedPackages'][0] = {**legacy, 'minVersion': '2.0.0', 'maxVersion': None}
    pattern = load(DocumentTemplateBundle, data).allowed_packages[0]
    assert pattern.id == expected
    assert 'orgId' not in pattern.to_json_data()


def test_legacy_identity_is_read():
    data = load_synthetic('template_bundle.json')
    legacy = {**data, 'id': 'example:my-template:1.0.0', 'organizationId': 'example',
              'templateId': 'my-template'}
    assert_same_json(data, load(DocumentTemplateBundle, legacy).to_json_data())


def test_package_pattern_options_are_optional():
    data = load_synthetic('template_bundle.json')
    data['allowedPackages'][0]['options'] = {'any': 'value'}
    bundle = load(DocumentTemplateBundle, data)
    assert bundle.allowed_packages[0].options == {'any': 'value'}
    assert_same_json(data, bundle.to_json_data())
    assert 'options' not in bundle.to_json_data()['allowedPackages'][1]
