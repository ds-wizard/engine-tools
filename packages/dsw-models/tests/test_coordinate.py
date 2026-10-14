import pytest

from dsw.models.coordinate import (
    build_reference,
    parse_legacy_reference,
    parse_reference,
    upgrade_legacy_coordinate,
    upgrade_legacy_id,
)
from dsw.models.knowledge_model.package import KnowledgeModelBundlePackage
from dsw.models.strictness import load


def test_references():
    assert build_reference('dsw.root', '2.8.1') == 'dsw.root:2.8.1'
    assert parse_reference('dsw.root:2.8.1') == ('dsw.root', '2.8.1')
    assert parse_reference('dsw:root:2.8.1') is None
    assert parse_legacy_reference('dsw:root:2.8.1') == ('dsw.root', '2.8.1')
    assert parse_legacy_reference('root:2.8.1') == ('root', '2.8.1')
    assert parse_legacy_reference('root') is None


@pytest.mark.parametrize(('data', 'expected'), [
    ({'organizationId': 'dsw', 'kmId': 'root', 'id': 'dsw:root:1.0.0'}, {'id': 'dsw.root'}),
    ({'id': 'root'}, {'id': 'root'}),
    # the backend falls back to "id" unless both legacy keys are present
    ({'organizationId': 'dsw', 'id': 'root'}, {'id': 'root'}),
])
def test_upgrade_legacy_id(data, expected):
    upgrade_legacy_id(data, 'kmId')
    assert data == expected


@pytest.mark.parametrize(('data', 'expected'), [
    ({'forkOfPackageId': 'dsw:root:1.0.0'},
     {'forkOfPackageId': 'dsw.root', 'forkOfPackageVersion': '1.0.0'}),
    ({'forkOfPackageId': 'dsw.root', 'forkOfPackageVersion': '1.0.0'},
     {'forkOfPackageId': 'dsw.root', 'forkOfPackageVersion': '1.0.0'}),
    ({'forkOfPackageId': 'unparsable'}, {'forkOfPackageId': None, 'forkOfPackageVersion': None}),
    ({'forkOfPackageId': None}, {'forkOfPackageId': None}),
    ({}, {}),
])
def test_upgrade_legacy_coordinate(data, expected):
    upgrade_legacy_coordinate(data, 'forkOfPackage')
    assert data == expected


def test_package_reads_both_shapes_and_writes_5_0():
    common = {'name': 'KM', 'version': '1.1.0', 'metamodelVersion': 20, 'description': '',
              'events': []}
    legacy = load(KnowledgeModelBundlePackage, {
        **common, 'id': 'dsw:root:1.1.0', 'organizationId': 'dsw', 'kmId': 'root',
        'previousPackageId': 'dsw:root:1.0.0'})
    current = load(KnowledgeModelBundlePackage, {
        **common, 'id': 'dsw.root', 'previousPackageId': 'dsw.root',
        'previousPackageVersion': '1.0.0'})
    assert legacy == current
    assert current.reference == 'dsw.root:1.1.0'
    assert current.previous_package_reference == 'dsw.root:1.0.0'
    data = current.to_json_data()
    assert 'organizationId' not in data
    assert (data['previousPackageId'], data['previousPackageVersion']) == ('dsw.root', '1.0.0')
