"""Every pydantic model in dsw.models must be fully defined and produce a JSON Schema.

Guards against annotations that pydantic cannot resolve at runtime, e.g. imports hidden
under ``typing.TYPE_CHECKING``.
"""
import importlib
import inspect
import pkgutil

import pydantic
import pytest

import dsw.models


OPTIONAL_MODULES = {'dsw.models.document_context.rendering'}  # needs dsw-models[rendering]


def _modules():
    for info in pkgutil.walk_packages(dsw.models.__path__, prefix='dsw.models.'):
        try:
            yield importlib.import_module(info.name)
        except ImportError:
            if info.name not in OPTIONAL_MODULES:
                raise


def _models():
    seen = set()
    for module in _modules():
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, pydantic.BaseModel)
                    and obj.__module__.startswith('dsw.models.')
                    and obj not in seen):
                seen.add(obj)
                yield obj


@pytest.mark.parametrize('model', sorted(_models(), key=lambda m: f'{m.__module__}.{m.__qualname__}'),
                         ids=lambda m: f'{m.__module__}.{m.__qualname__}')
def test_model_is_complete(model: type[pydantic.BaseModel]):
    if model.__pydantic_generic_metadata__['parameters']:
        pytest.skip('generic without type arguments')
    model.model_rebuild(raise_errors=True)
    assert model.__pydantic_complete__
    model.model_json_schema()
