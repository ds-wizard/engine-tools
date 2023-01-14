import json


class DSWJSONEncoder(json.JSONEncoder):

    def default(self, value):
        if hasattr(value, 'to_dict') and callable(value.to_dict):
            return value.to_dict()
        else:
            return super().default(value)
