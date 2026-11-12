"""Port resolution helper for ``start.bat`` on Windows."""

from __future__ import annotations

import argparse
import json
import socket
import urllib.request


def is_house_price_api(host: str, port: int, timeout: float = 0.8) -> bool:
    """Return True if ``host:port/health`` responds with a House Price API payload."""
    url = f"http://{host}:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            data = json.loads(resp.read().decode("utf-8"))
            return isinstance(data, dict) and "model_loaded" in data
    except Exception:
        return False


def is_port_free(host: str, port: int) -> bool:
    """Return True if binding ``host:port`` exclusively succeeds with no active listener."""
    # Check active TCP listeners on IPv4 and IPv6 loopback first.
    for family, target in ((socket.AF_INET, host), (socket.AF_INET6, "::1")):
        probe = socket.socket(family, socket.SOCK_STREAM)
        probe.settimeout(0.2)
        try:
            if probe.connect_ex((target, port)) == 0:
                return False
        except OSError:
            pass
        finally:
            probe.close()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def resolve_api_port(host: str = "127.0.0.1", start_port: int = 8000, span: int = 20) -> str:
    """Return ``reuse:<port>`` if our API is already running, else ``start:<free_port>``."""
    for port in range(start_port, start_port + span + 1):
        if is_house_price_api(host, port):
            return f"reuse:{port}"
        if is_port_free(host, port):
            return f"start:{port}"
    return "none:0"


def resolve_free_port(host: str = "127.0.0.1", start_port: int = 5173, span: int = 20) -> int:
    """Return the first bindable TCP port starting from ``start_port`` or ``0``."""
    for port in range(start_port, start_port + span + 1):
        if is_port_free(host, port):
            return port
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve API or frontend listening ports.")
    parser.add_argument("--mode", choices=("api", "free"), required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--start", type=int, default=8000)
    parser.add_argument("--span", type=int, default=20)
    args = parser.parse_args()

    if args.mode == "api":
        print(resolve_api_port(host=args.host, start_port=args.start, span=args.span))
    else:
        print(resolve_free_port(host=args.host, start_port=args.start, span=args.span))


if __name__ == "__main__":
    main()
