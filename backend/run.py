"""Start the OpenDF API. From backend/: python run.py"""

import errno
import socket
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.config import settings  # noqa: E402


def _address_in_use(exc: OSError) -> bool:
    # 48 is EADDRINUSE on macOS, 98 on Linux. errno.EADDRINUSE covers both, plus Windows.
    return exc.errno == errno.EADDRINUSE or exc.errno in {48, 98}


def _port_is_taken(host: str, port: int) -> bool:
    """Bind without SO_REUSEADDR so a busy port fails on Linux and macOS."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False
    seen: set[tuple] = set()
    for family, socktype, proto, _canon, sockaddr in infos:
        key = (family, sockaddr)
        if key in seen:
            continue
        seen.add(key)
        sock = socket.socket(family, socktype, proto)
        try:
            sock.bind(sockaddr)
        except OSError as exc:
            if _address_in_use(exc):
                return True
            raise
        finally:
            sock.close()
    return False


def _port_busy_message(host: str, port: int) -> str:
    return (
        f"OpenDF cannot start: {host}:{port} is already in use.\n"
        "Another process is listening on this port. Stop it, or choose a different port:\n"
        "  OPENDF_PORT=8001 python run.py\n"
        "Host and port are read from OPENDF_HOST and OPENDF_PORT "
        "(defaults: 127.0.0.1 and 8000)."
    )


if __name__ == "__main__":
    host = settings.host
    port = int(settings.port)
    if _port_is_taken(host, port):
        print(_port_busy_message(host, port))
        raise SystemExit(1)
    try:
        uvicorn.run("app.main:app", host=host, port=port, reload=False, log_level="info")
    except OSError as exc:
        if _address_in_use(exc):
            print(_port_busy_message(host, port))
            raise SystemExit(1) from None
        raise
