"""Unit tests for ``scripts/resolve_port.py`` port fallback logic."""

from __future__ import annotations

import socket

from scripts.resolve_port import resolve_api_port, resolve_free_port


def test_resolve_free_port_skips_occupied_port() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    occupied_port = sock.getsockname()[1]
    try:
        resolved = resolve_free_port("127.0.0.1", start_port=occupied_port, span=5)
        assert resolved != occupied_port
        assert occupied_port < resolved <= occupied_port + 5
    finally:
        sock.close()


def test_resolve_api_port_falls_back_when_port_busy_without_api() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    occupied_port = sock.getsockname()[1]
    try:
        result = resolve_api_port("127.0.0.1", start_port=occupied_port, span=5)
        mode, port_str = result.split(":", maxsplit=1)
        assert mode == "start"
        assert int(port_str) > occupied_port
    finally:
        sock.close()
