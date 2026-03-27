"""Tests for cobol_penetrator.mock_reader — Stream D.

Validates parsing of .mock.cbl instrumented COBOL source files:
paragraph identification, branch probe extraction, call graph
construction, and helper methods on ProgramStructure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cobol_penetrator.mock_reader import (
    BranchInfo,
    ParagraphInfo,
    ProgramStructure,
    parse_mock_structure,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_MOCK_CBL = FIXTURES_DIR / "sample.mock.cbl"


@pytest.fixture
def structure() -> ProgramStructure:
    """Parse the sample fixture once for use across tests."""
    return parse_mock_structure(SAMPLE_MOCK_CBL)


# ---------------------------------------------------------------------------
# Paragraph discovery tests
# ---------------------------------------------------------------------------

class TestParagraphDiscovery:
    """Verify that all paragraphs are correctly identified."""

    def test_finds_all_four_paragraphs(self, structure: ProgramStructure) -> None:
        assert len(structure.paragraphs) == 4

    def test_paragraph_names(self, structure: ProgramStructure) -> None:
        expected = {"1000-MAIN", "2000-VALIDATE", "3000-PROCESS", "9000-ERROR"}
        assert set(structure.paragraphs.keys()) == expected

    def test_entry_paragraph_is_first(self, structure: ProgramStructure) -> None:
        assert structure.entry_paragraph == "1000-MAIN"

    def test_paragraph_info_types(self, structure: ProgramStructure) -> None:
        for para in structure.paragraphs.values():
            assert isinstance(para, ParagraphInfo)
            assert isinstance(para.line_start, int)
            assert isinstance(para.line_end, int)
            assert para.line_start > 0
            assert para.line_end >= para.line_start

    def test_paragraph_line_ranges_are_contiguous(
        self, structure: ProgramStructure
    ) -> None:
        """Paragraph line ranges should cover all lines without overlap."""
        sorted_paras = sorted(
            structure.paragraphs.values(), key=lambda p: p.line_start
        )
        for i in range(len(sorted_paras) - 1):
            current = sorted_paras[i]
            next_para = sorted_paras[i + 1]
            # Current paragraph ends one line before the next starts
            assert current.line_end == next_para.line_start - 1


# ---------------------------------------------------------------------------
# Branch extraction tests
# ---------------------------------------------------------------------------

class TestBranchExtraction:
    """Verify branch probes are correctly identified and attributed."""

    def test_total_branch_count(self, structure: ProgramStructure) -> None:
        assert len(structure.branches) == 2

    def test_branch_ids(self, structure: ProgramStructure) -> None:
        assert set(structure.branches.keys()) == {"1", "2"}

    def test_branch_1_belongs_to_main(self, structure: ProgramStructure) -> None:
        assert structure.branches["1"].paragraph == "1000-MAIN"

    def test_branch_2_belongs_to_validate(self, structure: ProgramStructure) -> None:
        assert structure.branches["2"].paragraph == "2000-VALIDATE"

    def test_branch_1_directions(self, structure: ProgramStructure) -> None:
        dirs = structure.branches["1"].directions
        assert "T" in dirs
        assert "F" in dirs
        assert len(dirs) == 2

    def test_branch_2_directions(self, structure: ProgramStructure) -> None:
        dirs = structure.branches["2"].directions
        assert "T" in dirs
        assert "F" in dirs
        assert len(dirs) == 2

    def test_branch_info_types(self, structure: ProgramStructure) -> None:
        for branch in structure.branches.values():
            assert isinstance(branch, BranchInfo)
            assert isinstance(branch.id, str)
            assert isinstance(branch.paragraph, str)
            assert isinstance(branch.directions, list)


# ---------------------------------------------------------------------------
# Branch conditions tests
# ---------------------------------------------------------------------------

class TestBranchConditions:
    """Verify that IF conditions are extracted and associated with branches."""

    def test_branch_1_condition_contains_ws_status(
        self, structure: ProgramStructure
    ) -> None:
        condition = structure.branches["1"].condition_text
        assert "WS-STATUS" in condition

    def test_branch_2_condition_contains_ws_flag(
        self, structure: ProgramStructure
    ) -> None:
        condition = structure.branches["2"].condition_text
        assert "WS-FLAG" in condition

    def test_branch_1_condition_vars(self, structure: ProgramStructure) -> None:
        vars_ = structure.branches["1"].condition_vars
        assert "WS-STATUS" in vars_

    def test_branch_2_condition_vars(self, structure: ProgramStructure) -> None:
        vars_ = structure.branches["2"].condition_vars
        assert "WS-FLAG" in vars_

    def test_condition_vars_exclude_cobol_keywords(
        self, structure: ProgramStructure
    ) -> None:
        """Condition vars should not include COBOL reserved words."""
        for branch in structure.branches.values():
            for var in branch.condition_vars:
                assert var not in {
                    "IF", "ELSE", "THEN", "NOT", "AND", "OR",
                    "EQUAL", "EQUALS", "GREATER", "LESS", "THAN",
                }


# ---------------------------------------------------------------------------
# Call graph tests
# ---------------------------------------------------------------------------

class TestCallGraph:
    """Verify the PERFORM-based call graph."""

    def test_main_performs_three_paragraphs(
        self, structure: ProgramStructure
    ) -> None:
        calls = structure.call_graph["1000-MAIN"]
        assert "2000-VALIDATE" in calls
        assert "3000-PROCESS" in calls
        assert "9000-ERROR" in calls

    def test_main_performs_count(self, structure: ProgramStructure) -> None:
        assert len(structure.call_graph["1000-MAIN"]) == 3

    def test_validate_has_no_performs(self, structure: ProgramStructure) -> None:
        assert structure.call_graph["2000-VALIDATE"] == []

    def test_process_has_no_performs(self, structure: ProgramStructure) -> None:
        assert structure.call_graph["3000-PROCESS"] == []

    def test_error_has_no_performs(self, structure: ProgramStructure) -> None:
        assert structure.call_graph["9000-ERROR"] == []

    def test_all_paragraphs_in_call_graph(
        self, structure: ProgramStructure
    ) -> None:
        """Every paragraph should have an entry in the call graph."""
        for name in structure.paragraphs:
            assert name in structure.call_graph


# ---------------------------------------------------------------------------
# ProgramStructure method tests
# ---------------------------------------------------------------------------

class TestProgramStructureMethods:
    """Verify the helper methods on ProgramStructure."""

    def test_branches_in_main(self, structure: ProgramStructure) -> None:
        branch_ids = structure.branches_in("1000-MAIN")
        assert "1" in branch_ids
        assert len(branch_ids) == 1

    def test_branches_in_validate(self, structure: ProgramStructure) -> None:
        branch_ids = structure.branches_in("2000-VALIDATE")
        assert "2" in branch_ids
        assert len(branch_ids) == 1

    def test_branches_in_process_is_empty(
        self, structure: ProgramStructure
    ) -> None:
        assert structure.branches_in("3000-PROCESS") == []

    def test_branches_in_error_is_empty(
        self, structure: ProgramStructure
    ) -> None:
        assert structure.branches_in("9000-ERROR") == []

    def test_branches_in_unknown_paragraph_raises(
        self, structure: ProgramStructure
    ) -> None:
        with pytest.raises(KeyError, match="Unknown paragraph"):
            structure.branches_in("NONEXISTENT")

    def test_branch_condition_for_branch_1(
        self, structure: ProgramStructure
    ) -> None:
        condition = structure.branch_condition("1")
        assert "WS-STATUS" in condition

    def test_branch_condition_for_branch_2(
        self, structure: ProgramStructure
    ) -> None:
        condition = structure.branch_condition("2")
        assert "WS-FLAG" in condition

    def test_branch_condition_unknown_raises(
        self, structure: ProgramStructure
    ) -> None:
        with pytest.raises(KeyError, match="Unknown branch ID"):
            structure.branch_condition("999")

    def test_get_paragraph_code_returns_source(
        self, structure: ProgramStructure
    ) -> None:
        code = structure.get_paragraph_code("1000-MAIN")
        assert "1000-MAIN" in code
        assert "PERFORM 2000-VALIDATE" in code
        assert "STOP RUN" in code

    def test_get_paragraph_code_validate(
        self, structure: ProgramStructure
    ) -> None:
        code = structure.get_paragraph_code("2000-VALIDATE")
        assert "2000-VALIDATE" in code
        assert "WS-FLAG" in code

    def test_get_paragraph_code_process(
        self, structure: ProgramStructure
    ) -> None:
        code = structure.get_paragraph_code("3000-PROCESS")
        assert "3000-PROCESS" in code
        assert "ADD 1 TO WS-AMOUNT" in code

    def test_get_paragraph_code_error(
        self, structure: ProgramStructure
    ) -> None:
        code = structure.get_paragraph_code("9000-ERROR")
        assert "9000-ERROR" in code
        assert "WRITE-ERROR-LOG" in code

    def test_get_paragraph_code_unknown_raises(
        self, structure: ProgramStructure
    ) -> None:
        with pytest.raises(KeyError, match="Unknown paragraph"):
            structure.get_paragraph_code("NONEXISTENT")


# ---------------------------------------------------------------------------
# Edge case / error handling tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Verify graceful handling of invalid inputs."""

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            parse_mock_structure(tmp_path / "nonexistent.mock.cbl")

    def test_no_procedure_division_raises(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.mock.cbl"
        bad_file.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. BAD.\n"
        )
        with pytest.raises(ValueError, match="PROCEDURE DIVISION"):
            parse_mock_structure(bad_file)

    def test_no_paragraphs_raises(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "empty.mock.cbl"
        bad_file.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. EMPTY.\n"
            "       PROCEDURE DIVISION.\n"
            "           STOP RUN.\n"
        )
        with pytest.raises(ValueError, match="No paragraphs"):
            parse_mock_structure(bad_file)


# ---------------------------------------------------------------------------
# Performs / paragraph cross-reference tests
# ---------------------------------------------------------------------------

class TestParagraphPerforms:
    """Verify that PERFORM targets are recorded on ParagraphInfo."""

    def test_main_paragraph_performs(self, structure: ProgramStructure) -> None:
        para = structure.paragraphs["1000-MAIN"]
        assert "2000-VALIDATE" in para.performs
        assert "3000-PROCESS" in para.performs
        assert "9000-ERROR" in para.performs

    def test_validate_paragraph_performs_empty(
        self, structure: ProgramStructure
    ) -> None:
        assert structure.paragraphs["2000-VALIDATE"].performs == []

    def test_main_paragraph_branches(self, structure: ProgramStructure) -> None:
        para = structure.paragraphs["1000-MAIN"]
        assert "1" in para.branches

    def test_validate_paragraph_branches(
        self, structure: ProgramStructure
    ) -> None:
        para = structure.paragraphs["2000-VALIDATE"]
        assert "2" in para.branches
