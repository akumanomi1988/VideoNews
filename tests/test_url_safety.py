import socket
from unittest.mock import patch

import pytest

from scripts.url_safety import validate_public_url


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "http://127.0.0.1/admin",
    "http://localhost:8080/",
    "http://192.168.1.1/",
    "https://user:password@example.com/",
])
def test_reject_local_or_unsafe_urls(url):
    with pytest.raises(ValueError):
        validate_public_url(url)


def test_allow_public_dns_target():
    address = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0))]
    with patch("socket.getaddrinfo", return_value=address):
        validate_public_url("https://example.com/article")


def test_reject_dns_resolution_to_private_ip():
    address = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 0))]
    with patch("socket.getaddrinfo", return_value=address):
        with pytest.raises(ValueError):
            validate_public_url("https://example.com/article")
