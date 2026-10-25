import socket
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


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


def test_default_selection_excludes_integration_and_eval(pytester: pytest.Pytester) -> None:
    """Run an inner session with the project's real pytest options, not a copy of them."""
    options = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]
    markers = "\n    ".join(options["markers"])
    pytester.makeini(f"[pytest]\naddopts = {options['addopts']}\nmarkers =\n    {markers}\n")
    pytester.makepyfile(
        """
        import pytest

        def test_unit():
            pass

        @pytest.mark.integration
        def test_integration():
            pass

        @pytest.mark.eval
        def test_eval():
            pass
        """
    )
    result = pytester.runpytest_inprocess()
    result.assert_outcomes(passed=1, deselected=2)
