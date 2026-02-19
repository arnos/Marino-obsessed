"""Shared fixtures for Playwright UI tests.

Starts the Marimo vault app as a subprocess and provides a ``live_url``
fixture that gives the base URL to each test.  The server is started once
per session to keep test runs fast.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

_ROOT = Path(__file__).parent.parent.parent
_APP = _ROOT / "notebooks" / "vault_app.py"
_PORT = 2718


@pytest.fixture(scope="session")
def marimo_server():
    """Start the marimo app server; yield the process; terminate on teardown."""
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "marimo",
            "run",
            str(_APP),
            "--port",
            str(_PORT),
            "--headless",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(_ROOT),
    )

    # Wait up to 20 s for the server to be ready
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            r = requests.get(f"http://localhost:{_PORT}/", timeout=1)
            if r.status_code < 500:
                break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        stdout, stderr = proc.communicate(timeout=5)
        pytest.fail(
            f"Marimo server did not start within 20 s.\n"
            f"stdout: {stdout.decode()}\nstderr: {stderr.decode()}"
        )

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def live_url(marimo_server) -> str:  # noqa: ARG001
    return f"http://localhost:{_PORT}"
