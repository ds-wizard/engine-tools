from __future__ import annotations

import typing
from datetime import UTC, date, datetime
from uuid import UUID

import pydantic

from .strictness import UnknownKeys, unknown_keys_of


NULL_UUID = UUID('00000000-0000-0000-0000-000000000000')


def to_camel(s: str) -> str:
    parts = s.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])


class BaseModel(pydantic.BaseModel):
    """Base of all wire models: camelCase JSON, unknown keys forbidden unless asked otherwise.

    Unknown keys are accepted by pydantic and then either rejected (default) or dropped,
    depending on the validation context (see :mod:`dsw.models.strictness`). Dropping them
    keeps serialization identical to the backend in both modes.
    """

    model_config = pydantic.ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        extra='allow',
    )

    @pydantic.model_validator(mode='after')
    def _check_unknown_keys(self, info: pydantic.ValidationInfo) -> typing.Self:
        extra = self.__pydantic_extra__
        if not extra:
            return self
        if unknown_keys_of(info.context) == UnknownKeys.IGNORE:
            self.__pydantic_extra__ = {}
            return self
        keys = ', '.join(sorted(extra))
        raise ValueError(f'Unknown keys for {type(self).__name__}: {keys}')

    def to_json_data(self) -> dict[str, typing.Any]:
        """Serialize to JSON-compatible data exactly as the backend writes it."""
        return self.model_dump(mode='json', by_alias=True)


JsonValue = pydantic.JsonValue


def format_timestamp(value: datetime) -> str:
    """Format as the backend (Aeson ``UTCTime``) does: UTC, ``Z``, no trailing fraction zeros."""
    if value.tzinfo is not None:
        value = value.astimezone(UTC)
    text = value.strftime('%Y-%m-%dT%H:%M:%S')
    if value.microsecond:
        text += f'.{value.microsecond:06d}'.rstrip('0')
    return f'{text}Z'


def utc_date(value: datetime) -> date:
    """Calendar day of ``value`` in UTC; naive values are taken as UTC."""
    return value.astimezone(UTC).date() if value.tzinfo is not None else value.date()


Timestamp = typing.Annotated[
    datetime,
    pydantic.PlainSerializer(format_timestamp, return_type=str, when_used='json'),
]


class KeyValue(BaseModel):
    """Backend ``MapEntry``, used for annotations and HTTP headers."""

    key: str
    value: str


Annotations = list[KeyValue]


class UserSuggestion(BaseModel):
    uuid: UUID
    first_name: str
    last_name: str
    gravatar_hash: str
    image_url: str | None = None
    affiliation: str | None = None
