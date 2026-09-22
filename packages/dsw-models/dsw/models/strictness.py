from __future__ import annotations

import enum
import typing


if typing.TYPE_CHECKING:
    import pydantic


CONTEXT_KEY = 'unknown_keys'


class UnknownKeys(enum.StrEnum):
    """What to do with keys a model does not know."""

    FORBID = 'forbid'
    IGNORE = 'ignore'


def unknown_keys_of(context: typing.Any) -> UnknownKeys:
    if isinstance(context, dict):
        return UnknownKeys(context.get(CONTEXT_KEY, UnknownKeys.FORBID))
    return UnknownKeys.FORBID


def load[TModel: pydantic.BaseModel](
    model: type[TModel],
    data: typing.Any,
    *,
    unknown_keys: UnknownKeys = UnknownKeys.FORBID,
) -> TModel:
    """Validate Python data (e.g. parsed JSON) as ``model``."""
    return model.model_validate(data, context={CONTEXT_KEY: unknown_keys})


def load_json[TModel: pydantic.BaseModel](
    model: type[TModel],
    data: str | bytes,
    *,
    unknown_keys: UnknownKeys = UnknownKeys.FORBID,
) -> TModel:
    """Validate a JSON document as ``model``."""
    return model.model_validate_json(data, context={CONTEXT_KEY: unknown_keys})
