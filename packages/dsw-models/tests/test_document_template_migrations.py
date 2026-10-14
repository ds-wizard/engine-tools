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


def as_5_0_identity(data):
    data = {**data, 'id': f"{data['organizationId']}.{data['templateId']}"}
    del data['organizationId'], data['templateId']
    data['allowedPackages'] = [
        {'id': f"{p['orgId']}.{p['kmId']}" if p['orgId'] and p['kmId'] else None,
         **{k: v for k, v in p.items() if k not in ('orgId', 'kmId')}}
        for p in data['allowedPackages']]
    return data


@pytest.mark.parametrize('path', TEMPLATES, ids=lambda path: path.stem)
def test_current_descriptors_gain_language_and_single_id(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    result = migrate_template_json(data)
    assert result.source_version == MetamodelVersion(18, 0)
    # crossing 18 -> 19: the descriptor is upgraded, the Jinja templates need porting by hand
    assert len(result.warnings) == 1
    assert 'written for the document context of 18.x' in result.warnings[0]
    assert result.changed
    assert result.data == {**as_5_0_identity(data), 'metamodelVersion': '19.0', 'language': 'en'}
    metadata = load(DocumentTemplateMetadata, result.data)
    assert metadata.reference == f"{data['organizationId']}.{data['templateId']}:{data['version']}"


def test_v1_local_descriptor():
    result = migrate_template_json(V1_DESCRIPTOR)
    metadata = load(DocumentTemplateMetadata, result.data)
    assert metadata.reference == 'dsw.questionnaire-report:1.0.0'
    assert metadata.metamodel_version == '19.0'
    assert result.data['formats'][0] == {
        'uuid': 'd3e98eb6-344d-481f-8e37-6a67b6cd1ad2', 'name': 'HTML', 'icon': 'far fa-file-code',
        'steps': [{'name': 'jinja', 'options': {'template': 'src/default.html.j2'}}]}
    assert metadata.allowed_packages[0].options == {'mode': 'full'}
    assert metadata.allowed_packages[0].id is None  # only an organization was named
    assert len(result.warnings) == 2
    assert 'not migrated' in result.warnings[-1]
    assert V1_DESCRIPTOR['metamodelVersion'] == 1  # input untouched


def test_legacy_bundle_descriptor_gets_single_id():
    data = load_synthetic('template_bundle.json')
    legacy = {**data, 'id': 'example:my-template:1.0.0', 'organizationId': 'example',
              'templateId': 'my-template', 'metamodelVersion': '17.1',
              'allowedPackages': [{'orgId': 'dsw', 'kmId': 'root', 'minVersion': '2.0.0',
                                   'maxVersion': None},
                                  {'orgId': None, 'kmId': None, 'minVersion': None,
                                   'maxVersion': None}]}
    result = migrate_template_json(legacy)
    assert result.data == data
    assert load(DocumentTemplateBundle, result.data).reference == 'example.my-template:1.0.0'
    assert len(result.warnings) == 1


@pytest.mark.parametrize(('extra', 'warning'), [
    ({'organizationId': 'dsw', 'templateId': 'other'}, 'disagrees with organizationId'),
    ({'version': '2.0.0'}, "disagrees with version '2.0.0'"),
])
def test_legacy_id_conflict_is_reported(extra, warning):
    result = migrate_template_json({**V1_DESCRIPTOR, **extra})
    assert result.data['id'] == ('dsw.other' if 'templateId' in extra else 'dsw.questionnaire-report')
    assert result.data['version'] == extra.get('version', '1.0.0')
    assert any(warning in w for w in result.warnings)


@pytest.mark.parametrize(('version', 'message'), [
    ('19.1', 'newer than supported'),
    ('20.0', 'newer than supported'),
    ('x', 'Invalid metamodel version'),
])
def test_unsupported_versions(version, message):
    with pytest.raises(MigrationError, match=message):
        migrate_template_json({**V1_DESCRIPTOR, 'metamodelVersion': version})


def test_same_version_gaining_language_is_changed():
    data = {**load_synthetic('template_bundle.json')}
    del data['language']
    result = migrate_template_json(data)
    assert result.data == {**data, 'language': 'en'}
    assert result.changed


def test_same_version_is_unchanged():
    data = load_synthetic('template_bundle.json')
    result = migrate_template_json(data)
    assert result.data == data
    assert not result.changed
