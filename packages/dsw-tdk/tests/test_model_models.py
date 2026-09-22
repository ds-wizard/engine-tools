"""Behavior the TDK takes from dsw-models."""
import collections
import logging

import pytest

from dsw.models.versions import DOCUMENT_TEMPLATE_METAMODEL_VERSION
from dsw.tdk import consts
from dsw.tdk.core import TDKCore, TDKProcessingError
from dsw.tdk.model import Template
from dsw.tdk.validation import TemplateValidator


DESCRIPTOR = {
    'templateId': 'my-template',
    'organizationId': 'example',
    'version': '1.0.0',
    'name': 'My template',
    'description': 'Test',
    'license': 'Apache-2.0',
    'metamodelVersion': '18.3',
    'allowedPackages': [
        {'orgId': 'dsw', 'kmId': None, 'minVersion': None, 'maxVersion': None,
         'options': {'mode': 'full'}},
        {'orgId': None, 'kmId': None, 'minVersion': None, 'maxVersion': None},
    ],
    'formats': [],
    'unknownKey': 'kept',
}


def test_metamodel_version_matches_models():
    assert consts.METAMODEL_VERSION == str(DOCUMENT_TEMPLATE_METAMODEL_VERSION)


def test_allowed_package_options_survive_rewrite():
    template = Template.load_local(collections.OrderedDict(DESCRIPTOR))
    serialized = template.serialize_local()
    assert serialized['allowedPackages'] == DESCRIPTOR['allowedPackages']
    assert serialized['unknownKey'] == 'kept'
    assert template.serialize_for_package()['allowedPackages'] == DESCRIPTOR['allowedPackages']


@pytest.mark.parametrize(('version', 'valid'), [
    ('18.3', True), (18, True), ('18', True), ('0', False), ('abc', False), ('18.3.1', False),
])
def test_metamodel_version_validation(version, valid):
    template = Template.load_local(collections.OrderedDict({**DESCRIPTOR, 'metamodelVersion': version}))
    errors = [e for e in TemplateValidator.collect_errors(template) if e.field_name == 'metamodel_version']
    assert (errors == []) is valid


@pytest.mark.parametrize(('local', 'remote', 'outcome'), [
    ('18.3', '18.3', None),
    ('18.0', '18.3', 'warning'),
    ('18', '18.3', 'warning'),
    (11, '18.3', 'Unsupported metamodel version: local 11.0, remote 18.3'),
    ('18.4', '18.3', 'Unsupported metamodel version: local 18.4, remote 18.3'),
    ('x', '18.3', 'Invalid metamodel version format: x'),
    ('18.3', 'unknown', 'Invalid remote metamodel version format: unknown'),
])
def test_remote_metamodel_version_check(local, remote, outcome, caplog):
    template = Template.load_local(collections.OrderedDict({**DESCRIPTOR, 'metamodelVersion': local}))
    core = TDKCore(template=template, logger=logging.getLogger('test-tdk'))
    core.remote_metamodel_version = remote
    if outcome is None or outcome == 'warning':
        with caplog.at_level(logging.WARNING, logger='test-tdk'):
            core._check_metamodel_version()
        assert ('older than remote version' in caplog.text) is (outcome == 'warning')
    else:
        with pytest.raises(TDKProcessingError) as error:
            core._check_metamodel_version()
        assert error.value.message == outcome
