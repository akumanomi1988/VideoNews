"""Reject local/private URL targets before article extraction.

The HTTP fetcher must also disable redirects to private destinations if exposed
outside a trusted network. This preflight blocks direct local targets and DNS
names currently resolving to non-public IPs.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit


def validate_public_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Article URL must use HTTP or HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("Userinfo is not allowed in article URLs")
    hostname = parsed.hostname.rstrip(".")
    if hostname in ("localhost",) or hostname.endswith(".localhost"):
        raise ValueError("Localhost URLs are forbidden")
    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        try:
            addresses = [
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
            ]
        except (socket.gaierror, ValueError) as exc:
            raise ValueError("Article URL hostname could not be resolved") from exc
    if not addresses or any(not address.is_global or address.is_multicast for address in addresses):
        raise ValueError("Article URL must resolve only to public IP addresses")
