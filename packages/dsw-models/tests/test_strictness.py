import pydantic
import pytest

from dsw.models.common import BaseModel
from dsw.models.strictness import UnknownKeys, load, load_json


class Inner(BaseModel):
    some_value: int


class Outer(BaseModel):
    inner: Inner
    optional_text: str | None = None


def test_camel_case_round_trip():
    data = {'inner': {'someValue': 1}, 'optionalText': None}
    model = load(Outer, data)
    assert model.inner.some_value == 1
    assert model.to_json_data() == data


def test_unknown_keys_forbidden_by_default():
    with pytest.raises(pydantic.ValidationError, match='Unknown keys for Inner: extra'):
        load(Outer, {'inner': {'someValue': 1, 'extra': True}})


def test_unknown_keys_forbidden_without_context():
    with pytest.raises(pydantic.ValidationError, match='Unknown keys for Outer: other'):
        Outer.model_validate({'inner': {'someValue': 1}, 'other': 2})


def test_unknown_keys_ignored_and_dropped():
    model = load_json(
        Outer,
        '{"inner": {"someValue": 1, "extra": true}, "other": 2}',
        unknown_keys=UnknownKeys.IGNORE,
    )
    assert model.to_json_data() == {'inner': {'someValue': 1}, 'optionalText': None}
