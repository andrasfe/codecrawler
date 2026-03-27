"""End-to-end integration tests for the orchestrator loop.

These tests create real mock executables (shell scripts), real mock.cbl
fixtures, and mock the LLM provider to return predetermined params.
They verify the full lifecycle: ticket creation, cascading, coverage
tracking, and resume.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cobol_penetrator.config import PenetratorConfig
from cobol_penetrator.llm_providers.protocol import CompletionResponse
from cobol_penetrator.orchestrator import run


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _create_mock_executable(tmp_path: Path, name: str = "mock_cobol") -> Path:
    """Create a shell script that emits trace lines for a two-paragraph program.

    The script emits:
    - SPECTER-TRACE for 1000-MAIN and 2000-VALIDATE
    - @@B for branches 1 (T) and 2 (T)
    - SPECTER-CALL from 1000-MAIN to 2000-VALIDATE
    - @@V variable snapshot for branch 1
    """
    script = tmp_path / name
    script.write_text(
        '#!/bin/bash\n'
        'echo "SPECTER-TRACE:1000-MAIN"\n'
        'echo "@@B:1:T"\n'
        'echo "SPECTER-CALL:FROM=1000-MAIN:TO=2000-VALIDATE"\n'
        'echo "SPECTER-TRACE:2000-VALIDATE"\n'
        'echo "@@B:2:T"\n'
        'echo "@@V:1:WS-STATUS=00:WS-FLAG=Y"\n'
    )
    script.chmod(0o755)
    return script


def _create_mock_cbl(tmp_path: Path, name: str = "test.mock.cbl") -> Path:
    """Create a minimal mock.cbl with 2 paragraphs and 2 branches."""
    cbl = tmp_path / name
    cbl.write_text(
        "       IDENTIFICATION DIVISION.\n"
        "       PROGRAM-ID. TESTPROG.\n"
        "       DATA DIVISION.\n"
        "       WORKING-STORAGE SECTION.\n"
        "       01 WS-STATUS    PIC X(2).\n"
        "       01 WS-FLAG      PIC X(1).\n"
        "       PROCEDURE DIVISION.\n"
        "       1000-MAIN.\n"
        '           DISPLAY "SPECTER-TRACE:1000-MAIN"\n'
        "           PERFORM 2000-VALIDATE\n"
        "           IF WS-STATUS = '00'\n"
        '               DISPLAY "@@B:1:T"\n'
        "           ELSE\n"
        '               DISPLAY "@@B:1:F"\n'
        "           END-IF\n"
        "           STOP RUN.\n"
        "       2000-VALIDATE.\n"
        '           DISPLAY "SPECTER-TRACE:2000-VALIDATE"\n'
        "           IF WS-FLAG = 'Y'\n"
        '               DISPLAY "@@B:2:T"\n'
        "           ELSE\n"
        '               DISPLAY "@@B:2:F"\n'
        "           END-IF.\n"
    )
    return cbl


def _create_mock_provider() -> MagicMock:
    """Create a mock LLM provider that returns predetermined params."""
    provider = MagicMock()
    provider.default_model = "test-model"
    provider.complete = AsyncMock(
        return_value=CompletionResponse(
            content=json.dumps({
                "input_state": {"WS-STATUS": "00", "WS-FLAG": "Y"},
                "stubs": {},
            }),
            model="test-model",
            tokens_used=50,
        )
    )
    return provider


def _make_config(
    tmp_path: Path,
    executable: Path,
    mock_cbl: Path,
    budget: int = 20,
    resume: bool = False,
) -> PenetratorConfig:
    """Create a PenetratorConfig pointing at tmp_path."""
    return PenetratorConfig(
        executable=executable,
        mock_cbl=mock_cbl,
        budget=budget,
        timeout=60,
        resume=resume,
        tickets_path=tmp_path / "tickets.json",
        coverage_path=tmp_path / "coverage.json",
        params_dir=tmp_path / "params",
        max_attempts=3,
    )


# ---------------------------------------------------------------------------
# End-to-end test: full loop
# ---------------------------------------------------------------------------


class TestFullLoop:
    """End-to-end orchestrator tests."""

    def test_full_lifecycle(self, tmp_path: Path) -> None:
        """Complete lifecycle: create, execute, cascade, close tickets."""
        executable = _create_mock_executable(tmp_path)
        mock_cbl = _create_mock_cbl(tmp_path)
        config = _make_config(tmp_path, executable, mock_cbl)
        mock_provider = _create_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result = asyncio.run(run(config))

        # The orchestrator should have run at least one execution.
        assert result["executions"] >= 1

        # Coverage should be non-zero.
        assert result["coverage_pct"] > 0.0

        # At least the entry ticket should be done.
        assert result["done_tickets"] >= 1

        # Total tickets includes cascaded ones.
        assert result["total_tickets"] >= 1

        # Verify artifacts were written.
        assert (tmp_path / "tickets.json").exists()
        assert (tmp_path / "coverage.json").exists()
        assert (tmp_path / "params").exists()

    def test_coverage_increases_with_iterations(
        self, tmp_path: Path
    ) -> None:
        """Coverage should be monotonically non-decreasing."""
        executable = _create_mock_executable(tmp_path)
        mock_cbl = _create_mock_cbl(tmp_path)
        config = _make_config(tmp_path, executable, mock_cbl)
        mock_provider = _create_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            asyncio.run(run(config))

        coverage_data = json.loads(
            (tmp_path / "coverage.json").read_text()
        )
        history = coverage_data.get("history", [])

        if len(history) > 1:
            for i in range(1, len(history)):
                assert history[i]["coverage_pct"] >= history[i - 1]["coverage_pct"], (
                    f"Coverage decreased at iteration {history[i]['iteration']}"
                )

    def test_ticket_cascade_creates_branch_and_paragraph_tickets(
        self, tmp_path: Path
    ) -> None:
        """Completing entry paragraph should cascade to branch and paragraph tickets."""
        executable = _create_mock_executable(tmp_path)
        mock_cbl = _create_mock_cbl(tmp_path)
        config = _make_config(tmp_path, executable, mock_cbl)
        mock_provider = _create_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            asyncio.run(run(config))

        tickets_data = json.loads(
            (tmp_path / "tickets.json").read_text()
        )

        ticket_types = [t["_type"] for t in tickets_data]
        assert "ParagraphTicket" in ticket_types
        assert "BranchTicket" in ticket_types

        # Entry paragraph should have cascaded to at least 1 branch ticket
        branch_tickets = [
            t for t in tickets_data if t["_type"] == "BranchTicket"
        ]
        assert len(branch_tickets) >= 1

    def test_params_files_written(self, tmp_path: Path) -> None:
        """Each successful ticket should get a params JSON file."""
        executable = _create_mock_executable(tmp_path)
        mock_cbl = _create_mock_cbl(tmp_path)
        config = _make_config(tmp_path, executable, mock_cbl)
        mock_provider = _create_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result = asyncio.run(run(config))

        params_dir = tmp_path / "params"
        param_files = list(params_dir.glob("*.json"))
        # At least one param file for the entry ticket success.
        assert len(param_files) >= 1

        # Verify param file structure.
        for pf in param_files:
            data = json.loads(pf.read_text())
            assert "ticket_id" in data
            assert "ticket_type" in data
            assert "params" in data


# ---------------------------------------------------------------------------
# Resume test
# ---------------------------------------------------------------------------


class TestResume:
    """Tests for resume functionality."""

    def test_resume_continues_from_prior_state(
        self, tmp_path: Path
    ) -> None:
        """Running with resume=True picks up from the saved state."""
        executable = _create_mock_executable(tmp_path)
        mock_cbl = _create_mock_cbl(tmp_path)
        mock_provider = _create_mock_provider()

        # First run with budget=1 to stop early.
        config1 = _make_config(
            tmp_path, executable, mock_cbl, budget=1, resume=False
        )
        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result1 = asyncio.run(run(config1))

        assert result1["executions"] == 1
        # The first run should have created tickets.json
        assert (tmp_path / "tickets.json").exists()

        tickets_after_first = json.loads(
            (tmp_path / "tickets.json").read_text()
        )
        total_first = len(tickets_after_first)

        # Second run with resume=True and more budget.
        config2 = _make_config(
            tmp_path, executable, mock_cbl, budget=10, resume=True
        )
        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result2 = asyncio.run(run(config2))

        # The resume run should have processed more tickets.
        # It should not have created a duplicate entry ticket.
        tickets_after_second = json.loads(
            (tmp_path / "tickets.json").read_text()
        )

        # On resume, the entry ticket already exists so should
        # not be duplicated. Total tickets should be >= first run.
        assert len(tickets_after_second) >= total_first

        # Coverage should be at least as high as the first run.
        assert result2["coverage_pct"] >= result1["coverage_pct"]

    def test_resume_loads_coverage_state(self, tmp_path: Path) -> None:
        """Resume run loads coverage history and continues it."""
        executable = _create_mock_executable(tmp_path)
        mock_cbl = _create_mock_cbl(tmp_path)
        mock_provider = _create_mock_provider()

        # First run.
        config1 = _make_config(
            tmp_path, executable, mock_cbl, budget=2, resume=False
        )
        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            asyncio.run(run(config1))

        coverage1 = json.loads(
            (tmp_path / "coverage.json").read_text()
        )
        history_len_1 = len(coverage1.get("history", []))

        # Second run (resume).
        config2 = _make_config(
            tmp_path, executable, mock_cbl, budget=5, resume=True
        )
        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            asyncio.run(run(config2))

        coverage2 = json.loads(
            (tmp_path / "coverage.json").read_text()
        )
        # History should have grown (or stayed same if no new work).
        assert len(coverage2.get("history", [])) >= history_len_1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for the orchestrator."""

    def test_all_tickets_blocked(self, tmp_path: Path) -> None:
        """Run terminates gracefully when tickets exhaust attempts."""
        executable = _create_mock_executable(tmp_path)
        # Create a mock.cbl with a paragraph the executable never hits.
        cbl = tmp_path / "unreachable.mock.cbl"
        cbl.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TESTPROG.\n"
            "       DATA DIVISION.\n"
            "       WORKING-STORAGE SECTION.\n"
            "       01 WS-STATUS    PIC X(2).\n"
            "       PROCEDURE DIVISION.\n"
            "       9999-UNREACHABLE.\n"
            '           DISPLAY "SPECTER-TRACE:9999-UNREACHABLE"\n'
            "           STOP RUN.\n"
        )

        config = _make_config(tmp_path, executable, cbl, budget=10)
        config.max_attempts = 2
        mock_provider = _create_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result = asyncio.run(run(config))

        # The entry paragraph ticket should eventually be blocked.
        assert result["blocked_tickets"] >= 1

    def test_zero_budget(self, tmp_path: Path) -> None:
        """Budget of 0 means no executions."""
        executable = _create_mock_executable(tmp_path)
        mock_cbl = _create_mock_cbl(tmp_path)
        config = _make_config(
            tmp_path, executable, mock_cbl, budget=0
        )
        mock_provider = _create_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result = asyncio.run(run(config))

        assert result["executions"] == 0
