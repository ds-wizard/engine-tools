import json
import typing


class DSWJSONEncoder(json.JSONEncoder):

    def default(self, o: typing.Any) -> typing.Any:
        if hasattr(o, 'to_dict') and callable(o.to_dict):
            return o.to_dict()
        return super().default(o)
