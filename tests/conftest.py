import asyncio
import socket
import subprocess
import threading
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def offline(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit tests cannot open outbound sockets or start subprocesses."""
    if request.node.get_closest_marker("integration"):
        return  # Integration tests talk to the docker-compose services.

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("External network and subprocesses are forbidden in tests")

    original_connect = socket.socket.connect
    original_socketpair = socket.socketpair
    internal = threading.local()

    def guarded_connect(connection: socket.socket, address: Any) -> None:
        # The event loop wakes itself through a local socket pair.
        if getattr(internal, "socketpair", False):
            return original_connect(connection, address)
        return forbidden()

    def local_socketpair(*args: Any, **kwargs: Any) -> tuple[socket.socket, socket.socket]:
        internal.socketpair = True
        try:
            return original_socketpair(*args, **kwargs)
        finally:
            internal.socketpair = False

    monkeypatch.setattr(socket, "socketpair", local_socketpair)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


@pytest.fixture
def anyio_backend() -> tuple[str, dict[str, Any]]:
    # psycopg cannot use the Windows default Proactor loop, so tests use the selector loop.
    return "asyncio", {"loop_factory": asyncio.SelectorEventLoop}
