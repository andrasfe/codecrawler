"""Tests for cobol_penetrator.evoskill_feedback."""

from __future__ import annotations

from cobol_penetrator.evoskill_feedback import (
    build_failure_feedback,
    build_stub_discovery_feedback,
    build_success_feedback,
)
from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket
from cobol_penetrator.trace_parser import ExecutionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _para_ticket() -> ParagraphTicket:
    return ParagraphTicket(
        id="PARA-2000-VALIDATE",
        paragraph="2000-VALIDATE",
        call_path=["1000-MAIN", "2000-VALIDATE"],
    )


def _branch_ticket() -> BranchTicket:
    return BranchTicket(
        id="BRANCH-1-F",
        branch_id="1",
        direction="F",
        paragraph="1000-MAIN",
        condition_text="WS-STATUS = '00'",
        condition_vars=["WS-STATUS"],
    )


def _exec_result(**kwargs) -> ExecutionResult:
    defaults = {
        "paragraphs_hit": ["1000-MAIN", "2000-VALIDATE"],
        "branches_hit": {"1": "T"},
        "variable_snapshots": {"1": {"WS-STATUS": "00"}},
    }
    defaults.update(kwargs)
    return ExecutionResult(**defaults)


# ---------------------------------------------------------------------------
# Tests: build_success_feedback
# ---------------------------------------------------------------------------


class TestBuildSuccessFeedback:
    """Verify success feedback construction."""

    def test_paragraph_ticket_keys(self) -> None:
        fb = build_success_feedback(
            _para_ticket(),
            {"input_state": {"WS-STATUS": "00"}, "stubs": {}},
            _exec_result(),
        )
        assert "input_prompt" in fb
        assert "agent_output" in fb
        assert "reviewer_feedback" in fb

    def test_paragraph_ticket_mentions_target(self) -> None:
        fb = build_success_feedback(
            _para_ticket(),
            {"input_state": {}, "stubs": {}},
            _exec_result(),
        )
        assert "2000-VALIDATE" in fb["input_prompt"]
        assert "SUCCESS" in fb["reviewer_feedback"]

    def test_branch_ticket_keys(self) -> None:
        fb = build_success_feedback(
            _branch_ticket(),
            {"input_state": {"WS-STATUS": "GE"}, "stubs": {}},
            _exec_result(branches_hit={"1": "F"}),
        )
        assert "input_prompt" in fb
        assert "agent_output" in fb
        assert "reviewer_feedback" in fb

    def test_branch_ticket_mentions_direction(self) -> None:
        fb = build_success_feedback(
            _branch_ticket(),
            {"input_state": {"WS-STATUS": "GE"}, "stubs": {}},
            _exec_result(branches_hit={"1": "F"}),
        )
        assert "F" in fb["reviewer_feedback"]
        assert "branch" in fb["input_prompt"].lower()

    def test_branch_ticket_includes_condition(self) -> None:
        fb = build_success_feedback(
            _branch_ticket(),
            {"input_state": {}, "stubs": {}},
            _exec_result(),
        )
        assert "WS-STATUS" in fb["input_prompt"]


# ---------------------------------------------------------------------------
# Tests: build_failure_feedback
# ---------------------------------------------------------------------------


class TestBuildFailureFeedback:
    """Verify failure feedback construction."""

    def test_paragraph_ticket_keys(self) -> None:
        fb = build_failure_feedback(_para_ticket(), 3, None)
        assert "input_prompt" in fb
        assert "agent_output" in fb
        assert "reviewer_feedback" in fb

    def test_paragraph_ticket_mentions_failure(self) -> None:
        fb = build_failure_feedback(
            _para_ticket(), 5, _exec_result(paragraphs_hit=["1000-MAIN"]),
        )
        assert "FAILURE" in fb["reviewer_feedback"]
        assert "2000-VALIDATE" in fb["reviewer_feedback"]
        assert "5" in fb["reviewer_feedback"]

    def test_paragraph_ticket_none_result(self) -> None:
        fb = build_failure_feedback(_para_ticket(), 3, None)
        assert "FAILURE" in fb["reviewer_feedback"]
        assert "[]" in fb["reviewer_feedback"]

    def test_branch_ticket_mentions_condition_vars(self) -> None:
        fb = build_failure_feedback(_branch_ticket(), 4, None)
        assert "WS-STATUS" in fb["reviewer_feedback"]
        assert "FAILURE" in fb["reviewer_feedback"]

    def test_attempt_count_in_output(self) -> None:
        fb = build_failure_feedback(_para_ticket(), 7, None)
        assert "7" in fb["agent_output"]


# ---------------------------------------------------------------------------
# Tests: build_stub_discovery_feedback
# ---------------------------------------------------------------------------


class TestBuildStubDiscoveryFeedback:
    """Verify stub discovery feedback construction."""

    def test_keys_present(self) -> None:
        fb = build_stub_discovery_feedback("GE", 3, "READ-ACCOUNT", 2)
        assert "input_prompt" in fb
        assert "agent_output" in fb
        assert "reviewer_feedback" in fb

    def test_contains_fault_value(self) -> None:
        fb = build_stub_discovery_feedback("GE", 3, "READ-ACCOUNT", 2)
        assert "GE" in fb["agent_output"]
        assert "GE" in fb["reviewer_feedback"]

    def test_contains_position(self) -> None:
        fb = build_stub_discovery_feedback("23", 5, "WRITE-FILE", 4)
        assert "5" in fb["agent_output"]
        assert "5" in fb["reviewer_feedback"]

    def test_contains_operation(self) -> None:
        fb = build_stub_discovery_feedback("10", 1, "SQL-SELECT", 3)
        assert "SQL-SELECT" in fb["agent_output"]

    def test_contains_branch_count(self) -> None:
        fb = build_stub_discovery_feedback("GE", 0, "OP", 7)
        assert "7" in fb["reviewer_feedback"]
