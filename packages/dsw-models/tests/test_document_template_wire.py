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
    # 18.0 descriptors predate `language`; the model writes its default
    assert_same_json({**data, 'language': 'en'}, metadata.to_json_data())


def test_local_descriptor_without_optional_sections():
    data = json.loads((REFERENCE_DIR / 'templates' / 'smp-template.json').read_text(encoding='utf-8'))
    del data['_tdk']
    metadata = load(DocumentTemplateMetadata, data)
    assert metadata.language == 'en'
    assert '_tdk' not in metadata.to_json_data()


def test_bundle_descriptor_round_trip():
    data = load_synthetic('template_bundle.json')
    bundle = load(DocumentTemplateBundle, data)
    assert bundle.coordinate == bundle.id
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


def test_package_pattern_options_are_optional():
    data = load_synthetic('template_bundle.json')
    data['allowedPackages'][0]['options'] = {'any': 'value'}
    bundle = load(DocumentTemplateBundle, data)
    assert bundle.allowed_packages[0].options == {'any': 'value'}
    assert_same_json(data, bundle.to_json_data())
    assert 'options' not in bundle.to_json_data()['allowedPackages'][1]
