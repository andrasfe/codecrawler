"""Tests for cobol_penetrator.heuristics.stub_fault_table."""

from __future__ import annotations

from cobol_penetrator.heuristics.stub_fault_table import (
    CICS_STATUS_CODES,
    DLI_STATUS_CODES,
    EIBAID_VALUES,
    FILE_STATUS_CODES,
    RETURN_CODES,
    SQL_STATUS_CODES,
    fault_values_for,
    success_value_for,
)


class TestFaultTables:
    """Verify the static fault code tables contain expected values."""

    def test_file_status_codes_non_empty(self) -> None:
        assert len(FILE_STATUS_CODES) > 0

    def test_file_status_contains_success(self) -> None:
        assert "00" in FILE_STATUS_CODES

    def test_file_status_contains_eof(self) -> None:
        assert "10" in FILE_STATUS_CODES

    def test_sql_status_codes_non_empty(self) -> None:
        assert len(SQL_STATUS_CODES) > 0

    def test_sql_status_contains_success(self) -> None:
        assert 0 in SQL_STATUS_CODES

    def test_sql_status_contains_not_found(self) -> None:
        assert 100 in SQL_STATUS_CODES

    def test_sql_status_contains_negative_codes(self) -> None:
        negatives = [c for c in SQL_STATUS_CODES if c < 0]
        assert len(negatives) >= 1

    def test_cics_status_codes_non_empty(self) -> None:
        assert len(CICS_STATUS_CODES) > 0

    def test_cics_status_contains_normal(self) -> None:
        assert 0 in CICS_STATUS_CODES

    def test_dli_status_codes_non_empty(self) -> None:
        assert len(DLI_STATUS_CODES) > 0

    def test_dli_status_contains_success(self) -> None:
        assert "  " in DLI_STATUS_CODES

    def test_dli_status_contains_not_found(self) -> None:
        assert "GE" in DLI_STATUS_CODES

    def test_return_codes_non_empty(self) -> None:
        assert len(RETURN_CODES) > 0

    def test_return_codes_contains_zero(self) -> None:
        assert 0 in RETURN_CODES

    def test_return_codes_ascending(self) -> None:
        assert RETURN_CODES == sorted(RETURN_CODES)

    def test_eibaid_values_non_empty(self) -> None:
        assert len(EIBAID_VALUES) > 0

    def test_eibaid_contains_enter(self) -> None:
        assert "DFHENTER" in EIBAID_VALUES


class TestFaultValuesFor:
    """Test the fault_values_for lookup function."""

    def test_status_file_returns_file_codes(self) -> None:
        result = fault_values_for("status_file")
        assert result == FILE_STATUS_CODES

    def test_status_sql_returns_sql_codes(self) -> None:
        result = fault_values_for("status_sql")
        assert result == SQL_STATUS_CODES

    def test_status_cics_returns_cics_codes(self) -> None:
        result = fault_values_for("status_cics")
        assert result == CICS_STATUS_CODES

    def test_status_dli_returns_dli_codes(self) -> None:
        result = fault_values_for("status_dli")
        assert result == DLI_STATUS_CODES

    def test_return_code_returns_return_codes(self) -> None:
        result = fault_values_for("return_code")
        assert result == RETURN_CODES

    def test_eibaid_returns_eibaid_values(self) -> None:
        result = fault_values_for("eibaid")
        assert result == EIBAID_VALUES

    def test_unknown_type_returns_empty(self) -> None:
        result = fault_values_for("nonexistent_type")
        assert result == []

    def test_returns_copy_not_reference(self) -> None:
        """Modifying the returned list must not affect the source table."""
        result = fault_values_for("status_file")
        result.append("XX")
        assert "XX" not in fault_values_for("status_file")


class TestSuccessValueFor:
    """Test the success_value_for lookup function."""

    def test_file_success(self) -> None:
        assert success_value_for("status_file") == "00"

    def test_sql_success(self) -> None:
        assert success_value_for("status_sql") == 0

    def test_cics_success(self) -> None:
        assert success_value_for("status_cics") == 0

    def test_dli_success(self) -> None:
        assert success_value_for("status_dli") == "  "

    def test_return_code_success(self) -> None:
        assert success_value_for("return_code") == 0

    def test_eibaid_success(self) -> None:
        assert success_value_for("eibaid") == "DFHENTER"

    def test_unknown_type_returns_empty_string(self) -> None:
        assert success_value_for("nonexistent_type") == ""
