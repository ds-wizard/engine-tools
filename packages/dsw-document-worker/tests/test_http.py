import pytest
import requests

from dsw.document_worker.config import (
    SecurityConfig,
    TemplateConfig,
    TemplateRequestsConfig,
)
from dsw.document_worker.model.http import RequestsWrapper
from dsw.document_worker.urls import UrlNotAllowedError, UrlPolicy


def make_wrapper(*, limit=100, **security) -> RequestsWrapper:
    options = {
        'allow_external_resources': True,
        'allow_private_network': False,
        'allowed_hosts': [],
        'allowed_paths': [],
        'max_redirects': 3,
    }
    options.update(security)
    template_cfg = TemplateConfig(
        ids=['dsw:'],
        requests=TemplateRequestsConfig(enabled=True, limit=limit, timeout=1),
        secrets={},
        send_sentry=False,
    )
    return RequestsWrapper(
        template_cfg=template_cfg,
        policy=UrlPolicy(SecurityConfig(**options)),
    )


class FakeResponse:
    def __init__(self, url, status_code=200, location=None):
        self.url = url
        self.status_code = status_code
        self.headers = {} if location is None else {'location': location}

    @property
    def is_redirect(self):
        return 'location' in self.headers and self.status_code in (
            301, 302, 303, 307, 308,
        )


@pytest.fixture
def calls(monkeypatch):
    recorded = []

    def fake_request(**kwargs):
        recorded.append(kwargs)
        location = kwargs.pop('_location', None)
        return FakeResponse(kwargs['url'], location=location)

    monkeypatch.setattr(requests, 'request', fake_request)
    return recorded


def test_blocked_url_is_not_requested(calls):
    with pytest.raises(UrlNotAllowedError):
        make_wrapper().get('http://169.254.169.254/latest/meta-data/')
    assert calls == []


def test_non_http_scheme_blocked(calls):
    with pytest.raises(UrlNotAllowedError):
        make_wrapper().get('file:///etc/passwd')
    assert calls == []


def test_forbidden_kwargs_rejected(calls):
    for kwargs in ({'verify': False}, {'timeout': 100}, {'proxies': {}}):
        with pytest.raises(RuntimeError):
            make_wrapper().get('http://8.8.8.8/x', **kwargs)
    assert calls == []


def test_request_defaults(calls):
    make_wrapper().get('http://8.8.8.8/x')
    assert calls[0]['verify'] is True
    assert calls[0]['allow_redirects'] is False
    assert calls[0]['timeout'] == 1


def test_request_limit(calls):
    wrapper = make_wrapper(limit=2)
    wrapper.get('http://8.8.8.8/x')
    wrapper.get('http://8.8.8.8/x')
    with pytest.raises(RuntimeError):
        wrapper.get('http://8.8.8.8/x')


def test_redirect_target_is_checked(monkeypatch):
    def fake_request(**kwargs):
        return FakeResponse(kwargs['url'], status_code=302,
                            location='http://169.254.169.254/latest/meta-data/')

    monkeypatch.setattr(requests, 'request', fake_request)
    with pytest.raises(UrlNotAllowedError):
        make_wrapper().get('http://8.8.8.8/x')


def test_redirects_are_limited(monkeypatch):
    seen = []

    def fake_request(**kwargs):
        seen.append(kwargs['url'])
        return FakeResponse(kwargs['url'], status_code=302, location='http://8.8.8.8/next')

    monkeypatch.setattr(requests, 'request', fake_request)
    response = make_wrapper(max_redirects=2).get('http://8.8.8.8/x')
    assert response.is_redirect
    assert len(seen) == 3  # initial + 2 redirects


def test_redirects_not_followed_when_disabled(monkeypatch):
    seen = []

    def fake_request(**kwargs):
        seen.append(kwargs['url'])
        return FakeResponse(kwargs['url'], status_code=302, location='http://8.8.8.8/next')

    monkeypatch.setattr(requests, 'request', fake_request)
    make_wrapper().get('http://8.8.8.8/x', allow_redirects=False)
    assert len(seen) == 1


def test_credentials_dropped_on_cross_host_redirect(monkeypatch):
    seen = []

    def fake_request(**kwargs):
        seen.append(kwargs)
        if len(seen) == 1:
            return FakeResponse(kwargs['url'], status_code=302,
                                location='https://1.1.1.1/other')
        return FakeResponse(kwargs['url'])

    monkeypatch.setattr(requests, 'request', fake_request)
    make_wrapper().post(
        'http://8.8.8.8/x',
        json={'a': 1},
        headers={'Authorization': 'Bearer secret', 'Accept': 'application/json'},
    )
    assert seen[0]['headers']['Authorization'] == 'Bearer secret'
    assert 'Authorization' not in seen[1]['headers']
    assert seen[1]['headers']['Accept'] == 'application/json'
    assert seen[1]['method'] == 'GET'
    assert seen[1].get('json') is None
