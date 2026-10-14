import pytest

from dsw.models.errors import MetamodelVersionError
from dsw.models.versions import DOCUMENT_TEMPLATE_METAMODEL_VERSION, MetamodelVersion


@pytest.mark.parametrize(('value', 'expected'), [
    ('18.3', MetamodelVersion(18, 3)),
    ('18', MetamodelVersion(18, 0)),
    (17, MetamodelVersion(17, 0)),
    (MetamodelVersion(1, 2), MetamodelVersion(1, 2)),
])
def test_parse(value, expected):
    assert MetamodelVersion.parse(value) == expected


@pytest.mark.parametrize('value', ['', '18.3.1', 'x.1', '-1', True, None, 18.3])
def test_parse_invalid(value):
    with pytest.raises(MetamodelVersionError):
        MetamodelVersion.parse(value)


def test_str():
    assert str(DOCUMENT_TEMPLATE_METAMODEL_VERSION) == '19.0'


@pytest.mark.parametrize(('other', 'supported'), [
    ('19.0', True),
    ('19.1', False),
    ('18.3', False),
    ('20.0', False),
])
def test_supports(other, supported):
    assert DOCUMENT_TEMPLATE_METAMODEL_VERSION.supports(MetamodelVersion.parse(other)) is supported
