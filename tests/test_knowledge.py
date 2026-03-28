"""Tests for cobol_penetrator.knowledge — shared knowledge store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cobol_penetrator.knowledge import LearnedKnowledge
from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket
from cobol_penetrator.trace_parser import ExecutionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    paragraphs_hit: list[str] | None = None,
    branches_hit: dict[str, str] | None = None,
    call_chain: list[tuple[str, str]] | None = None,
    variable_snapshots: dict[str, dict[str, str]] | None = None,
    mock_ops: list[str] | None = None,
) -> ExecutionResult:
    """Build an ExecutionResult with sensible defaults."""
    return ExecutionResult(
        paragraphs_hit=paragraphs_hit or [],
        branches_hit=branches_hit or {},
        call_chain=call_chain or [],
        variable_snapshots=variable_snapshots or {},
        mock_ops=mock_ops or [],
    )


# ---------------------------------------------------------------------------
# Tests: LearnedKnowledge creation and defaults
# ---------------------------------------------------------------------------


class TestLearnedKnowledgeCreation:
    """Verify initial state and basic construction."""

    def test_empty_on_creation(self) -> None:
        k = LearnedKnowledge()
        assert k.successful_params == {}
        assert k.branch_params == {}
        assert k.variable_observations == {}
        assert k.stub_outcomes == {}
        assert k.failed_attempts == {}
        assert k.call_path_params == {}

    def test_construction_with_data(self) -> None:
        k = LearnedKnowledge(
            successful_params={"PARA-A": {"input_state": {"X": "1"}}},
        )
        assert "PARA-A" in k.successful_params


# ---------------------------------------------------------------------------
# Tests: record_execution
# ---------------------------------------------------------------------------


class TestRecordExecution:
    """Verify record_execution populates all knowledge sections."""

    def test_records_paragraph_hits(self) -> None:
        k = LearnedKnowledge()
        result = _make_result(paragraphs_hit=["1000-MAIN", "2000-VALIDATE"])
        params = {"input_state": {"X": "1"}, "stubs": {}}
        k.record_execution(params, result)

        assert "1000-MAIN" in k.successful_params
        assert "2000-VALIDATE" in k.successful_params
        assert k.successful_params["1000-MAIN"]["input_state"]["X"] == "1"

    def test_records_branch_hits(self) -> None:
        k = LearnedKnowledge()
        result = _make_result(branches_hit={"1": "T", "2": "F"})
        params = {"input_state": {}, "stubs": {}}
        k.record_execution(params, result)

        assert "1:T" in k.branch_params
        assert "2:F" in k.branch_params

    def test_records_variable_observations(self) -> None:
        k = LearnedKnowledge()
        result = _make_result(
            variable_snapshots={"1": {"WS-STATUS": "00", "WS-FLAG": "Y"}}
        )
        k.record_execution({"input_state": {}, "stubs": {}}, result)

        assert "WS-STATUS" in k.variable_observations
        assert "00" in k.variable_observations["WS-STATUS"]
        assert "Y" in k.variable_observations["WS-FLAG"]

    def test_deduplicates_variable_observations(self) -> None:
        k = LearnedKnowledge()
        result = _make_result(
            variable_snapshots={"1": {"WS-STATUS": "00"}}
        )
        k.record_execution({"input_state": {}, "stubs": {}}, result)
        k.record_execution({"input_state": {}, "stubs": {}}, result)

        assert k.variable_observations["WS-STATUS"] == ["00"]

    def test_records_call_chain(self) -> None:
        k = LearnedKnowledge()
        result = _make_result(
            call_chain=[("1000-MAIN", "2000-VALIDATE")]
        )
        params = {"input_state": {"X": "1"}, "stubs": {}}
        k.record_execution(params, result)

        assert "1000-MAIN->2000-VALIDATE" in k.call_path_params

    def test_records_mock_ops(self) -> None:
        k = LearnedKnowledge()
        result = _make_result(mock_ops=["READ-ACCOUNT", "WRITE-LOG"])
        k.record_execution({"input_state": {}, "stubs": {}}, result)

        assert "READ-ACCOUNT" in k.stub_outcomes
        assert "WRITE-LOG" in k.stub_outcomes

    def test_does_not_overwrite_existing_params(self) -> None:
        """First success for a paragraph should persist."""
        k = LearnedKnowledge()
        params1 = {"input_state": {"X": "1"}, "stubs": {}}
        params2 = {"input_state": {"X": "2"}, "stubs": {}}
        result = _make_result(paragraphs_hit=["1000-MAIN"])

        k.record_execution(params1, result)
        k.record_execution(params2, result)

        assert k.successful_params["1000-MAIN"]["input_state"]["X"] == "1"


# ---------------------------------------------------------------------------
# Tests: failure recording
# ---------------------------------------------------------------------------


class TestFailureRecording:
    """Verify failed attempts are recorded correctly."""

    def test_records_paragraph_miss(self) -> None:
        k = LearnedKnowledge()
        ticket = ParagraphTicket(
            id="PARA-3000-PROCESS",
            paragraph="3000-PROCESS",
        )
        result = _make_result(paragraphs_hit=["1000-MAIN"])
        params = {"input_state": {"X": "1"}, "stubs": {}}

        k.record_execution(params, result, ticket)

        assert "3000-PROCESS" in k.failed_attempts
        assert len(k.failed_attempts["3000-PROCESS"]) == 1
        assert k.failed_attempts["3000-PROCESS"][0]["params"] == params

    def test_records_branch_miss(self) -> None:
        k = LearnedKnowledge()
        ticket = BranchTicket(
            id="BRANCH-5-T",
            branch_id="5",
            direction="T",
            paragraph="1000-MAIN",
        )
        result = _make_result(branches_hit={"5": "F"})
        params = {"input_state": {}, "stubs": {}}

        k.record_execution(params, result, ticket)

        assert "BRANCH-5" in k.failed_attempts
        assert len(k.failed_attempts["BRANCH-5"]) == 1

    def test_does_not_record_success_as_failure(self) -> None:
        k = LearnedKnowledge()
        ticket = ParagraphTicket(
            id="PARA-1000-MAIN",
            paragraph="1000-MAIN",
        )
        result = _make_result(paragraphs_hit=["1000-MAIN"])
        k.record_execution({"input_state": {}, "stubs": {}}, result, ticket)

        assert "1000-MAIN" not in k.failed_attempts

    def test_caps_failures_at_20(self) -> None:
        k = LearnedKnowledge()
        ticket = ParagraphTicket(
            id="PARA-HARD",
            paragraph="HARD",
        )
        result = _make_result(paragraphs_hit=["1000-MAIN"])

        for i in range(25):
            params = {"input_state": {"X": str(i)}, "stubs": {}}
            k.record_execution(params, result, ticket)

        assert len(k.failed_attempts["HARD"]) == 20

    def test_no_ticket_no_failure_recorded(self) -> None:
        k = LearnedKnowledge()
        result = _make_result(paragraphs_hit=["1000-MAIN"])
        k.record_execution({"input_state": {}, "stubs": {}}, result)

        assert k.failed_attempts == {}


# ---------------------------------------------------------------------------
# Tests: get_parent_params
# ---------------------------------------------------------------------------


class TestGetParentParams:
    """Verify parent parameter lookup along call paths."""

    def test_returns_direct_parent(self) -> None:
        k = LearnedKnowledge()
        k.successful_params["1000-MAIN"] = {"input_state": {"X": "1"}, "stubs": {}}
        k.successful_params["2000-VALIDATE"] = {"input_state": {"X": "2"}, "stubs": {}}

        result = k.get_parent_params(
            ["1000-MAIN", "2000-VALIDATE", "3000-PROCESS"]
        )
        assert result is not None
        assert result["input_state"]["X"] == "2"

    def test_returns_nearest_parent(self) -> None:
        k = LearnedKnowledge()
        k.successful_params["1000-MAIN"] = {"input_state": {"X": "1"}, "stubs": {}}
        # 2000-VALIDATE is NOT in successful_params

        result = k.get_parent_params(
            ["1000-MAIN", "2000-VALIDATE", "3000-PROCESS"]
        )
        assert result is not None
        assert result["input_state"]["X"] == "1"

    def test_returns_none_when_no_parent_matches(self) -> None:
        k = LearnedKnowledge()
        result = k.get_parent_params(["1000-MAIN", "2000-VALIDATE"])
        assert result is None

    def test_returns_none_for_single_element_path(self) -> None:
        k = LearnedKnowledge()
        k.successful_params["1000-MAIN"] = {"input_state": {"X": "1"}, "stubs": {}}
        result = k.get_parent_params(["1000-MAIN"])
        assert result is None

    def test_returns_none_for_empty_path(self) -> None:
        k = LearnedKnowledge()
        result = k.get_parent_params([])
        assert result is None

    def test_returns_copy_not_reference(self) -> None:
        k = LearnedKnowledge()
        original = {"input_state": {"X": "1"}, "stubs": {}}
        k.successful_params["1000-MAIN"] = original

        result = k.get_parent_params(["1000-MAIN", "2000-VALIDATE"])
        assert result is not None
        result["input_state"]["X"] = "MODIFIED"
        # Original should be unchanged
        assert k.successful_params["1000-MAIN"]["input_state"]["X"] == "1"


# ---------------------------------------------------------------------------
# Tests: get_sibling_branch_params
# ---------------------------------------------------------------------------


class TestGetSiblingBranchParams:
    """Verify sibling branch parameter lookup."""

    def test_returns_all_directions(self) -> None:
        k = LearnedKnowledge()
        k.branch_params["1:T"] = {"input_state": {"X": "1"}, "stubs": {}}
        k.branch_params["1:F"] = {"input_state": {"X": "2"}, "stubs": {}}
        k.branch_params["2:T"] = {"input_state": {"X": "3"}, "stubs": {}}

        result = k.get_sibling_branch_params("1")
        assert len(result) == 2
        assert "1:T" in result
        assert "1:F" in result
        assert "2:T" not in result

    def test_returns_empty_when_no_match(self) -> None:
        k = LearnedKnowledge()
        k.branch_params["1:T"] = {"input_state": {}, "stubs": {}}

        result = k.get_sibling_branch_params("99")
        assert result == {}

    def test_returns_empty_when_no_branches(self) -> None:
        k = LearnedKnowledge()
        result = k.get_sibling_branch_params("1")
        assert result == {}


# ---------------------------------------------------------------------------
# Tests: save / load round-trip
# ---------------------------------------------------------------------------


class TestPersistence:
    """Verify save/load preserves knowledge data."""

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        k = LearnedKnowledge()
        k.successful_params["1000-MAIN"] = {
            "input_state": {"X": "1"},
            "stubs": {},
        }
        k.branch_params["1:T"] = {"input_state": {}, "stubs": {}}
        k.variable_observations["WS-STATUS"] = ["00", "10"]
        k.stub_outcomes["READ-ACCOUNT"] = []
        k.call_path_params["A->B"] = {"input_state": {}, "stubs": {}}
        k.failed_attempts["HARD"] = [
            {"params": {}, "paragraphs_hit": []}
        ]

        path = tmp_path / "knowledge.json"
        k.save(path)

        loaded = LearnedKnowledge.load(path)

        assert loaded.successful_params == k.successful_params
        assert loaded.branch_params == k.branch_params
        assert loaded.variable_observations == k.variable_observations
        assert loaded.stub_outcomes == k.stub_outcomes
        assert loaded.call_path_params == k.call_path_params
        # failed_attempts are NOT persisted
        assert loaded.failed_attempts == {}

    def test_load_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        loaded = LearnedKnowledge.load(path)
        assert loaded.successful_params == {}

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "knowledge.json"
        k = LearnedKnowledge()
        k.save(path)
        assert path.exists()

    def test_load_corrupted_file_returns_empty(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not valid json{{{", encoding="utf-8")
        loaded = LearnedKnowledge.load(path)
        assert loaded.successful_params == {}

    def test_load_partial_data(self, tmp_path: Path) -> None:
        """Loading a file missing some keys should fill with defaults."""
        path = tmp_path / "partial.json"
        path.write_text(
            json.dumps({"successful_params": {"A": {"x": 1}}}),
            encoding="utf-8",
        )
        loaded = LearnedKnowledge.load(path)
        assert loaded.successful_params == {"A": {"x": 1}}
        assert loaded.branch_params == {}
        assert loaded.variable_observations == {}

    def test_save_file_is_valid_json(self, tmp_path: Path) -> None:
        k = LearnedKnowledge()
        k.successful_params["P"] = {"input_state": {}, "stubs": {}}
        path = tmp_path / "knowledge.json"
        k.save(path)

        data = json.loads(path.read_text(encoding="utf-8"))
        assert "successful_params" in data
        assert "P" in data["successful_params"]
