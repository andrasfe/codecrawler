"""Tests for cobol_penetrator.executor."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from cobol_penetrator.executor import execute
from cobol_penetrator.trace_parser import ExecutionResult


class TestExecuteBasic:
    """Basic execution with the mock executable fixture."""

    def test_returns_execution_result(self, mock_executable: Path) -> None:
        result = execute(mock_executable, {"input_state": {}, "stubs": {}})
        assert isinstance(result, ExecutionResult)

    def test_parses_paragraphs(self, mock_executable: Path) -> None:
        result = execute(mock_executable, {"input_state": {}, "stubs": {}})
        assert "1000-MAIN" in result.paragraphs_hit
        assert "2000-VALIDATE" in result.paragraphs_hit

    def test_parses_branches(self, mock_executable: Path) -> None:
        result = execute(mock_executable, {"input_state": {}, "stubs": {}})
        assert result.branches_hit.get("1") == "T"

    def test_parses_call_chain(self, mock_executable: Path) -> None:
        result = execute(mock_executable, {"input_state": {}, "stubs": {}})
        assert ("1000-MAIN", "2000-VALIDATE") in result.call_chain

    def test_parses_variable_snapshots(self, mock_executable: Path) -> None:
        result = execute(mock_executable, {"input_state": {}, "stubs": {}})
        assert result.variable_snapshots.get("1") == {
            "WS-STATUS": "00",
            "WS-FLAG": "Y",
        }

    def test_parses_mock_ops(self, mock_executable: Path) -> None:
        result = execute(mock_executable, {"input_state": {}, "stubs": {}})
        assert "READ-ACCOUNT" in result.mock_ops

    def test_exit_code_zero(self, mock_executable: Path) -> None:
        result = execute(mock_executable, {"input_state": {}, "stubs": {}})
        assert result.exit_code == 0

    def test_raw_stdout_populated(self, mock_executable: Path) -> None:
        result = execute(mock_executable, {"input_state": {}, "stubs": {}})
        assert "SPECTER-TRACE:1000-MAIN" in result.raw_stdout


class TestExecuteWithParams:
    """Execution with actual input_state and stubs parameters."""

    def test_mockdata_env_var_set(self, tmp_path: Path) -> None:
        """The executable receives MOCKDATA env var pointing to the .dat file."""
        script = tmp_path / "check_env"
        script.write_text(
            '#!/bin/bash\n'
            'if [ -n "$MOCKDATA" ] && [ -f "$MOCKDATA" ]; then\n'
            '    echo "SPECTER-TRACE:ENV-OK"\n'
            'else\n'
            '    echo "SPECTER-TRACE:ENV-MISSING"\n'
            'fi\n'
        )
        script.chmod(0o755)

        result = execute(
            script,
            {
                "input_state": {"WS-X": "1"},
                "stubs": {"OP": {"alpha_status": "OK"}},
            },
        )
        assert "ENV-OK" in result.paragraphs_hit

    def test_mockdata_file_contents(self, tmp_path: Path) -> None:
        """The .dat file contains properly formatted 80-byte records."""
        script = tmp_path / "dump_mock"
        script.write_text(
            '#!/bin/bash\n'
            'while IFS= read -r line; do\n'
            '    len=${#line}\n'
            '    echo "SPECTER-MOCK:LEN=$len"\n'
            'done < "$MOCKDATA"\n'
        )
        script.chmod(0o755)

        result = execute(
            script,
            {
                "input_state": {"VAR1": "A"},
                "stubs": {"OP1": {"alpha_status": "B"}},
            },
        )
        # Each record should be 80 bytes
        assert "LEN=80" in result.mock_ops


class TestExecuteExitCodes:
    """Non-zero exit codes."""

    def test_nonzero_exit_code(self, tmp_path: Path) -> None:
        script = tmp_path / "failing"
        script.write_text(
            '#!/bin/bash\n'
            'echo "SPECTER-TRACE:BEFORE-FAIL"\n'
            'exit 42\n'
        )
        script.chmod(0o755)

        result = execute(script, {"input_state": {}, "stubs": {}})
        assert result.exit_code == 42
        assert "BEFORE-FAIL" in result.paragraphs_hit

    def test_stderr_captured(self, tmp_path: Path) -> None:
        script = tmp_path / "stderr_script"
        script.write_text(
            '#!/bin/bash\n'
            'echo "ERROR: something went wrong" >&2\n'
            'echo "SPECTER-TRACE:DONE"\n'
        )
        script.chmod(0o755)

        result = execute(script, {"input_state": {}, "stubs": {}})
        assert "ERROR: something went wrong" in result.stderr
        assert "DONE" in result.paragraphs_hit


class TestExecuteTimeout:
    """Timeout handling."""

    def test_timeout_raises(self, tmp_path: Path) -> None:
        script = tmp_path / "slow"
        script.write_text(
            '#!/bin/bash\n'
            'sleep 60\n'
        )
        script.chmod(0o755)

        with pytest.raises(subprocess.TimeoutExpired):
            execute(script, {"input_state": {}, "stubs": {}}, timeout=1)


class TestExecuteErrors:
    """Error conditions."""

    def test_missing_executable_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError, match="Executable not found"):
            execute(missing, {"input_state": {}, "stubs": {}})

    def test_empty_params_accepted(self, mock_executable: Path) -> None:
        """Passing empty dicts for both input_state and stubs works."""
        result = execute(mock_executable, {})
        assert isinstance(result, ExecutionResult)

    def test_params_with_only_input_state(self, mock_executable: Path) -> None:
        result = execute(mock_executable, {"input_state": {"X": "1"}})
        assert isinstance(result, ExecutionResult)

    def test_params_with_only_stubs(self, mock_executable: Path) -> None:
        result = execute(
            mock_executable,
            {"stubs": {"OP": {"alpha_status": "OK"}}},
        )
        assert isinstance(result, ExecutionResult)
