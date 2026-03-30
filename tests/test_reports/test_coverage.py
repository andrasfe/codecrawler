"""Tests for CoverageTracker and CoverageState."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cobol_penetrator.mock_reader import BranchInfo, ParagraphInfo, ProgramStructure
from cobol_penetrator.reports.coverage import CoverageState, CoverageTracker
from cobol_penetrator.trace_parser import ExecutionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_structure(
    paragraphs: dict[str, ParagraphInfo] | None = None,
    branches: dict[str, BranchInfo] | None = None,
) -> ProgramStructure:
    """Build a minimal ProgramStructure for testing."""
    if paragraphs is None:
        paragraphs = {
            "1000-MAIN": ParagraphInfo(
                name="1000-MAIN",
                line_start=1,
                line_end=10,
                source_code="1000-MAIN.\n   ...",
                branches=["1"],
                performs=["2000-VALIDATE"],
            ),
            "2000-VALIDATE": ParagraphInfo(
                name="2000-VALIDATE",
                line_start=11,
                line_end=20,
                source_code="2000-VALIDATE.\n   ...",
                branches=["2"],
                performs=[],
            ),
            "3000-PROCESS": ParagraphInfo(
                name="3000-PROCESS",
                line_start=21,
                line_end=30,
                source_code="3000-PROCESS.\n   ...",
            ),
        }
    if branches is None:
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
    entry = next(iter(paragraphs), "")
    return ProgramStructure(
        entry_paragraph=entry,
        paragraphs=paragraphs,
        branches=branches,
        call_graph={name: info.performs for name, info in paragraphs.items()},
    )


def _make_result(
    paragraphs_hit: list[str] | None = None,
    branches_hit: dict[str, str] | None = None,
) -> ExecutionResult:
    """Build a minimal ExecutionResult for testing."""
    return ExecutionResult(
        paragraphs_hit=paragraphs_hit or [],
        branches_hit=branches_hit or {},
    )


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestCoverageTrackerInit:
    """Tests for CoverageTracker.__init__."""

    def test_empty_structure(self) -> None:
        """Tracker with no paragraphs or branches starts at 0."""
        structure = _make_structure(paragraphs={}, branches={})
        tracker = CoverageTracker(structure)
        assert tracker.state.total_paragraphs == 0
        assert tracker.state.total_branches == 0
        assert tracker.coverage_pct == 0.0

    def test_counts_paragraphs(self) -> None:
        """Tracker counts paragraphs from the structure."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        assert tracker.state.total_paragraphs == 3

    def test_counts_branch_directions(self) -> None:
        """Tracker counts total branch directions, not just branch IDs."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        # 2 branches x 2 directions each = 4
        assert tracker.state.total_branches == 4

    def test_initial_coverage_zero(self) -> None:
        """Coverage starts at 0% before any updates."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        assert tracker.coverage_pct == 0.0
        assert tracker.state.hit_paragraphs == []
        assert tracker.state.hit_branches == {}
        assert tracker.state.history == []


# ---------------------------------------------------------------------------
# Tests: Update
# ---------------------------------------------------------------------------


class TestCoverageTrackerUpdate:
    """Tests for CoverageTracker.update."""

    def test_single_paragraph_hit(self) -> None:
        """Hitting one paragraph increases coverage."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        result = _make_result(paragraphs_hit=["1000-MAIN"])
        tracker.update(result)
        assert "1000-MAIN" in tracker.state.hit_paragraphs
        assert tracker.coverage_pct > 0.0

    def test_single_branch_hit(self) -> None:
        """Hitting one branch direction increases coverage."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        result = _make_result(branches_hit={"1": "T"})
        tracker.update(result)
        assert "1:T" in tracker.state.hit_branches
        assert tracker.coverage_pct > 0.0

    def test_combined_hit(self) -> None:
        """Hitting paragraphs and branches together is additive."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        result = _make_result(
            paragraphs_hit=["1000-MAIN"],
            branches_hit={"1": "T"},
        )
        tracker.update(result)
        # 3 paragraphs + 4 branch directions = 7 total
        # 1 paragraph + 1 branch direction = 2 hit
        expected = round((2 / 7) * 100.0, 2)
        assert tracker.coverage_pct == expected

    def test_duplicate_paragraphs_not_double_counted(self) -> None:
        """Same paragraph hit twice should not be counted twice."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)

        result1 = _make_result(paragraphs_hit=["1000-MAIN"])
        tracker.update(result1)
        pct_after_first = tracker.coverage_pct

        result2 = _make_result(paragraphs_hit=["1000-MAIN"])
        tracker.update(result2)
        assert tracker.coverage_pct == pct_after_first
        assert tracker.state.hit_paragraphs.count("1000-MAIN") == 1

    def test_duplicate_branches_not_double_counted(self) -> None:
        """Same branch direction hit twice should not be counted twice."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)

        result1 = _make_result(branches_hit={"1": "T"})
        tracker.update(result1)
        pct_after_first = tracker.coverage_pct

        result2 = _make_result(branches_hit={"1": "T"})
        tracker.update(result2)
        assert tracker.coverage_pct == pct_after_first

    def test_different_directions_same_branch(self) -> None:
        """Hitting T then F for the same branch ID counts as 2 hits."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)

        tracker.update(_make_result(branches_hit={"1": "T"}))
        pct_after_t = tracker.coverage_pct

        tracker.update(_make_result(branches_hit={"1": "F"}))
        assert tracker.coverage_pct > pct_after_t
        assert "1:T" in tracker.state.hit_branches
        assert "1:F" in tracker.state.hit_branches


