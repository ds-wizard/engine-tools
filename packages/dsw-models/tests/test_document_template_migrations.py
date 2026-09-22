import json

import pytest
from conftest import REFERENCE_DIR, load_synthetic

from dsw.models.document_template.metadata import DocumentTemplateBundle, DocumentTemplateMetadata
from dsw.models.document_template.migrations import migrate_template_json
from dsw.models.errors import MigrationError
from dsw.models.strictness import load
from dsw.models.versions import MetamodelVersion


TEMPLATES = sorted((REFERENCE_DIR / 'templates').glob('*.json'))

V1_DESCRIPTOR = {
    'id': 'dsw:questionnaire-report:1.0.0',
    'name': 'Questionnaire Report',
    'description': 'Exported questions and answers',
    'license': 'Apache-2.0',
    'metamodelVersion': 1,
    'recommendedPackageId': 'dsw:root:1.0.0',
    'allowedPackages': [{'orgId': 'dsw', 'kmId': None, 'minVersion': None, 'maxVersion': None,
                         'options': {'mode': 'full'}}],
    'formats': [{'uuid': 'd3e98eb6-344d-481f-8e37-6a67b6cd1ad2', 'name': 'HTML', 'shortName': 'html',
                 'icon': 'far fa-file-code', 'color': '#f15a24',
                 'steps': [{'name': 'jinja', 'options': {'template': 'src/default.html.j2'}}]}],
}


@pytest.mark.parametrize('path', TEMPLATES, ids=lambda path: path.stem)
def test_current_descriptors_only_gain_language(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    result = migrate_template_json(data)
    assert result.source_version == MetamodelVersion(18, 0)
    assert result.warnings == []
    assert result.changed
    assert result.data == {**data, 'metamodelVersion': '18.3', 'language': 'en'}
    load(DocumentTemplateMetadata, result.data)


def test_v1_local_descriptor():
    result = migrate_template_json(V1_DESCRIPTOR)
    metadata = load(DocumentTemplateMetadata, result.data)
    assert metadata.coordinate == 'dsw:questionnaire-report:1.0.0'
    assert metadata.metamodel_version == '18.3'
    assert 'id' not in result.data
    assert result.data['formats'][0] == {
        'uuid': 'd3e98eb6-344d-481f-8e37-6a67b6cd1ad2', 'name': 'HTML', 'icon': 'far fa-file-code',
        'steps': [{'name': 'jinja', 'options': {'template': 'src/default.html.j2'}}]}
    assert metadata.allowed_packages[0].options == {'mode': 'full'}
    assert len(result.warnings) == 2
    assert 'not migrated' in result.warnings[-1]
    assert V1_DESCRIPTOR['metamodelVersion'] == 1  # input untouched


def test_bundle_descriptor_keeps_id():
    data = load_synthetic('template_bundle.json')
    data['metamodelVersion'] = '17.1'
    result = migrate_template_json(data, kind='bundle')
    bundle = load(DocumentTemplateBundle, result.data)
    assert bundle.id == 'example:my-template:1.0.0'
    assert len(result.warnings) == 1


def test_legacy_id_conflict_is_reported():
    result = migrate_template_json({**V1_DESCRIPTOR, 'templateId': 'other'})
    assert result.data['templateId'] == 'other'
    assert any('disagrees with templateId' in warning for warning in result.warnings)


@pytest.mark.parametrize(('version', 'message'), [
    ('19.0', 'newer than supported'),
    ('18.4', 'newer than supported'),
    ('x', 'Invalid metamodel version'),
])
def test_unsupported_versions(version, message):
    with pytest.raises(MigrationError, match=message):
        migrate_template_json({**V1_DESCRIPTOR, 'metamodelVersion': version})


def test_same_version_gaining_language_is_changed():
    data = {**load_synthetic('template_bundle.json')}
    del data['language']
    result = migrate_template_json(data, kind='bundle')
    assert result.data == {**data, 'language': 'en'}
    assert result.changed


def test_same_version_is_unchanged():
    data = load_synthetic('template_bundle.json')
    result = migrate_template_json(data, kind='bundle')
    assert result.data == data
    assert not result.changed
