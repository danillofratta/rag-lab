import socket
import subprocess
import sys

import pytest


def test_outbound_socket_is_blocked() -> None:
    with socket.socket() as connection, pytest.raises(AssertionError, match="forbidden"):
        connection.connect(("127.0.0.1", 9))


def test_create_connection_is_blocked() -> None:
    with pytest.raises(AssertionError, match="forbidden"):
        socket.create_connection(("example.com", 80))


def test_subprocess_is_blocked() -> None:
    with pytest.raises(AssertionError, match="forbidden"):
        subprocess.run([sys.executable, "-c", "pass"], check=False)


@pytest.mark.anyio
async def test_event_loop_still_works_offline() -> None:
    import anyio

    await anyio.sleep(0)


@pytest.mark.integration
def test_integration_marker_is_excluded_by_default() -> None:
    raise AssertionError("integration tests must not run in the default selection")


@pytest.mark.eval
def test_eval_marker_is_excluded_by_default() -> None:
    raise AssertionError("eval tests must not run in the default selection")
