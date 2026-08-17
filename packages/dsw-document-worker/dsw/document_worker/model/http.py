from __future__ import annotations

import logging
import typing
import urllib.parse

import requests


if typing.TYPE_CHECKING:
    from ..config import TemplateConfig
    from ..urls import UrlPolicy


LOG = logging.getLogger(__name__)

# Keyword arguments that must not be overridden by a template as they would
# weaken the security controls applied here
FORBIDDEN_KWARGS = frozenset({'hooks', 'proxies', 'timeout', 'verify'})
# Statuses after which the request method is changed to GET (as in requests)
REDIRECT_TO_GET_STATUSES = frozenset({301, 302, 303})
SAFE_METHODS = frozenset({'GET', 'HEAD', 'OPTIONS'})


class RequestsWrapper:
    """Wrapper for HTTP requests made from document templates.

    The URL of each request (including each redirect hop) is verified against
    the security policy, so that templates cannot reach loopback, link-local,
    or otherwise private addresses (e.g. cloud metadata endpoints).
    """

    def __init__(self, template_cfg: TemplateConfig, policy: UrlPolicy):
        self.limit = template_cfg.requests.limit
        self.timeout = template_cfg.requests.timeout
        self.policy = policy
        self.request_counter = 0

    def _prepare_for_request(self):
        self.request_counter += 1
        if self.request_counter > self.limit:
            raise RuntimeError(f'Number of requests is over the limit {self.limit}')

    @staticmethod
    def _check_kwargs(kwargs: dict):
        forbidden = FORBIDDEN_KWARGS.intersection(kwargs.keys())
        if forbidden:
            raise RuntimeError(f'Request options are not allowed: {", ".join(sorted(forbidden))}')

    @staticmethod
    def _drop_credentials(kwargs: dict):
        kwargs.pop('auth', None)
        kwargs.pop('cookies', None)
        headers = kwargs.get('headers')
        if isinstance(headers, dict):
            kwargs['headers'] = {
                name: value for name, value in headers.items()
                if name.lower() not in ('authorization', 'cookie', 'proxy-authorization')
            }

    @staticmethod
    def _drop_body(kwargs: dict):
        for key in ('data', 'json', 'files'):
            kwargs.pop(key, None)

    def _send(self, method: str, url: str, **kwargs) -> requests.Response:
        self._check_kwargs(kwargs)
        follow_redirects = bool(kwargs.pop('allow_redirects', True))
        method = method.upper()
        redirects = 0
        while True:
            self._prepare_for_request()
            self.policy.check_http_url(url)
            response = requests.request(
                method=method,
                url=url,
                timeout=self.timeout,
                allow_redirects=False,
                verify=True,
                **kwargs,
            )
            if not follow_redirects or not response.is_redirect:
                return response
            if redirects >= self.policy.max_redirects:
                LOG.warning('Too many redirects for request to %s', url)
                return response
            redirects += 1
            target = urllib.parse.urljoin(response.url, response.headers['location'])
            # the query of the redirect target is already part of its location
            kwargs.pop('params', None)
            if urllib.parse.urlsplit(target).netloc != urllib.parse.urlsplit(url).netloc:
                # do not leak credentials (e.g. template secrets) to another host
                self._drop_credentials(kwargs)
            if response.status_code in REDIRECT_TO_GET_STATUSES and method not in SAFE_METHODS:
                method = 'GET'
                self._drop_body(kwargs)
            url = target

    def get(self, url, params=None, **kwargs) -> requests.Response:
        return self._send('GET', url, params=params, **kwargs)

    def post(self, url, data=None, json=None, **kwargs) -> requests.Response:
        return self._send('POST', url, data=data, json=json, **kwargs)

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        return self._send(method, url, **kwargs)
