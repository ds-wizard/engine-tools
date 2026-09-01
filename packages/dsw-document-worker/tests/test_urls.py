import pathlib

import pytest

from dsw.document_worker.config import SecurityConfig
from dsw.document_worker.urls import UrlNotAllowedError, UrlPolicy


def make_policy(**kwargs) -> UrlPolicy:
    options = {
        'allow_external_resources': True,
        'allow_private_network': False,
        'allowed_hosts': [],
        'allowed_paths': [],
        'max_redirects': 3,
    }
    options.update(kwargs)
    return UrlPolicy(SecurityConfig(**options))


@pytest.mark.parametrize('url', [
    'http://127.0.0.1/x',
    'http://127.13.13.13/x',
    'https://localhost:8080/x',
    'http://169.254.169.254/latest/meta-data/iam/security-credentials/',
    'http://[::1]/x',
    'http://[::ffff:169.254.169.254]/x',
    'http://[fd00::1]/x',
    'http://10.0.0.1/x',
    'http://172.16.0.1/x',
    'http://192.168.1.1/x',
    'http://100.64.0.1/x',
    'http://0.0.0.0/x',  # noqa: S104
    'http://198.18.0.1/x',
    'http://224.0.0.1/x',
    'http://240.0.0.1/x',
    'http://[2002:a9fe:a9fe::]/x',  # 6to4 of 169.254.169.254
])
def test_private_addresses_blocked(url):
    with pytest.raises(UrlNotAllowedError):
        make_policy().check_http_url(url)


@pytest.mark.parametrize('url', [
    'ftp://example.org/x',
    'file:///etc/passwd',
    'gopher://127.0.0.1/x',
    'jar:http://example.org/x!/y',
    'x',
])
def test_non_http_schemes_blocked(url):
    with pytest.raises(UrlNotAllowedError):
        make_policy().check_http_url(url)


def test_public_address_allowed():
    make_policy().check_http_url('http://8.8.8.8/x')
    make_policy().check_http_url('https://[2001:4860:4860::8888]/x')


def test_allowed_host_bypasses_address_check():
    make_policy(allowed_hosts=['localhost']).check_http_url('http://localhost:8080/x')
    with pytest.raises(UrlNotAllowedError):
        make_policy(allowed_hosts=['other']).check_http_url('http://localhost:8080/x')


def test_allow_private_network():
    make_policy(allow_private_network=True).check_http_url('http://127.0.0.1/x')


def test_external_requests_disabled():
    with pytest.raises(UrlNotAllowedError):
        make_policy(allow_external_resources=False).check_http_url('http://8.8.8.8/x')


def test_file_url_within_base_dir(tmp_path: pathlib.Path):
    asset = tmp_path / 'logo.svg'
    asset.touch()
    make_policy().check_file_url(asset.as_uri(), base_dir=tmp_path.resolve())


def test_file_url_outside_base_dir(tmp_path: pathlib.Path):
    base_dir = (tmp_path / 'template').resolve()
    base_dir.mkdir()
    outside = tmp_path / 'other.txt'
    outside.touch()
    for url in ('file:///etc/passwd', outside.as_uri(),
                f'{base_dir.as_uri()}/../other.txt'):
        with pytest.raises(UrlNotAllowedError):
            make_policy().check_file_url(url, base_dir=base_dir)


def test_file_url_remote_host(tmp_path: pathlib.Path):
    with pytest.raises(UrlNotAllowedError):
        make_policy().check_file_url(
            'file://example.org/x.png',
            base_dir=tmp_path.resolve(),
        )


def test_file_url_allowed_paths(tmp_path: pathlib.Path):
    base_dir = (tmp_path / 'template').resolve()
    base_dir.mkdir()
    fonts = tmp_path / 'fonts'
    fonts.mkdir()
    font = fonts / 'x.ttf'
    font.touch()
    policy = make_policy(allowed_paths=[str(fonts)])
    policy.check_file_url(font.as_uri(), base_dir=base_dir)


def test_resource_url_data(tmp_path: pathlib.Path):
    make_policy().check_resource_url(
        'data:image/png;base64,AAAA',
        base_dir=tmp_path.resolve(),
    )


def test_resource_url_dispatch(tmp_path: pathlib.Path):
    policy = make_policy()
    with pytest.raises(UrlNotAllowedError):
        policy.check_resource_url('file:///etc/passwd', base_dir=tmp_path.resolve())
    with pytest.raises(UrlNotAllowedError):
        policy.check_resource_url('http://127.0.0.1/x', base_dir=tmp_path.resolve())
    with pytest.raises(UrlNotAllowedError):
        policy.check_resource_url('ftp://8.8.8.8/x', base_dir=tmp_path.resolve())
