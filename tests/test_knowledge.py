"""Tests for cobol_penetrator.knowledge — within-run knowledge store."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from cobol_penetrator.knowledge import LearnedKnowledge
from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket


@dataclass
class _MockResult:
    paragraphs_hit: list[str] = field(default_factory=list)
    branches_hit: dict[str, str] = field(default_factory=dict)
    call_chain: list[tuple[str, str]] = field(default_factory=list)
    variable_snapshots: dict[str, dict[str, str]] = field(default_factory=dict)
    mock_ops: list[str] = field(default_factory=list)


class TestCreation:
    def test_empty(self) -> None:
        k = LearnedKnowledge()
        assert k.successful_params == {}
        assert k.failed_attempts == {}


class TestRecordExecution:
    def test_records_successful_params(self) -> None:
        k = LearnedKnowledge()
        result = _MockResult(paragraphs_hit=["MAIN-PARA", "1000-EXIT"])
        k.record_execution({"input_state": {"X": "1"}, "stubs": {}}, result)
        assert "MAIN-PARA" in k.successful_params
        assert "1000-EXIT" in k.successful_params

    def test_first_params_win(self) -> None:
        k = LearnedKnowledge()
        r1 = _MockResult(paragraphs_hit=["MAIN-PARA"])
        r2 = _MockResult(paragraphs_hit=["MAIN-PARA"])
        k.record_execution({"input_state": {"X": "1"}, "stubs": {}}, r1)
        k.record_execution({"input_state": {"X": "2"}, "stubs": {}}, r2)
        assert k.successful_params["MAIN-PARA"]["input_state"]["X"] == "1"

    def test_records_failure(self) -> None:
        k = LearnedKnowledge()
        ticket = ParagraphTicket(id="PARA-DEEP-PARA", paragraph="DEEP-PARA")
        result = _MockResult(paragraphs_hit=["MAIN-PARA"])
        k.record_execution({"input_state": {}, "stubs": {}}, result, ticket)
        assert "DEEP-PARA" in k.failed_attempts
        assert len(k.failed_attempts["DEEP-PARA"]) == 1

    def test_failure_cap(self) -> None:
        k = LearnedKnowledge()
        ticket = ParagraphTicket(id="PARA-DEEP-PARA", paragraph="DEEP-PARA")
        for i in range(15):
            result = _MockResult(paragraphs_hit=["MAIN-PARA"])
            k.record_execution({"input_state": {"i": str(i)}, "stubs": {}}, result, ticket)
        assert len(k.failed_attempts["DEEP-PARA"]) == 10

    def test_no_failure_on_hit(self) -> None:
        k = LearnedKnowledge()
        ticket = ParagraphTicket(id="PARA-MAIN-PARA", paragraph="MAIN-PARA")
        result = _MockResult(paragraphs_hit=["MAIN-PARA"])
        k.record_execution({"input_state": {}, "stubs": {}}, result, ticket)
        assert "MAIN-PARA" not in k.failed_attempts

    def test_branch_failure(self) -> None:
        k = LearnedKnowledge()
        ticket = BranchTicket(
            id="BRANCH-5-F", branch_id="5", direction="F", paragraph="MAIN-PARA"
        )
        result = _MockResult(paragraphs_hit=["MAIN-PARA"], branches_hit={"5": "T"})
        k.record_execution({"input_state": {}, "stubs": {}}, result, ticket)
        assert "BRANCH-5-F" in k.failed_attempts


class TestGetParentParams:
    def test_returns_parent(self) -> None:
        k = LearnedKnowledge()
        k.successful_params["MAIN-PARA"] = {"input_state": {"X": "1"}, "stubs": {}}
        result = k.get_parent_params(["MAIN-PARA", "DEEP-PARA"])
        assert result is not None
        assert result["input_state"]["X"] == "1"

    def test_returns_nearest_parent(self) -> None:
        k = LearnedKnowledge()
        k.successful_params["MAIN-PARA"] = {"input_state": {"X": "1"}, "stubs": {}}
        k.successful_params["MID-PARA"] = {"input_state": {"X": "2"}, "stubs": {}}
        result = k.get_parent_params(["MAIN-PARA", "MID-PARA", "DEEP-PARA"])
        assert result["input_state"]["X"] == "2"

    def test_returns_none_for_short_path(self) -> None:
        k = LearnedKnowledge()
        assert k.get_parent_params(["MAIN-PARA"]) is None
        assert k.get_parent_params([]) is None

    def test_returns_none_when_no_parent_done(self) -> None:
        k = LearnedKnowledge()
        assert k.get_parent_params(["A", "B", "C"]) is None

    def test_deep_copy(self) -> None:
        k = LearnedKnowledge()
        k.successful_params["MAIN-PARA"] = {"input_state": {"X": "1"}, "stubs": {}}
        result = k.get_parent_params(["MAIN-PARA", "DEEP-PARA"])
        result["input_state"]["X"] = "MUTATED"
        assert k.successful_params["MAIN-PARA"]["input_state"]["X"] == "1"


class TestGetFailedParams:
    def test_returns_failures(self) -> None:
        k = LearnedKnowledge()
        k.failed_attempts["DEEP-PARA"] = [{"input_state": {"X": "1"}}]
        assert len(k.get_failed_params("DEEP-PARA")) == 1

    def test_returns_empty_for_unknown(self) -> None:
        k = LearnedKnowledge()
        assert k.get_failed_params("UNKNOWN") == []
