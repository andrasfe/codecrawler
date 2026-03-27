"""Tests for cobol_penetrator.analysis.condition_harvester.

Validates literal extraction from IF statements, EVALUATE/WHEN blocks,
multi-value OR conditions, and numeric comparisons.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cobol_penetrator.analysis.condition_harvester import harvest_conditions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_MOCK_CBL = FIXTURES_DIR / "sample.mock.cbl"


@pytest.fixture
def conditions() -> dict[str, list]:
    """Harvest conditions from the sample fixture."""
    return harvest_conditions(SAMPLE_MOCK_CBL)


# ---------------------------------------------------------------------------
# IF statement harvesting
# ---------------------------------------------------------------------------

class TestIfConditions:
    """Verify literal extraction from IF statements."""

    def test_ws_status_equals_00(
        self, conditions: dict[str, list]
    ) -> None:
        assert "WS-STATUS" in conditions
        assert "00" in conditions["WS-STATUS"]

    def test_ws_flag_equals_y(
        self, conditions: dict[str, list]
    ) -> None:
        assert "WS-FLAG" in conditions
        assert "Y" in conditions["WS-FLAG"]

    def test_ws_amount_greater_than(
        self, conditions: dict[str, list]
    ) -> None:
        """Numeric comparison should extract the literal and boundaries."""
        assert "WS-AMOUNT" in conditions
        assert 1000 in conditions["WS-AMOUNT"]


# ---------------------------------------------------------------------------
# EVALUATE/WHEN harvesting
# ---------------------------------------------------------------------------

class TestEvaluateConditions:
    """Verify literal extraction from EVALUATE/WHEN blocks."""

    def test_evaluate_ws_status_values(
        self, conditions: dict[str, list]
    ) -> None:
        """EVALUATE WS-STATUS should capture WHEN literals."""
        assert "WS-STATUS" in conditions
        ws_status_vals = conditions["WS-STATUS"]
        assert "00" in ws_status_vals
        assert "04" in ws_status_vals
        assert "99" in ws_status_vals


# ---------------------------------------------------------------------------
# Multi-value conditions
# ---------------------------------------------------------------------------

class TestMultiValueConditions:
    """Verify extraction of OR-separated multi-value lists."""

    def test_or_separated_values(self, tmp_path: Path) -> None:
        """IF WS-CODE = '01' OR '02' OR '03' should capture all."""
        cobol = (
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       DATA DIVISION.\n"
            "       WORKING-STORAGE SECTION.\n"
            "       01 WS-CODE PIC X(02).\n"
            "       PROCEDURE DIVISION.\n"
            "       1000-MAIN.\n"
            "           IF WS-CODE = '01' OR '02' OR '03'\n"
            "               CONTINUE\n"
            "           END-IF.\n"
        )
        f = tmp_path / "multi.mock.cbl"
        f.write_text(cobol)
        result = harvest_conditions(f)
        assert "WS-CODE" in result
        assert "01" in result["WS-CODE"]
        assert "02" in result["WS-CODE"]
        assert "03" in result["WS-CODE"]


# ---------------------------------------------------------------------------
# Numeric comparison boundaries
# ---------------------------------------------------------------------------

class TestNumericBoundaries:
    """Verify boundary value generation for ordering comparisons."""

    def test_greater_than_adds_boundaries(self, tmp_path: Path) -> None:
        """IF WS-COUNTER > 10 should include 9, 10, and 11."""
        cobol = (
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       DATA DIVISION.\n"
            "       WORKING-STORAGE SECTION.\n"
            "       01 WS-COUNTER PIC 9(5).\n"
            "       PROCEDURE DIVISION.\n"
            "       1000-MAIN.\n"
            "           IF WS-COUNTER > 10\n"
            "               CONTINUE\n"
            "           END-IF.\n"
        )
        f = tmp_path / "boundary.mock.cbl"
        f.write_text(cobol)
        result = harvest_conditions(f)
        assert "WS-COUNTER" in result
        assert 10 in result["WS-COUNTER"]
        assert 9 in result["WS-COUNTER"]
        assert 11 in result["WS-COUNTER"]

    def test_less_than_adds_boundaries(self, tmp_path: Path) -> None:
        """IF WS-LIMIT < 500 should include 499, 500, and 501."""
        cobol = (
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       DATA DIVISION.\n"
            "       WORKING-STORAGE SECTION.\n"
            "       01 WS-LIMIT PIC 9(5).\n"
            "       PROCEDURE DIVISION.\n"
            "       1000-MAIN.\n"
            "           IF WS-LIMIT < 500\n"
            "               CONTINUE\n"
            "           END-IF.\n"
        )
        f = tmp_path / "boundary2.mock.cbl"
        f.write_text(cobol)
        result = harvest_conditions(f)
        assert "WS-LIMIT" in result
        assert 500 in result["WS-LIMIT"]
        assert 499 in result["WS-LIMIT"]
        assert 501 in result["WS-LIMIT"]


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    """Verify that duplicate literals are not repeated."""

    def test_no_duplicate_values(
        self, conditions: dict[str, list]
    ) -> None:
        """All literal lists should have unique values."""
        for var_name, literals in conditions.items():
            assert len(literals) == len(set(literals)), (
                f"Duplicate literals for {var_name}: {literals}"
            )


# ---------------------------------------------------------------------------
# EVALUATE TRUE with conditions
# ---------------------------------------------------------------------------

class TestEvaluateTrue:
    """Verify EVALUATE TRUE / WHEN <condition> harvesting."""

    def test_evaluate_true_extracts_conditions(
        self, tmp_path: Path
    ) -> None:
        cobol = (
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       DATA DIVISION.\n"
            "       WORKING-STORAGE SECTION.\n"
            "       01 WS-STATUS PIC X(02).\n"
            "       PROCEDURE DIVISION.\n"
            "       1000-MAIN.\n"
            "           EVALUATE TRUE\n"
            "               WHEN WS-STATUS = '00'\n"
            "                   CONTINUE\n"
            "               WHEN WS-STATUS = '08'\n"
            "                   CONTINUE\n"
            "               WHEN OTHER\n"
            "                   CONTINUE\n"
            "           END-EVALUATE.\n"
        )
        f = tmp_path / "evaltrue.mock.cbl"
        f.write_text(cobol)
        result = harvest_conditions(f)
        assert "WS-STATUS" in result
        assert "00" in result["WS-STATUS"]
        assert "08" in result["WS-STATUS"]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestHarvesterErrors:
    """Verify error handling for invalid inputs."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            harvest_conditions(tmp_path / "nonexistent.mock.cbl")

    def test_no_procedure_division(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.mock.cbl"
        bad_file.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. BAD.\n"
        )
        with pytest.raises(ValueError, match="PROCEDURE DIVISION"):
            harvest_conditions(bad_file)

    def test_empty_procedure_division(self, tmp_path: Path) -> None:
        """A PROCEDURE DIVISION with no conditions should return empty."""
        cobol = (
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. TEST.\n"
            "       DATA DIVISION.\n"
            "       WORKING-STORAGE SECTION.\n"
            "       01 WS-X PIC X.\n"
            "       PROCEDURE DIVISION.\n"
            "       1000-MAIN.\n"
            "           DISPLAY 'HELLO'.\n"
        )
        f = tmp_path / "empty.mock.cbl"
        f.write_text(cobol)
        result = harvest_conditions(f)
        assert result == {}
