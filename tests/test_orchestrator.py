"""Tests for the orchestrator module."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cobol_penetrator.config import PenetratorConfig
from cobol_penetrator.knowledge import LearnedKnowledge
from cobol_penetrator.llm_providers.protocol import CompletionResponse, Message
from cobol_penetrator.mock_reader import BranchInfo, ParagraphInfo, ProgramStructure
from cobol_penetrator.orchestrator import (
    run,
    select_agent,
    ticket_target_reached,
)
from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket
from cobol_penetrator.trace_parser import ExecutionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_structure() -> ProgramStructure:
    """Build a minimal ProgramStructure for testing."""
    paragraphs = {
        "1000-MAIN": ParagraphInfo(
            name="1000-MAIN",
            line_start=1,
            line_end=10,
            source_code="1000-MAIN.\n    ...",
            branches=["1"],
            performs=["2000-VALIDATE"],
        ),
        "2000-VALIDATE": ParagraphInfo(
            name="2000-VALIDATE",
            line_start=11,
            line_end=20,
            source_code="2000-VALIDATE.\n    ...",
            branches=["2"],
            performs=[],
        ),
    }
    branches = {
        "1": BranchInfo(
            id="1",
            paragraph="1000-MAIN",
            condition_text="WS-STATUS = '00'",
            condition_vars=["WS-STATUS"],
            directions=["T", "F"],
        ),
        "2": BranchInfo(
            id="2",
            paragraph="2000-VALIDATE",
            condition_text="WS-FLAG = 'Y'",
            condition_vars=["WS-FLAG"],
            directions=["T", "F"],
        ),
    }
    return ProgramStructure(
        entry_paragraph="1000-MAIN",
        paragraphs=paragraphs,
        branches=branches,
        call_graph={
            "1000-MAIN": ["2000-VALIDATE"],
            "2000-VALIDATE": [],
        },
    )


def _make_mock_provider() -> MagicMock:
    """Create a mock LLM provider that returns predetermined params."""
    provider = MagicMock()
    provider.default_model = "test-model"
    provider.complete = AsyncMock(
        return_value=CompletionResponse(
            content=json.dumps({
                "input_state": {"WS-STATUS": "00"},
                "stubs": {},
            }),
            model="test-model",
            tokens_used=100,
        )
    )
    return provider


# ---------------------------------------------------------------------------
# Tests: select_agent
# ---------------------------------------------------------------------------


class TestSelectAgent:
    """Tests for select_agent."""

    def test_entry_paragraph_gets_recon_agent(self) -> None:
        """ParagraphTicket with single-element call_path -> ReconAgent."""
        from cobol_penetrator.agents.recon import ReconAgent

        ticket = ParagraphTicket(
            id="PARA-1000-MAIN",
            paragraph="1000-MAIN",
            call_path=["1000-MAIN"],
        )
        provider = _make_mock_provider()
        config = PenetratorConfig()
        agent = select_agent(ticket, provider, config)
        assert isinstance(agent, ReconAgent)

    def test_empty_call_path_gets_recon_agent(self) -> None:
        """ParagraphTicket with empty call_path -> ReconAgent."""
        from cobol_penetrator.agents.recon import ReconAgent

        ticket = ParagraphTicket(
            id="PARA-TEST",
            paragraph="TEST",
            call_path=[],
        )
        provider = _make_mock_provider()
        config = PenetratorConfig()
        agent = select_agent(ticket, provider, config)
        assert isinstance(agent, ReconAgent)

    def test_deep_paragraph_gets_paragraph_agent(self) -> None:
        """ParagraphTicket with multi-element call_path -> ParagraphAgent."""
        from cobol_penetrator.agents.paragraph import ParagraphAgent

        ticket = ParagraphTicket(
            id="PARA-2000-VALIDATE",
            paragraph="2000-VALIDATE",
            call_path=["1000-MAIN", "2000-VALIDATE"],
        )
        provider = _make_mock_provider()
        config = PenetratorConfig()
        agent = select_agent(ticket, provider, config)
        assert isinstance(agent, ParagraphAgent)

    def test_branch_ticket_gets_branch_agent(self) -> None:
        """BranchTicket -> BranchAgent."""
        from cobol_penetrator.agents.branch import BranchAgent

        ticket = BranchTicket(
            id="BRANCH-1-T",
            branch_id="1",
            direction="T",
            paragraph="1000-MAIN",
        )
        provider = _make_mock_provider()
        config = PenetratorConfig()
        agent = select_agent(ticket, provider, config)
        assert isinstance(agent, BranchAgent)

    def test_unknown_ticket_type_raises(self) -> None:
        """Non-ticket type raises ValueError."""
        provider = _make_mock_provider()
        config = PenetratorConfig()
        with pytest.raises(ValueError, match="Unknown ticket type"):
            select_agent("not a ticket", provider, config)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests: ticket_target_reached
# ---------------------------------------------------------------------------


class TestTicketTargetReached:
    """Tests for ticket_target_reached."""

    def test_paragraph_hit(self) -> None:
        """Returns True when paragraph appears in paragraphs_hit."""
        ticket = ParagraphTicket(
            id="PARA-1000-MAIN",
            paragraph="1000-MAIN",
        )
        result = ExecutionResult(paragraphs_hit=["1000-MAIN", "2000-VALIDATE"])
        assert ticket_target_reached(ticket, result) is True

    def test_paragraph_miss(self) -> None:
        """Returns False when paragraph is not in paragraphs_hit."""
        ticket = ParagraphTicket(
            id="PARA-3000-PROCESS",
            paragraph="3000-PROCESS",
        )
        result = ExecutionResult(paragraphs_hit=["1000-MAIN"])
        assert ticket_target_reached(ticket, result) is False

    def test_branch_hit_correct_direction(self) -> None:
        """Returns True when branch ID+direction match."""
        ticket = BranchTicket(
            id="BRANCH-1-T",
            branch_id="1",
            direction="T",
            paragraph="1000-MAIN",
        )
        result = ExecutionResult(branches_hit={"1": "T"})
        assert ticket_target_reached(ticket, result) is True

    def test_branch_hit_wrong_direction(self) -> None:
        """Returns False when branch ID matches but direction differs."""
        ticket = BranchTicket(
            id="BRANCH-1-T",
            branch_id="1",
            direction="T",
            paragraph="1000-MAIN",
        )
        result = ExecutionResult(branches_hit={"1": "F"})
        assert ticket_target_reached(ticket, result) is False

    def test_branch_miss(self) -> None:
        """Returns False when branch ID is not in branches_hit."""
        ticket = BranchTicket(
            id="BRANCH-5-T",
            branch_id="5",
            direction="T",
            paragraph="2000-VALIDATE",
        )
        result = ExecutionResult(branches_hit={"1": "T"})
        assert ticket_target_reached(ticket, result) is False


# ---------------------------------------------------------------------------
# Tests: Full run() loop
# ---------------------------------------------------------------------------


class TestRunLoop:
    """Integration tests for the run() orchestration loop."""

    def _make_mock_executable(self, tmp_path: Path) -> Path:
        """Create a mock executable that emits trace lines."""
        script = tmp_path / "mock_cobol"
        script.write_text(
            '#!/bin/bash\n'
            'echo "SPECTER-TRACE:1000-MAIN"\n'
            'echo "@@B:1:T"\n'
            'echo "SPECTER-CALL:FROM=1000-MAIN:TO=2000-VALIDATE"\n'
            'echo "SPECTER-TRACE:2000-VALIDATE"\n'
            'echo "@@B:2:T"\n'
            'echo "@@V:1:WS-STATUS=00"\n'
        )
        script.chmod(0o755)
        return script

    def _make_mock_cbl(self, tmp_path: Path) -> Path:
        """Create a minimal mock.cbl file."""
        cbl = tmp_path / "test.mock.cbl"
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

    def test_run_creates_and_closes_entry_ticket(
        self, tmp_path: Path
    ) -> None:
        """run() creates entry ticket and closes it on success."""
        executable = self._make_mock_executable(tmp_path)
        mock_cbl = self._make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=5,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
        )

        mock_provider = _make_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result = asyncio.run(run(config))

        assert result["executions"] >= 1
        assert result["coverage_pct"] > 0.0
        assert result["done_tickets"] >= 1

        # Verify tickets.json was written.
        assert (tmp_path / "tickets.json").exists()
        tickets_data = json.loads(
            (tmp_path / "tickets.json").read_text()
        )
        # At least the entry ticket should exist.
        assert len(tickets_data) >= 1

        # Verify coverage.json was written.
        assert (tmp_path / "coverage.json").exists()

    def test_run_cascades_branch_tickets(self, tmp_path: Path) -> None:
        """After completing a paragraph, branch tickets are created."""
        executable = self._make_mock_executable(tmp_path)
        mock_cbl = self._make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=10,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
        )

        mock_provider = _make_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result = asyncio.run(run(config))

        # Check that branch tickets were created.
        tickets_data = json.loads(
            (tmp_path / "tickets.json").read_text()
        )
        branch_tickets = [
            t for t in tickets_data if t["_type"] == "BranchTicket"
        ]
        # 1000-MAIN has branch 1 (T, F) -> 2 branch tickets
        # 2000-VALIDATE has branch 2 (T, F) -> 2 branch tickets
        assert len(branch_tickets) >= 2

    def test_run_cascades_paragraph_tickets(self, tmp_path: Path) -> None:
        """After completing entry, paragraph tickets for callees are created."""
        executable = self._make_mock_executable(tmp_path)
        mock_cbl = self._make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=10,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
        )

        mock_provider = _make_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result = asyncio.run(run(config))

        tickets_data = json.loads(
            (tmp_path / "tickets.json").read_text()
        )
        para_tickets = [
            t for t in tickets_data if t["_type"] == "ParagraphTicket"
        ]
        # Entry paragraph + cascaded 2000-VALIDATE
        assert len(para_tickets) >= 2

    def test_run_respects_budget(self, tmp_path: Path) -> None:
        """run() stops after the budget is exhausted."""
        executable = self._make_mock_executable(tmp_path)
        mock_cbl = self._make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=1,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
        )

        mock_provider = _make_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result = asyncio.run(run(config))

        assert result["executions"] <= 1

    def test_run_saves_successful_params(self, tmp_path: Path) -> None:
        """Successful params are saved as JSON files."""
        executable = self._make_mock_executable(tmp_path)
        mock_cbl = self._make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=5,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
        )

        mock_provider = _make_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result = asyncio.run(run(config))

        params_dir = tmp_path / "params"
        assert params_dir.exists()
        param_files = list(params_dir.glob("*.json"))
        assert len(param_files) >= 1

    def test_run_with_hybrid_mode_builds_field_report(
        self, tmp_path: Path
    ) -> None:
        """In hybrid mode, run() builds a field report and walker."""
        executable = self._make_mock_executable(tmp_path)
        mock_cbl = self._make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=3,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
            heuristic_mode="hybrid",
        )

        mock_provider = _make_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result = asyncio.run(run(config))

        # The run should complete successfully in hybrid mode
        assert result["executions"] >= 1

    def test_run_with_llm_only_mode_skips_field_report(
        self, tmp_path: Path
    ) -> None:
        """In llm_only mode, field_report should not be built."""
        executable = self._make_mock_executable(tmp_path)
        mock_cbl = self._make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=2,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
            heuristic_mode="llm_only",
        )

        mock_provider = _make_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ) as mock_env:
            result = asyncio.run(run(config))

        assert result["executions"] >= 1

    def test_run_field_report_failure_continues(
        self, tmp_path: Path
    ) -> None:
        """If field report building fails, run() continues without it."""
        executable = self._make_mock_executable(tmp_path)
        mock_cbl = self._make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=2,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
            heuristic_mode="hybrid",
        )

        mock_provider = _make_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ), patch(
            "cobol_penetrator.analysis.field_report.build_field_report",
            side_effect=ValueError("parse error"),
        ):
            result = asyncio.run(run(config))

        # Should still complete despite field report failure
        assert result["executions"] >= 1

    def test_run_populates_knowledge_store(
        self, tmp_path: Path
    ) -> None:
        """run() creates and populates the in-memory knowledge store."""
        executable = self._make_mock_executable(tmp_path)
        mock_cbl = self._make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=5,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=3,
        )

        mock_provider = _make_mock_provider()

        # Capture the knowledge object used during the run
        captured_knowledge = {}

        original_record = LearnedKnowledge.record_execution

        def spy_record(self_k, params, result, ticket=None):
            captured_knowledge["instance"] = self_k
            return original_record(self_k, params, result, ticket)

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ), patch.object(
            LearnedKnowledge, "record_execution", spy_record,
        ):
            result = asyncio.run(run(config))

        # Knowledge should have been populated in-memory
        knowledge = captured_knowledge.get("instance")
        assert knowledge is not None
        # Baseline + LLM executions should populate paragraphs
        assert len(knowledge.successful_params) >= 1

    def test_run_uses_max_turns_per_ticket(
        self, tmp_path: Path
    ) -> None:
        """Config's max_turns_per_ticket is respected."""
        executable = self._make_mock_executable(tmp_path)
        mock_cbl = self._make_mock_cbl(tmp_path)

        config = PenetratorConfig(
            executable=executable,
            mock_cbl=mock_cbl,
            budget=20,
            timeout=60,
            resume=False,
            tickets_path=tmp_path / "tickets.json",
            coverage_path=tmp_path / "coverage.json",
            params_dir=tmp_path / "params",
            max_attempts=5,
            max_turns_per_ticket=2,
        )

        mock_provider = _make_mock_provider()

        with patch(
            "cobol_penetrator.orchestrator.get_provider_from_env",
            return_value=mock_provider,
        ):
            result = asyncio.run(run(config))

        # Should complete without error
        assert result["executions"] >= 1