# ---------------------------------------------------------------------------
# Tests: Coverage percentage calculation
# ---------------------------------------------------------------------------


class TestCoveragePercentage:
    """Tests for coverage_pct property and calculation edge cases."""

    def test_zero_when_empty_structure(self) -> None:
        """Coverage is 0% for an empty structure even after update."""
        structure = _make_structure(paragraphs={}, branches={})
        tracker = CoverageTracker(structure)
        tracker.update(_make_result())
        assert tracker.coverage_pct == 0.0

    def test_full_coverage(self) -> None:
        """Coverage reaches 100% when everything is hit."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        result = _make_result(
            paragraphs_hit=["1000-MAIN", "2000-VALIDATE", "3000-PROCESS"],
            branches_hit={"1": "T", "2": "F"},
        )
        tracker.update(result)
        # Need all 4 branch directions. First update hits 2.
        result2 = _make_result(
            branches_hit={"1": "F", "2": "T"},
        )
        tracker.update(result2)
        assert tracker.coverage_pct == 100.0


# ---------------------------------------------------------------------------
# Tests: History tracking
# ---------------------------------------------------------------------------


class TestCoverageHistory:
    """Tests for history tracking in CoverageTracker."""

    def test_history_grows_with_updates(self) -> None:
        """Each update appends exactly one entry to history."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        assert len(tracker.state.history) == 0

        tracker.update(_make_result(paragraphs_hit=["1000-MAIN"]))
        assert len(tracker.state.history) == 1

        tracker.update(_make_result(paragraphs_hit=["2000-VALIDATE"]))
        assert len(tracker.state.history) == 2

    def test_history_contains_iteration_and_pct(self) -> None:
        """Each history entry has iteration number and coverage_pct."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        tracker.update(_make_result(paragraphs_hit=["1000-MAIN"]))
        entry = tracker.state.history[0]
        assert "iteration" in entry
        assert "coverage_pct" in entry
        assert entry["iteration"] == 1

    def test_history_iterations_are_sequential(self) -> None:
        """Iteration numbers are 1-based and sequential."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        for para in ["1000-MAIN", "2000-VALIDATE", "3000-PROCESS"]:
            tracker.update(_make_result(paragraphs_hit=[para]))

        iterations = [e["iteration"] for e in tracker.state.history]
        assert iterations == [1, 2, 3]

    def test_monotonic_coverage_increase(self) -> None:
        """Coverage percentage never decreases across iterations."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)

        tracker.update(_make_result(paragraphs_hit=["1000-MAIN"]))
        tracker.update(
            _make_result(
                paragraphs_hit=["2000-VALIDATE"],
                branches_hit={"1": "T"},
            )
        )
        tracker.update(_make_result(branches_hit={"2": "F"}))
        # Repeat with no new hits — should not decrease.
        tracker.update(_make_result())

        pcts = [e["coverage_pct"] for e in tracker.state.history]
        for i in range(1, len(pcts)):
            assert pcts[i] >= pcts[i - 1], (
                f"Coverage decreased from {pcts[i-1]} to {pcts[i]} "
                f"at iteration {i+1}"
            )


# ---------------------------------------------------------------------------
# Tests: Save / Load round-trip
# ---------------------------------------------------------------------------


class TestCoveragePersistence:
    """Tests for save() and load() round-trip."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save() writes a valid JSON file."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        tracker.update(_make_result(paragraphs_hit=["1000-MAIN"]))

        out_path = tmp_path / "coverage.json"
        tracker.save(out_path)
        assert out_path.exists()

        data = json.loads(out_path.read_text())
        assert data["total_paragraphs"] == 3
        assert "1000-MAIN" in data["hit_paragraphs"]

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """save() creates parent directories if needed."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        out_path = tmp_path / "deep" / "nested" / "coverage.json"
        tracker.save(out_path)
        assert out_path.exists()

    def test_round_trip(self, tmp_path: Path) -> None:
        """load() restores the same state that save() wrote."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        tracker.update(
            _make_result(
                paragraphs_hit=["1000-MAIN", "2000-VALIDATE"],
                branches_hit={"1": "T"},
            )
        )
        tracker.update(
            _make_result(branches_hit={"2": "F"}),
        )

        path = tmp_path / "coverage.json"
        tracker.save(path)

        loaded = CoverageTracker.load(path, structure)
        assert loaded.coverage_pct == tracker.coverage_pct
        assert loaded.state.hit_paragraphs == tracker.state.hit_paragraphs
        assert loaded.state.hit_branches == tracker.state.hit_branches
        assert len(loaded.state.history) == len(tracker.state.history)

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        """load() raises FileNotFoundError for missing files."""
        structure = _make_structure()
        with pytest.raises(FileNotFoundError):
            CoverageTracker.load(tmp_path / "nope.json", structure)

    def test_load_restores_iteration_counter(self, tmp_path: Path) -> None:
        """After load, new updates continue iteration numbering."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        tracker.update(_make_result(paragraphs_hit=["1000-MAIN"]))
        tracker.update(_make_result(paragraphs_hit=["2000-VALIDATE"]))

        path = tmp_path / "coverage.json"
        tracker.save(path)

        loaded = CoverageTracker.load(path, structure)
        loaded.update(_make_result(paragraphs_hit=["3000-PROCESS"]))

        assert loaded.state.history[-1]["iteration"] == 3


# ---------------------------------------------------------------------------
# Tests: Separate paragraph and branch coverage
# ---------------------------------------------------------------------------


class TestSeparateCoverage:
    """Tests for separate paragraph and branch coverage reporting."""

    def test_separate_coverage_calculation(self) -> None:
        """Paragraph and branch coverage are calculated separately."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        
        # Hit 2 out of 3 paragraphs (66.67%)
        # Hit 1 out of 4 branch directions (25.0%)
        result = _make_result(
            paragraphs_hit=["1000-MAIN", "2000-VALIDATE"],
            branches_hit={"1": "T"},
        )
        tracker.update(result)
        
        # Check individual coverage calculations
        assert tracker._calculate_paragraph_pct() == 66.67
        assert tracker._calculate_branch_pct() == 25.0

    def test_separate_coverage_in_saved_json(self, tmp_path: Path) -> None:
        """JSON output includes separate paragraph and branch coverage."""
        structure = _make_structure()
        tracker = CoverageTracker(structure)
        
        # Hit all 3 paragraphs (100%) and 2 out of 4 branch directions (50%)
        result = _make_result(
            paragraphs_hit=["1000-MAIN", "2000-VALIDATE", "3000-PROCESS"],
            branches_hit={"1": "T", "2": "F"},
        )
        tracker.update(result)
        
        out_path = tmp_path / "coverage.json"
        tracker.save(out_path)
        
        data = json.loads(out_path.read_text())
        assert data["paragraph_coverage_pct"] == 100.0
        assert data["branch_coverage_pct"] == 50.0
        assert data["coverage_pct"] == 71.43  # Combined: 5/7 * 100 = 71.43%

    def test_zero_paragraphs_coverage(self) -> None:
        """Paragraph coverage handles zero paragraphs gracefully."""
        structure = _make_structure(paragraphs={})
        tracker = CoverageTracker(structure)
        assert tracker._calculate_paragraph_pct() == 0.0

    def test_zero_branches_coverage(self) -> None:
        """Branch coverage handles zero branches gracefully."""
        structure = _make_structure(branches={})
        tracker = CoverageTracker(structure)
        assert tracker._calculate_branch_pct() == 0.0
