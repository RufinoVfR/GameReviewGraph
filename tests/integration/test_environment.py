"""Environment integrity tests: verifies setup, build, and docker-up succeed."""
import subprocess
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAKE = ["make", "-C", str(PROJECT_ROOT)]
TIMEOUT_SETUP = 300
TIMEOUT_BUILD = 300
TIMEOUT_DOCKER_UP = 120


def _run(target: str, timeout: int) -> subprocess.CompletedProcess:
    """Run a make target and return the completed process.

    Args:
        target: Makefile target name.
        timeout: Maximum seconds to wait before raising TimeoutExpired.

    Returns:
        CompletedProcess with stdout/stderr captured.
    """
    return subprocess.run(
        [*MAKE, target],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.mark.env
class TestEnvironmentIntegrity:
    """Ensures the development environment bootstraps cleanly end-to-end."""

    def test_setup(self):
        """make setup must exit 0 — installs Docker, uv, and Python 3.11."""
        result = _run("setup", TIMEOUT_SETUP)
        assert result.returncode == 0, (
            f"make setup failed (exit {result.returncode}):\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )

    def test_build(self):
        """make build must exit 0 — builds the app Docker image."""
        result = _run("build", TIMEOUT_BUILD)
        assert result.returncode == 0, (
            f"make build failed (exit {result.returncode}):\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )

    def test_docker_up(self):
        """make docker-up must exit 0 — starts MinIO, Redis, and app services."""
        result = _run("docker-up", TIMEOUT_DOCKER_UP)
        assert result.returncode == 0, (
            f"make docker-up failed (exit {result.returncode}):\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
