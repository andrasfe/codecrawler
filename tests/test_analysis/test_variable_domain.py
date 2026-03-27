"""Tests for cobol_penetrator.analysis.variable_domain.

Validates semantic type inference, numeric range computation,
variable classification, and domain construction from field definitions.
"""

from __future__ import annotations

import pytest

from cobol_penetrator.analysis.data_division_parser import FieldDefinition
from cobol_penetrator.analysis.variable_domain import (
    VariableDomain,
    _classify_variable,
    _compute_range,
    _infer_semantic_type,
    build_domain,
)


# ---------------------------------------------------------------------------
# Helper to create minimal FieldDefinition objects for testing
# ---------------------------------------------------------------------------

def _make_field(
    name: str,
    pic_type: str = "alpha",
    length: int = 10,
    precision: int = 0,
    signed: bool = False,
    usage: str = "",
    value_clause: str | None = None,
    values_88: dict[str, str] | None = None,
) -> FieldDefinition:
    """Create a FieldDefinition with sensible defaults for testing."""
    return FieldDefinition(
        level=1,
        name=name,
        pic_clause=f"X({length})" if pic_type == "alpha" else f"9({length})",
        pic_type=pic_type,
        length=length,
        precision=precision,
        signed=signed,
        usage=usage,
        value_clause=value_clause,
        parent_name=None,
        is_filler=False,
        values_88=values_88 or {},
    )


# ---------------------------------------------------------------------------
# Semantic type inference
# ---------------------------------------------------------------------------

class TestSemanticTypeInference:
    """Verify _infer_semantic_type correctly identifies field purposes."""

    def test_date_from_dt_suffix(self) -> None:
        assert _infer_semantic_type("WS-TRANSACTION-DT", "internal") == "date"

    def test_date_from_date_keyword(self) -> None:
        assert _infer_semantic_type("WS-CUR-DATE-X6", "internal") == "date"

    def test_date_from_yymmdd(self) -> None:
        assert _infer_semantic_type("WS-YYMMDD", "internal") == "date"

    def test_date_from_yyddd(self) -> None:
        assert _infer_semantic_type("WS-YYDDD", "internal") == "date"

    def test_time_from_time_keyword(self) -> None:
        assert _infer_semantic_type("WS-PROCESS-TIME", "internal") == "time"

    def test_time_from_tm_suffix(self) -> None:
        assert _infer_semantic_type("WS-START-TM", "internal") == "time"

    def test_amount_from_amt(self) -> None:
        assert _infer_semantic_type("WS-AVAILABLE-AMT", "internal") == "amount"

    def test_amount_from_balance(self) -> None:
        assert _infer_semantic_type("WS-BALANCE", "internal") == "amount"

    def test_counter_from_cnt(self) -> None:
        assert _infer_semantic_type("WS-RECORD-CNT", "internal") == "counter"

    def test_counter_from_count(self) -> None:
        assert _infer_semantic_type("WS-ERROR-COUNT", "internal") == "counter"

    def test_identifier_from_id(self) -> None:
        assert _infer_semantic_type("WS-CUSTOMER-ID", "internal") == "identifier"

    def test_identifier_from_acct(self) -> None:
        assert _infer_semantic_type("WS-ACCT-NUM", "internal") == "identifier"

    def test_status_sql_from_sqlcode(self) -> None:
        assert _infer_semantic_type("SQLCODE", "status") == "status_sql"

    def test_status_sql_from_sqlstate(self) -> None:
        assert _infer_semantic_type("SQLSTATE", "status") == "status_sql"

    def test_status_cics_from_eibresp(self) -> None:
        assert _infer_semantic_type("EIBRESP", "status") == "status_cics"

    def test_status_file_from_suffix(self) -> None:
        assert _infer_semantic_type("WS-FILE-STATUS", "internal") == "status_file"

    def test_status_file_from_fs_prefix(self) -> None:
        assert _infer_semantic_type("FS-ACCOUNT", "internal") == "status_file"

    def test_flag_bool_from_flag(self) -> None:
        assert _infer_semantic_type("WS-ERROR-FLAG", "internal") == "flag_bool"

    def test_flag_bool_from_flg(self) -> None:
        assert _infer_semantic_type("WS-ERROR-FLG", "internal") == "flag_bool"

    def test_flag_bool_from_on_suffix(self) -> None:
        assert _infer_semantic_type("WS-DEBUG-ON", "internal") == "flag_bool"

    def test_generic_fallback(self) -> None:
        assert _infer_semantic_type("WS-SOME-FIELD", "internal") == "generic"

    def test_classification_status_fallback(self) -> None:
        assert _infer_semantic_type("WS-RESP-CD", "status") == "status_file"

    def test_classification_flag_fallback(self) -> None:
        assert _infer_semantic_type("WS-SOME-SWITCH", "flag") == "flag_bool"


