import requests

from ..config import TemplateConfig


class RequestsWrapper:

    def __init__(self, template_cfg: TemplateConfig):
        self.limit = template_cfg.requests.limit
        self.timeout = template_cfg.requests.timeout
        self.request_counter = 0

    def _prepare_for_request(self):
        self.request_counter += 1
        if self.request_counter > self.limit:
            raise RuntimeError(f'Number of requests is over the limit {self.limit}')

    def get(self, url, params=None, **kwargs) -> requests.Response:
        self._prepare_for_request()
        kwargs.update(timeout=self.timeout)
        resp = requests.get(url=url, params=params, **kwargs)
        return resp

    def post(self, url, data=None, json=None, **kwargs) -> requests.Response:
        self._prepare_for_request()
        kwargs.update(timeout=self.timeout)
        return requests.post(url=url, data=data, json=json, **kwargs)

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        self._prepare_for_request()
        kwargs.update(timeout=self.timeout)
        return requests.request(method=method, url=url, **kwargs)
