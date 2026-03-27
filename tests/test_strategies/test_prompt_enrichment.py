"""Tests for cobol_penetrator.strategies.prompt_enrichment."""

from __future__ import annotations

import pytest

from cobol_penetrator.analysis.variable_domain import VariableDomain
from cobol_penetrator.strategies.prompt_enrichment import (
    format_condition_hints,
    format_execution_history,
    format_variable_metadata,
)


# ---------------------------------------------------------------------------
# Helpers: lightweight FieldReport stand-in
# ---------------------------------------------------------------------------


class _FakeFieldReport:
    """Minimal FieldReport-like object for testing prompt formatting."""

    def __init__(
        self,
        fields: dict[str, VariableDomain] | None = None,
        condition_hints: dict[str, list] | None = None,
    ) -> None:
        self.fields = fields or {}
        self.condition_hints = condition_hints or {}
        self.stub_variables: dict[str, str] = {}
        self.stub_operations: list[str] = []


def _make_domain(
    name: str,
    data_type: str = "alpha",
    max_length: int = 2,
    semantic_type: str = "generic",
    classification: str = "internal",
    condition_literals: list | None = None,
    valid_88_values: dict | None = None,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    set_by_stub: str | None = None,
    default_value: str | None = None,
    signed: bool = False,
    precision: int = 0,
) -> VariableDomain:
    """Build a VariableDomain with minimal boilerplate."""
    return VariableDomain(
        name=name,
        data_type=data_type,
        max_length=max_length,
        precision=precision,
        signed=signed,
        min_value=min_value,
        max_value=max_value,
        condition_literals=condition_literals or [],
        valid_88_values=valid_88_values or {},
        classification=classification,
        semantic_type=semantic_type,
        set_by_stub=set_by_stub,
        default_value=default_value,
    )


# ---------------------------------------------------------------------------
# Tests: format_variable_metadata
# ---------------------------------------------------------------------------


class TestFormatVariableMetadata:
    """Tests for format_variable_metadata."""

    def test_empty_fields_returns_empty_string(self) -> None:
        report = _FakeFieldReport(fields={})
        result = format_variable_metadata(report)
        assert result == ""

    def test_single_alpha_field(self) -> None:
        fields = {
            "WS-STATUS": _make_domain(
                "WS-STATUS",
                data_type="alpha",
                max_length=2,
                semantic_type="status_file",
                classification="status",
            ),
        }
        report = _FakeFieldReport(fields=fields)
        result = format_variable_metadata(report)
        assert "Variable Definitions:" in result
        assert "WS-STATUS" in result
        assert "PIC X(02)" in result
        assert "type=alpha" in result
        assert "semantic=status_file" in result

    def test_numeric_field_includes_range(self) -> None:
        fields = {
            "WS-AMOUNT": _make_domain(
                "WS-AMOUNT",
                data_type="numeric",
                max_length=9,
                semantic_type="amount",
                min_value=0,
                max_value=999999999,
            ),
        }
        report = _FakeFieldReport(fields=fields)
        result = format_variable_metadata(report)
        assert "range=0..999999999" in result
        assert "type=numeric" in result

    def test_field_with_condition_literals(self) -> None:
        fields = {
            "WS-STATUS": _make_domain(
                "WS-STATUS",
                condition_literals=["00", "10", "23"],
            ),
        }
        report = _FakeFieldReport(fields=fields)
        result = format_variable_metadata(report)
        assert "Known values:" in result
        assert "'00'" in result
        assert "'10'" in result
        assert "'23'" in result

    def test_field_with_88_values(self) -> None:
        fields = {
            "WS-FLAG": _make_domain(
                "WS-FLAG",
                valid_88_values={"FLAG-YES": "Y", "FLAG-NO": "N"},
            ),
        }
        report = _FakeFieldReport(fields=fields)
        result = format_variable_metadata(report)
        assert "Known values:" in result
        assert "'Y'" in result
        assert "'N'" in result

    def test_field_with_default_value(self) -> None:
        fields = {
            "WS-STATUS": _make_domain(
                "WS-STATUS",
                default_value="00",
            ),
        }
        report = _FakeFieldReport(fields=fields)
        result = format_variable_metadata(report)
        assert "Default:" in result
        assert "'00'" in result

    def test_field_with_stub_relationship(self) -> None:
        fields = {
            "WS-STATUS": _make_domain(
                "WS-STATUS",
                set_by_stub="READ-ACCOUNT",
            ),
        }
        report = _FakeFieldReport(fields=fields)
        result = format_variable_metadata(report)
        assert "set_by_stub=READ-ACCOUNT" in result

    def test_relevant_vars_filters_output(self) -> None:
        fields = {
            "WS-STATUS": _make_domain("WS-STATUS"),
            "WS-FLAG": _make_domain("WS-FLAG"),
            "WS-AMOUNT": _make_domain("WS-AMOUNT"),
        }
        report = _FakeFieldReport(fields=fields)
        result = format_variable_metadata(report, relevant_vars=["WS-STATUS"])
        assert "WS-STATUS" in result
        assert "WS-FLAG" not in result
        assert "WS-AMOUNT" not in result

    def test_relevant_vars_nonexistent_name_ignored(self) -> None:
        fields = {"WS-STATUS": _make_domain("WS-STATUS")}
        report = _FakeFieldReport(fields=fields)
        result = format_variable_metadata(
            report, relevant_vars=["NONEXISTENT"]
        )
        assert result == ""

    def test_generic_semantic_type_omitted(self) -> None:
        fields = {
            "WS-TEMP": _make_domain(
                "WS-TEMP",
                semantic_type="generic",
            ),
        }
        report = _FakeFieldReport(fields=fields)
        result = format_variable_metadata(report)
        assert "semantic=" not in result

    def test_signed_numeric_field(self) -> None:
        fields = {
            "WS-BAL": _make_domain(
                "WS-BAL",
                data_type="numeric",
                max_length=7,
                signed=True,
                precision=2,
            ),
        }
        report = _FakeFieldReport(fields=fields)
        result = format_variable_metadata(report)
        assert "PIC S9(7)V9(2)" in result


