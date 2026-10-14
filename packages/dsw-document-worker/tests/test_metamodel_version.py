"""The metamodel gate the worker applies to a document template before rendering.

The check itself lives in ``dsw-models`` (one source of truth with the metamodel version);
what matters here is which template versions ``check_compliance`` lets through.
"""
import pytest

from dsw.models.document_context.graph import check_metamodel_version


@pytest.mark.parametrize('version', ['19.0', '19', '19.9', '19.10'])
def test_accepted(version):
    check_metamodel_version(version)


@pytest.mark.parametrize(('version', 'message'), [
    ('18.3', 'expected major version 19'),
    ('17.9', 'expected major version 19'),
    ('20.0', 'expected major version 19'),
    ('x', 'Invalid metamodel version format'),
    ('', 'Invalid metamodel version format'),
])
def test_rejected(version, message):
    with pytest.raises(ValueError, match=message):
        check_metamodel_version(version)
