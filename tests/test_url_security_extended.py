"""SSRF preflight: forbidden targets and DNS rebinding warning boundaries."""
import socket
import pytest
from scripts.url_safety import validate_public_url

@pytest.mark.parametrize("url", [
    "", "example.org/path", "//example.org/path", "ftp://example.org/file",
    "file:///etc/passwd", "data:text/plain,hello", "javascript:alert(1)",
    "http://localhost", "https://LOCALHOST/", "http://web.localhost/",
    "http://127.0.0.1/", "https://127.13.22.33", "http://0.0.0.0/",
    "http://10.2.3.4/", "http://172.16.0.1/", "http://172.31.255.255/",
    "http://192.168.1.1/", "http://169.254.169.254/latest/meta-data",
    "http://100.64.0.1/", "http://224.0.0.1/", "http://255.255.255.255/",
    "http://[::1]/", "http://[::]/", "http://[fc00::1]/",
    "http://[fe80::1]/", "http://[ff02::1]/", "http://[2001:db8::1]/",
    "https://user@8.8.8.8/", "https://user:pass@8.8.8.8/"
])
def test_forbidden_targets_fail_before_network(url):
    with pytest.raises(ValueError):
        validate_public_url(url)

@pytest.mark.parametrize("url", [
    "https://8.8.8.8/report", "http://1.1.1.1/a?b=c",
    "https://[2606:4700:4700::1111]/report"
])
def test_public_literal_ips_are_accepted(url):
    validate_public_url(url)

@pytest.mark.parametrize("addresses", [
    ["8.8.8.8", "10.0.0.8"], ["127.0.0.1", "8.8.8.8"],
    ["fe80::1", "2606:4700:4700::1111"], ["169.254.1.1"]
])
def test_any_private_dns_answer_causes_rejection(monkeypatch, addresses):
    def lookup(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (address, 0)) for address in addresses]
    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    with pytest.raises(ValueError, match="public IP"):
        validate_public_url("https://public.example.org/article")

def test_multiple_public_dns_records_are_allowed(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.1.1.1", 0)),
    ])
    validate_public_url("https://news.example.org/article")

def test_empty_dns_result_is_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [])
    with pytest.raises(ValueError):
        validate_public_url("https://news.example.org")

def test_dns_lookup_error_is_rejected(monkeypatch):
    def lookup(*args, **kwargs):
        raise socket.gaierror("no host")
    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    with pytest.raises(ValueError, match="could not be resolved"):
        validate_public_url("https://news.example.org")