# ---------------------------------------------------------------------------
# Range computation
# ---------------------------------------------------------------------------

class TestRangeComputation:
    """Verify _compute_range for various data types."""

    def test_alpha_returns_none(self) -> None:
        min_val, max_val = _compute_range("alpha", 10, 0, False)
        assert min_val is None
        assert max_val is None

    def test_group_returns_none(self) -> None:
        min_val, max_val = _compute_range("group", 0, 0, False)
        assert min_val is None
        assert max_val is None

    def test_unknown_returns_none(self) -> None:
        min_val, max_val = _compute_range("unknown", 10, 0, False)
        assert min_val is None
        assert max_val is None

    def test_numeric_unsigned_5_digits(self) -> None:
        min_val, max_val = _compute_range("numeric", 5, 0, False)
        assert min_val == 0
        assert max_val == 99999

    def test_numeric_unsigned_9_digits(self) -> None:
        min_val, max_val = _compute_range("numeric", 9, 0, False)
        assert min_val == 0
        assert max_val == 999999999

    def test_numeric_signed_9_digits(self) -> None:
        min_val, max_val = _compute_range("numeric", 9, 0, True)
        assert min_val == -999999999
        assert max_val == 999999999

    def test_numeric_with_precision(self) -> None:
        min_val, max_val = _compute_range("numeric", 7, 2, False)
        assert min_val == 0.0
        assert max_val == pytest.approx(9999999.99)

    def test_numeric_signed_with_precision(self) -> None:
        min_val, max_val = _compute_range("numeric", 7, 2, True)
        assert min_val == pytest.approx(-9999999.99)
        assert max_val == pytest.approx(9999999.99)

    def test_packed_5_digits(self) -> None:
        min_val, max_val = _compute_range("packed", 5, 0, False)
        assert min_val == 0
        assert max_val == 99999

    def test_comp_9_digits(self) -> None:
        min_val, max_val = _compute_range("comp", 9, 0, True)
        assert min_val == -999999999
        assert max_val == 999999999


# ---------------------------------------------------------------------------
# Variable classification
# ---------------------------------------------------------------------------

class TestClassification:
    """Verify _classify_variable for various naming patterns."""

    def test_sqlcode_is_status(self) -> None:
        assert _classify_variable("SQLCODE", False) == "status"

    def test_eibresp_is_status(self) -> None:
        assert _classify_variable("EIBRESP", False) == "status"

    def test_ws_file_status_is_status(self) -> None:
        assert _classify_variable("WS-FILE-STATUS", False) == "status"

    def test_fs_prefix_is_status(self) -> None:
        assert _classify_variable("FS-ACCOUNT", False) == "status"

    def test_pcb_status_is_status(self) -> None:
        assert _classify_variable("WS-PCB-STATUS", False) == "status"

    def test_status_code_prefix_is_status(self) -> None:
        assert _classify_variable("STATUS-CODE-PCB1", False) == "status"

    def test_flag_suffix(self) -> None:
        assert _classify_variable("WS-ERROR-FLAG", False) == "flag"

    def test_flg_in_name(self) -> None:
        assert _classify_variable("WS-MSG-FLG", False) == "flag"

    def test_on_suffix(self) -> None:
        assert _classify_variable("WS-DEBUG-ON", False) == "flag"

    def test_off_suffix(self) -> None:
        assert _classify_variable("WS-DEBUG-OFF", False) == "flag"

    def test_error_suffix(self) -> None:
        assert _classify_variable("WS-PARSE-ERROR", False) == "flag"

    def test_success_suffix(self) -> None:
        assert _classify_variable("WS-CALL-SUCCESS", False) == "flag"

    def test_end_prefix(self) -> None:
        assert _classify_variable("END-OF-FILE", False) == "flag"

    def test_no_more_prefix(self) -> None:
        assert _classify_variable("NO-MORE-RECORDS", False) == "flag"

    def test_88_values_makes_flag(self) -> None:
        assert _classify_variable("WS-SOME-FIELD", True) == "flag"

    def test_plain_field_is_internal(self) -> None:
        assert _classify_variable("WS-CUSTOMER-NAME", False) == "internal"


# ---------------------------------------------------------------------------
# Build domain from FieldDefinition
# ---------------------------------------------------------------------------

class TestBuildDomain:
    """Verify end-to-end domain construction from FieldDefinition."""

    def test_alpha_field(self) -> None:
        fld = _make_field("WS-CUSTOMER-NAME", "alpha", 30)
        domain = build_domain(fld)
        assert domain.name == "WS-CUSTOMER-NAME"
        assert domain.data_type == "alpha"
        assert domain.max_length == 30
        assert domain.min_value is None
        assert domain.max_value is None
        assert domain.classification == "internal"

    def test_numeric_field_with_range(self) -> None:
        fld = _make_field("WS-ACCOUNT-ID", "numeric", 11)
        domain = build_domain(fld)
        assert domain.data_type == "numeric"
        assert domain.min_value == 0
        assert domain.max_value == 99999999999

    def test_signed_packed_field(self) -> None:
        fld = _make_field(
            "WS-AMOUNT",
            "packed",
            7,
            precision=2,
            signed=True,
            usage="COMP-3",
        )
        domain = build_domain(fld)
        assert domain.data_type == "packed"
        assert domain.signed is True
        assert domain.precision == 2
        assert domain.min_value == pytest.approx(-9999999.99)
        assert domain.max_value == pytest.approx(9999999.99)

    def test_status_field_classification(self) -> None:
        fld = _make_field("SQLCODE", "comp", 9, signed=True)
        domain = build_domain(fld)
        assert domain.classification == "status"
        assert domain.semantic_type == "status_sql"

    def test_flag_field_with_88_values(self) -> None:
        fld = _make_field(
            "WS-FLAG",
            "alpha",
            1,
            values_88={"FLAG-YES": "'Y'", "FLAG-NO": "'N'"},
        )
        domain = build_domain(fld)
        assert domain.classification == "flag"
        assert domain.valid_88_values == {"FLAG-YES": "'Y'", "FLAG-NO": "'N'"}

    def test_date_field_semantic_type(self) -> None:
        fld = _make_field("WS-TRANSACTION-DT", "numeric", 8)
        domain = build_domain(fld)
        assert domain.semantic_type == "date"

    def test_default_value_quoted_string(self) -> None:
        fld = _make_field("WS-FLAG", "alpha", 1, value_clause="'N'")
        domain = build_domain(fld)
        assert domain.default_value == "N"

    def test_default_value_spaces(self) -> None:
        fld = _make_field("WS-NAME", "alpha", 30, value_clause="SPACES")
        domain = build_domain(fld)
        assert domain.default_value == " "

    def test_default_value_zeros(self) -> None:
        fld = _make_field("WS-CNT", "numeric", 5, value_clause="ZERO")
        domain = build_domain(fld)
        assert domain.default_value == "0"

    def test_default_value_none(self) -> None:
        fld = _make_field("WS-STATUS", "alpha", 2)
        domain = build_domain(fld)
        assert domain.default_value is None

    def test_group_item_becomes_unknown(self) -> None:
        fld = FieldDefinition(
            level=1,
            name="WS-VARIABLES",
            pic_clause=None,
            pic_type="group",
            length=0,
            precision=0,
            signed=False,
            usage="",
            value_clause=None,
            parent_name=None,
            is_filler=False,
        )
        domain = build_domain(fld)
        assert domain.data_type == "unknown"
        assert domain.min_value is None
        assert domain.max_value is None
