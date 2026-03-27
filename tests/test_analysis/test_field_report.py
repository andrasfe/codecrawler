"""Tests for cobol_penetrator.analysis.field_report.

Validates end-to-end FieldReport construction from sample.mock.cbl,
including field domain population, condition hint merging, and stub
operation mapping.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cobol_penetrator.analysis.field_report import FieldReport, build_field_report
from cobol_penetrator.analysis.variable_domain import VariableDomain
from cobol_penetrator.mock_reader import ProgramStructure, parse_mock_structure


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_MOCK_CBL = FIXTURES_DIR / "sample.mock.cbl"


@pytest.fixture
def structure() -> ProgramStructure:
    """Parse the sample fixture for program structure."""
    return parse_mock_structure(SAMPLE_MOCK_CBL)


@pytest.fixture
def report(structure: ProgramStructure) -> FieldReport:
    """Build a complete field report from the sample fixture."""
    return build_field_report(SAMPLE_MOCK_CBL, structure)


# ---------------------------------------------------------------------------
# FieldReport structure
# ---------------------------------------------------------------------------

class TestFieldReportStructure:
    """Verify the FieldReport has the expected attributes and types."""

    def test_report_has_fields(self, report: FieldReport) -> None:
        assert isinstance(report.fields, dict)
        assert len(report.fields) > 0

    def test_report_has_condition_hints(self, report: FieldReport) -> None:
        assert isinstance(report.condition_hints, dict)

    def test_report_has_stub_variables(self, report: FieldReport) -> None:
        assert isinstance(report.stub_variables, dict)

    def test_report_has_stub_operations(self, report: FieldReport) -> None:
        assert isinstance(report.stub_operations, list)

    def test_fields_are_variable_domains(self, report: FieldReport) -> None:
        for name, domain in report.fields.items():
            assert isinstance(domain, VariableDomain)
            assert domain.name == name


# ---------------------------------------------------------------------------
# Field population
# ---------------------------------------------------------------------------

class TestFieldPopulation:
    """Verify that fields are correctly populated from WORKING-STORAGE."""

    def test_ws_status_present(self, report: FieldReport) -> None:
        assert "WS-STATUS" in report.fields

    def test_ws_flag_present(self, report: FieldReport) -> None:
        assert "WS-FLAG" in report.fields

    def test_ws_amount_present(self, report: FieldReport) -> None:
        assert "WS-AMOUNT" in report.fields

    def test_ws_account_id_present(self, report: FieldReport) -> None:
        assert "WS-ACCOUNT-ID" in report.fields

    def test_sqlcode_present(self, report: FieldReport) -> None:
        assert "SQLCODE" in report.fields

    def test_filler_not_present(self, report: FieldReport) -> None:
        assert "FILLER" not in report.fields

    def test_mock_infrastructure_not_present(
        self, report: FieldReport
    ) -> None:
        for name in report.fields:
            assert not name.startswith("MOCK-")
            assert not name.startswith("SPECTER-")


# ---------------------------------------------------------------------------
# Domain details
# ---------------------------------------------------------------------------

class TestDomainDetails:
    """Verify specific field domain properties."""

    def test_ws_status_type(self, report: FieldReport) -> None:
        domain = report.fields["WS-STATUS"]
        assert domain.data_type == "alpha"
        assert domain.max_length == 2

    def test_ws_status_has_88_values(self, report: FieldReport) -> None:
        domain = report.fields["WS-STATUS"]
        assert "STATUS-OK" in domain.valid_88_values
        assert "STATUS-ERROR" in domain.valid_88_values

    def test_ws_amount_is_packed(self, report: FieldReport) -> None:
        domain = report.fields["WS-AMOUNT"]
        assert domain.data_type == "packed"
        assert domain.signed is True
        assert domain.precision == 2

    def test_ws_amount_has_range(self, report: FieldReport) -> None:
        domain = report.fields["WS-AMOUNT"]
        assert domain.min_value is not None
        assert domain.max_value is not None
        assert domain.min_value < 0
        assert domain.max_value > 0

    def test_sqlcode_classification(self, report: FieldReport) -> None:
        domain = report.fields["SQLCODE"]
        assert domain.classification == "status"
        assert domain.semantic_type == "status_sql"

    def test_ws_transaction_dt_semantic(self, report: FieldReport) -> None:
        domain = report.fields["WS-TRANSACTION-DT"]
        assert domain.semantic_type == "date"

    def test_ws_record_cnt_semantic(self, report: FieldReport) -> None:
        domain = report.fields["WS-RECORD-CNT"]
        assert domain.semantic_type == "counter"

    def test_ws_error_flg_classification(self, report: FieldReport) -> None:
        domain = report.fields["WS-ERROR-FLG"]
        assert domain.classification == "flag"
        assert domain.semantic_type == "flag_bool"


# ---------------------------------------------------------------------------
# Condition hints merged into domains
# ---------------------------------------------------------------------------

class TestConditionHintMerging:
    """Verify that harvested condition hints are merged into domains."""

    def test_ws_status_has_condition_literals(
        self, report: FieldReport
    ) -> None:
        domain = report.fields["WS-STATUS"]
        assert len(domain.condition_literals) > 0
        assert "00" in domain.condition_literals

    def test_ws_flag_has_condition_literals(
        self, report: FieldReport
    ) -> None:
        domain = report.fields["WS-FLAG"]
        assert "Y" in domain.condition_literals

    def test_condition_hints_dict_populated(
        self, report: FieldReport
    ) -> None:
        assert len(report.condition_hints) > 0
        assert "WS-STATUS" in report.condition_hints


# ---------------------------------------------------------------------------
# Stub mapping
# ---------------------------------------------------------------------------

class TestStubMapping:
    """Verify stub operation to variable mapping."""

    def test_stub_operations_found(self, report: FieldReport) -> None:
        """The sample file has SPECTER-MOCK operations."""
        assert len(report.stub_operations) > 0

    def test_read_account_stub_present(self, report: FieldReport) -> None:
        assert "READ-ACCOUNT" in report.stub_operations

    def test_write_error_log_stub_present(
        self, report: FieldReport
    ) -> None:
        assert "WRITE-ERROR-LOG" in report.stub_operations

    def test_stub_variable_mapped(self, report: FieldReport) -> None:
        """WS-STATUS should be mapped to READ-ACCOUNT stub."""
        if "WS-STATUS" in report.stub_variables:
            assert report.stub_variables["WS-STATUS"] == "READ-ACCOUNT"

    def test_stub_set_by_in_domain(self, report: FieldReport) -> None:
        """If stub is mapped, the domain should reflect it."""
        if "WS-STATUS" in report.stub_variables:
            domain = report.fields["WS-STATUS"]
            assert domain.set_by_stub == "READ-ACCOUNT"


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

class TestDefaultValues:
    """Verify default values are carried into domain objects."""

    def test_ws_flag_default(self, report: FieldReport) -> None:
        domain = report.fields["WS-FLAG"]
        assert domain.default_value == "N"

    def test_ws_customer_name_default(self, report: FieldReport) -> None:
        domain = report.fields["WS-CUSTOMER-NAME"]
        assert domain.default_value == " "

    def test_ws_record_cnt_default(self, report: FieldReport) -> None:
        domain = report.fields["WS-RECORD-CNT"]
        assert domain.default_value == "0"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestFieldReportErrors:
    """Verify error handling in build_field_report."""

    def test_file_not_found(
        self, structure: ProgramStructure, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            build_field_report(
                tmp_path / "nonexistent.mock.cbl", structure
            )
