"""Tiny helper: is a TCP service reachable? Used to gate integration smoke tests."""
from __future__ import annotations

import socket
from urllib.parse import urlparse


def port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def url_reachable(url: str, default_port: int) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    return port_open(host, parsed.port or default_port)
