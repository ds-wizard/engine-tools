from __future__ import annotations

import ipaddress
import logging
import pathlib
import socket
import typing
import urllib.parse
import urllib.request


if typing.TYPE_CHECKING:
    from .config import SecurityConfig


LOG = logging.getLogger(__name__)

HTTP_SCHEMES = frozenset({'http', 'https'})
LOCAL_NETLOCS = frozenset({'', 'localhost'})


class UrlNotAllowedError(ValueError):
    """Raised when a URL is rejected by the security policy."""

    def __init__(self, url: str, reason: str):
        super().__init__(f'URL not allowed ({reason}): {url}')
        self.url = url
        self.reason = reason


def _is_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(address, ipaddress.IPv6Address):
        # Unwrap addresses that are just another way to write an IPv4 address
        # (e.g. ::ffff:169.254.169.254 or 2002:a9fe:a9fe::)
        for mapped in (address.ipv4_mapped, address.sixtofour):
            if mapped is not None:
                return _is_public_address(mapped)
        if address.teredo is not None:
            return _is_public_address(address.teredo[1])
    # is_global excludes private, loopback, link-local, shared address space,
    # and other special-purpose ranges (but not multicast)
    return address.is_global and not address.is_multicast


class UrlPolicy:
    """Decides which URLs may be fetched while rendering a document.

    The policy is deliberately conservative: it is applied to resources
    referenced from rendered HTML (WeasyPrint) as well as to HTTP requests
    made from Jinja templates.

    Note that hosts are resolved for the check and then resolved again when
    the connection is made, so a DNS entry changing in between (DNS rebinding)
    is not covered here; use network-level restrictions of the worker if that
    is a concern.
    """

    def __init__(self, cfg: SecurityConfig):
        self.allow_external = cfg.allow_external_resources
        self.allow_private_network = cfg.allow_private_network
        self.allowed_hosts = frozenset(host.lower() for host in cfg.allowed_hosts)
        self.allowed_paths = tuple(
            pathlib.Path(path).expanduser().resolve()
            for path in cfg.allowed_paths
        )
        self.max_redirects = max(0, cfg.max_redirects)

    def _check_host(self, url: str, host: str, port: int | None):
        if host.lower() in self.allowed_hosts:
            return
        if self.allow_private_network:
            return
        try:
            addr_infos = socket.getaddrinfo(
                host, port, proto=socket.IPPROTO_TCP,
            )
        except OSError as e:
            raise UrlNotAllowedError(url, f'host cannot be resolved: {e}') from e
        addresses = {info[4][0] for info in addr_infos}
        if not addresses:
            raise UrlNotAllowedError(url, 'host cannot be resolved')
        for address in addresses:
            try:
                parsed_address = ipaddress.ip_address(address)
            except ValueError as e:
                raise UrlNotAllowedError(url, f'invalid address: {address}') from e
            if not _is_public_address(parsed_address):
                raise UrlNotAllowedError(
                    url,
                    f'host resolves to a non-public address: {address}',
                )

    def check_http_url(self, url: str):
        """Check a http(s) URL against the policy (raises if not allowed)."""
        if not self.allow_external:
            raise UrlNotAllowedError(url, 'external requests are disabled')
        try:
            parts = urllib.parse.urlsplit(url)
        except ValueError as e:
            raise UrlNotAllowedError(url, f'malformed URL: {e}') from e
        scheme = parts.scheme.lower()
        if scheme not in HTTP_SCHEMES:
            raise UrlNotAllowedError(url, f'disallowed scheme "{scheme}"')
        try:
            host = parts.hostname
            port = parts.port
        except ValueError as e:
            raise UrlNotAllowedError(url, f'malformed URL: {e}') from e
        if not host:
            raise UrlNotAllowedError(url, 'missing host')
        self._check_host(url, host, port)

    def check_file_url(self, url: str, base_dir: pathlib.Path):
        """Check a file URL, allowing only files within permitted directories."""
        parts = urllib.parse.urlsplit(url)
        if parts.netloc.lower() not in LOCAL_NETLOCS:
            raise UrlNotAllowedError(url, 'remote file URL')
        try:
            path = pathlib.Path(urllib.request.url2pathname(parts.path))
            resolved = path.resolve()
        except (OSError, ValueError) as e:
            raise UrlNotAllowedError(url, f'invalid path: {e}') from e
        allowed_dirs = (base_dir.resolve(), *self.allowed_paths)
        if not any(resolved.is_relative_to(allowed) for allowed in allowed_dirs):
            raise UrlNotAllowedError(url, 'file outside of the allowed directories')

    def check_resource_url(self, url: str, base_dir: pathlib.Path):
        """Check a URL referenced from a rendered document."""
        try:
            scheme = urllib.parse.urlsplit(url).scheme.lower()
        except ValueError as e:
            raise UrlNotAllowedError(url, f'malformed URL: {e}') from e
        if scheme == 'data':
            return
        if scheme == 'file':
            self.check_file_url(url, base_dir=base_dir)
            return
        if scheme in HTTP_SCHEMES:
            self.check_http_url(url)
            return
        raise UrlNotAllowedError(url, f'disallowed scheme "{scheme}"')
