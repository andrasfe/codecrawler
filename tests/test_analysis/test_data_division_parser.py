"""Tests for cobol_penetrator.analysis.data_division_parser.

Validates parsing of WORKING-STORAGE SECTION from .mock.cbl files:
field extraction, specter filtering, 88-level attachment, REDEFINES
handling, and parent tracking.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cobol_penetrator.analysis.data_division_parser import (
    FieldDefinition,
    parse_working_storage,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_MOCK_CBL = FIXTURES_DIR / "sample.mock.cbl"


@pytest.fixture
def fields() -> list[FieldDefinition]:
    """Parse the sample fixture once for use across tests."""
    return parse_working_storage(SAMPLE_MOCK_CBL)


@pytest.fixture
def field_map(fields: list[FieldDefinition]) -> dict[str, FieldDefinition]:
    """Build a name -> FieldDefinition lookup for convenience."""
    return {f.name: f for f in fields}


# ---------------------------------------------------------------------------
# Basic field discovery
# ---------------------------------------------------------------------------

class TestFieldDiscovery:
    """Verify that application fields are correctly discovered."""

    def test_finds_application_fields(
        self, fields: list[FieldDefinition]
    ) -> None:
        names = {f.name for f in fields}
        assert "WS-STATUS" in names
        assert "WS-FLAG" in names
        assert "WS-AMOUNT" in names
        assert "WS-ACCOUNT-ID" in names

    def test_finds_group_items(
        self, fields: list[FieldDefinition]
    ) -> None:
        names = {f.name for f in fields}
        assert "WS-VARIABLES" in names

    def test_finds_child_fields(
        self, fields: list[FieldDefinition]
    ) -> None:
        names = {f.name for f in fields}
        assert "WS-SUB-AMOUNT" in names
        assert "WS-CODE" in names

    def test_finds_date_and_time_fields(
        self, fields: list[FieldDefinition]
    ) -> None:
        names = {f.name for f in fields}
        assert "WS-TRANSACTION-DT" in names
        assert "WS-PROCESS-TIME" in names

    def test_finds_counter_field(
        self, fields: list[FieldDefinition]
    ) -> None:
        names = {f.name for f in fields}
        assert "WS-RECORD-CNT" in names


# ---------------------------------------------------------------------------
# Specter infrastructure filtering
# ---------------------------------------------------------------------------

class TestSpecterFiltering:
    """Verify that specter mock infrastructure fields are excluded."""

    def test_mock_record_filtered(
        self, fields: list[FieldDefinition]
    ) -> None:
        names = {f.name for f in fields}
        assert "MOCK-RECORD" not in names
        assert "MOCK-OP-KEY" not in names
        assert "MOCK-ALPHA-STATUS" not in names
        assert "MOCK-NUM-STATUS" not in names
        assert "MOCK-FILLER" not in names

    def test_mock_file_status_filtered(
        self, fields: list[FieldDefinition]
    ) -> None:
        names = {f.name for f in fields}
        assert "MOCK-FILE-STATUS" not in names

    def test_mock_file_record_filtered(
        self, fields: list[FieldDefinition]
    ) -> None:
        names = {f.name for f in fields}
        assert "MOCK-FILE-RECORD" not in names


# ---------------------------------------------------------------------------
# PIC clause parsing
# ---------------------------------------------------------------------------

class TestPicParsing:
    """Verify PIC clauses are correctly parsed for each field."""

    def test_ws_status_is_alpha(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-STATUS"]
        assert f.pic_type == "alpha"
        assert f.length == 2
        assert f.signed is False

    def test_ws_flag_is_alpha(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-FLAG"]
        assert f.pic_type == "alpha"
        assert f.length == 1

    def test_ws_amount_is_packed(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-AMOUNT"]
        assert f.pic_type == "packed"
        assert f.length == 7
        assert f.precision == 2
        assert f.signed is True

    def test_ws_account_id_is_numeric(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-ACCOUNT-ID"]
        assert f.pic_type == "numeric"
        assert f.length == 11

    def test_ws_customer_name_is_alpha(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-CUSTOMER-NAME"]
        assert f.pic_type == "alpha"
        assert f.length == 30

    def test_sqlcode_is_comp(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["SQLCODE"]
        assert f.pic_type == "comp"
        assert f.length == 9
        assert f.signed is True

    def test_ws_sub_amount_is_numeric(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-SUB-AMOUNT"]
        assert f.pic_type == "numeric"
        assert f.length == 5
        assert f.precision == 2
        assert f.signed is True

    def test_group_item_has_no_pic(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-VARIABLES"]
        assert f.pic_type == "group"
        assert f.pic_clause is None
        assert f.length == 0


# ---------------------------------------------------------------------------
# VALUE clause extraction
# ---------------------------------------------------------------------------

class TestValueClauses:
    """Verify that VALUE clauses are correctly extracted."""

    def test_ws_flag_default_value(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-FLAG"]
        assert f.value_clause is not None
        assert "N" in f.value_clause

    def test_ws_customer_name_spaces(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-CUSTOMER-NAME"]
        assert f.value_clause is not None
        assert "SPACES" in f.value_clause.upper()

    def test_ws_record_cnt_zero(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-RECORD-CNT"]
        assert f.value_clause is not None
        assert "ZERO" in f.value_clause.upper()

    def test_field_without_value(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-STATUS"]
        assert f.value_clause is None


# ---------------------------------------------------------------------------
# 88-level condition attachment
# ---------------------------------------------------------------------------

class TestLevel88Attachment:
    """Verify that 88-level conditions are attached to parent fields."""

    def test_ws_status_has_88_values(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-STATUS"]
        assert len(f.values_88) == 3
        assert "STATUS-OK" in f.values_88
        assert "STATUS-ERROR" in f.values_88
        assert "STATUS-WARNING" in f.values_88

    def test_ws_status_88_values_content(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-STATUS"]
        assert "'00'" in f.values_88["STATUS-OK"]
        assert "'99'" in f.values_88["STATUS-ERROR"]
        assert "'04'" in f.values_88["STATUS-WARNING"]

    def test_ws_flag_has_88_values(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-FLAG"]
        assert len(f.values_88) == 2
        assert "FLAG-YES" in f.values_88
        assert "FLAG-NO" in f.values_88

    def test_88_levels_not_in_field_list(
        self, fields: list[FieldDefinition]
    ) -> None:
        """88-level items should not appear as standalone fields."""
        for f in fields:
            assert f.level != 88


# ---------------------------------------------------------------------------
# Parent tracking
# ---------------------------------------------------------------------------

class TestParentTracking:
    """Verify parent-child relationships in field hierarchy."""

    def test_01_level_has_no_parent(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-STATUS"]
        assert f.parent_name is None

    def test_05_level_has_01_parent(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-SUB-AMOUNT"]
        assert f.parent_name == "WS-VARIABLES"

    def test_code_has_variables_parent(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        f = field_map["WS-CODE"]
        assert f.parent_name == "WS-VARIABLES"


# ---------------------------------------------------------------------------
# FILLER handling
# ---------------------------------------------------------------------------

class TestFillerHandling:
    """Verify FILLER fields are correctly identified."""

    def test_filler_is_marked(
        self, fields: list[FieldDefinition]
    ) -> None:
        fillers = [f for f in fields if f.is_filler]
        assert len(fillers) >= 1
        for f in fillers:
            assert f.name == "FILLER"


# ---------------------------------------------------------------------------
# REDEFINES handling
# ---------------------------------------------------------------------------

class TestRedefinesHandling:
    """Verify that REDEFINES groups are handled."""

    def test_redefines_alpha_present(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        """The original field before REDEFINES should be present."""
        assert "WS-REDEF-ALPHA" in field_map

    def test_redefines_num_skipped(
        self, field_map: dict[str, FieldDefinition]
    ) -> None:
        """The REDEFINES target field should be skipped."""
        assert "WS-REDEF-NUM" not in field_map


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestParserErrors:
    """Verify error handling for invalid inputs."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            parse_working_storage(tmp_path / "nonexistent.mock.cbl")

    def test_no_working_storage(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.mock.cbl"
        bad_file.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. BAD.\n"
            "       PROCEDURE DIVISION.\n"
            "       1000-MAIN.\n"
            "           STOP RUN.\n"
        )
        with pytest.raises(ValueError, match="WORKING-STORAGE"):
            parse_working_storage(bad_file)

    def test_no_procedure_division(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad2.mock.cbl"
        bad_file.write_text(
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. BAD.\n"
            "       DATA DIVISION.\n"
            "       WORKING-STORAGE SECTION.\n"
            "       01 WS-X PIC X.\n"
        )
        with pytest.raises(ValueError, match="PROCEDURE DIVISION"):
            parse_working_storage(bad_file)
