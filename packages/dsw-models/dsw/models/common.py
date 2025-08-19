import uuid

import pydantic


NULL_UUID = uuid.UUID('00000000-0000-0000-0000-000000000000')


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )
