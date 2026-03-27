"""Shared test fixtures for cobol-penetrator."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a clean temporary directory."""
    return tmp_path


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_executable(tmp_path: Path) -> Path:
    """Create a mock COBOL executable (shell script) that emits trace lines."""
    script = tmp_path / "mock_cobol"
    script.write_text(
        '#!/bin/bash\n'
        'echo "SPECTER-TRACE:1000-MAIN"\n'
        'echo "@@B:1:T"\n'
        'echo "SPECTER-CALL:FROM=1000-MAIN:TO=2000-VALIDATE"\n'
        'echo "SPECTER-TRACE:2000-VALIDATE"\n'
        'echo "@@V:1:WS-STATUS=00:WS-FLAG=Y"\n'
        'echo "SPECTER-MOCK:READ-ACCOUNT"\n'
    )
    script.chmod(0o755)
    return script