# ---------------------------------------------------------------------------
# Tests: format_condition_hints
# ---------------------------------------------------------------------------


class TestFormatConditionHints:
    """Tests for format_condition_hints."""

    def test_empty_hints_returns_empty_string(self) -> None:
        report = _FakeFieldReport(condition_hints={})
        result = format_condition_hints(report)
        assert result == ""

    def test_single_variable_hints(self) -> None:
        report = _FakeFieldReport(
            condition_hints={"WS-STATUS": ["00", "10", "23"]}
        )
        result = format_condition_hints(report)
        assert "Condition values found in program:" in result
        assert "WS-STATUS is compared to:" in result
        assert "'00'" in result
        assert "'10'" in result
        assert "'23'" in result

    def test_multiple_variables(self) -> None:
        report = _FakeFieldReport(
            condition_hints={
                "WS-STATUS": ["00", "10"],
                "WS-FLAG": ["Y", "N"],
            }
        )
        result = format_condition_hints(report)
        assert "WS-STATUS is compared to:" in result
        assert "WS-FLAG is compared to:" in result

    def test_relevant_vars_filters(self) -> None:
        report = _FakeFieldReport(
            condition_hints={
                "WS-STATUS": ["00"],
                "WS-FLAG": ["Y"],
            }
        )
        result = format_condition_hints(
            report, relevant_vars=["WS-STATUS"]
        )
        assert "WS-STATUS" in result
        assert "WS-FLAG" not in result

    def test_empty_values_list_omitted(self) -> None:
        report = _FakeFieldReport(
            condition_hints={"WS-EMPTY": []}
        )
        result = format_condition_hints(report)
        assert result == ""

    def test_relevant_vars_no_match_returns_empty(self) -> None:
        report = _FakeFieldReport(
            condition_hints={"WS-STATUS": ["00"]}
        )
        result = format_condition_hints(
            report, relevant_vars=["NONEXISTENT"]
        )
        assert result == ""


# ---------------------------------------------------------------------------
# Tests: format_execution_history
# ---------------------------------------------------------------------------


class TestFormatExecutionHistory:
    """Tests for format_execution_history."""

    def test_empty_history_returns_empty_string(self) -> None:
        result = format_execution_history([])
        assert result == ""

    def test_single_attempt(self) -> None:
        history = [
            {
                "input_state": {"WS-STATUS": "00"},
                "stubs": {"READ-ACCOUNT": {"alpha_status": "00"}},
                "paragraphs_hit": ["1000-MAIN", "2000-VALIDATE"],
                "branches_hit": {"1": "T"},
            }
        ]
        result = format_execution_history(history)
        assert "Prior attempts (most recent first):" in result
        assert "Attempt 1:" in result
        assert "WS-STATUS" in result
        assert "1 stub(s)" in result
        assert "2 paragraph(s)" in result
        assert "1 branch(es)" in result

    def test_multiple_attempts(self) -> None:
        history = [
            {
                "input_state": {"WS-STATUS": "00"},
                "stubs": {},
                "paragraphs_hit": ["1000-MAIN"],
                "branches_hit": {},
            },
            {
                "input_state": {"WS-STATUS": "10"},
                "stubs": {},
                "paragraphs_hit": ["1000-MAIN", "2000-VALIDATE"],
                "branches_hit": {"1": "T"},
            },
        ]
        result = format_execution_history(history)
        assert "Attempt 1:" in result
        assert "Attempt 2:" in result

    def test_max_entries_limits_output(self) -> None:
        history = [
            {
                "input_state": {"WS-STATUS": str(i)},
                "stubs": {},
                "paragraphs_hit": [],
                "branches_hit": {},
            }
            for i in range(10)
        ]
        result = format_execution_history(history, max_entries=3)
        assert "Attempt 1:" in result
        assert "Attempt 3:" in result
        assert "Attempt 4:" not in result

    def test_empty_input_state_shows_empty(self) -> None:
        history = [
            {
                "input_state": {},
                "stubs": {},
                "paragraphs_hit": [],
                "branches_hit": {},
            }
        ]
        result = format_execution_history(history)
        assert "input={empty}" in result

    def test_many_input_vars_truncated(self) -> None:
        state = {f"VAR-{i}": str(i) for i in range(10)}
        history = [
            {
                "input_state": state,
                "stubs": {},
                "paragraphs_hit": [],
                "branches_hit": {},
            }
        ]
        result = format_execution_history(history)
        assert "+5 more" in result

    def test_no_stubs_shows_none(self) -> None:
        history = [
            {
                "input_state": {"A": "1"},
                "stubs": {},
                "paragraphs_hit": [],
                "branches_hit": {},
            }
        ]
        result = format_execution_history(history)
        assert "stubs=none" in result

    def test_missing_keys_handled_gracefully(self) -> None:
        """Entries with missing keys should not raise."""
        history = [{}]
        result = format_execution_history(history)
        assert "Attempt 1:" in result
        assert "input={empty}" in result
