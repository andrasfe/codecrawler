"""Tests for cobol_penetrator.heuristics.value_generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from cobol_penetrator.heuristics.value_generator import (
    format_value_for_mock,
    generate_value,
)


@dataclass
class MockDomain:
    """Test stand-in for VariableDomainLike."""

    name: str = "WS-TEST"
    data_type: str = "alpha"
    max_length: int = 10
    precision: int = 0
    signed: bool = False
    min_value: int | float | None = None
    max_value: int | float | None = None
    condition_literals: list = field(default_factory=list)
    valid_88_values: dict[str, str] = field(default_factory=dict)
    classification: str = "data"
    semantic_type: str = ""


# ---------------------------------------------------------------------------
# Fixtures — reusable domain objects
# ---------------------------------------------------------------------------


def _alpha_domain(**overrides) -> MockDomain:
    defaults = dict(
        name="WS-NAME", data_type="alpha", max_length=10,
    )
    defaults.update(overrides)
    return MockDomain(**defaults)


def _numeric_domain(**overrides) -> MockDomain:
    defaults = dict(
        name="WS-AMOUNT", data_type="numeric", max_length=9,
        min_value=0, max_value=999999999,
    )
    defaults.update(overrides)
    return MockDomain(**defaults)


def _decimal_domain(**overrides) -> MockDomain:
    defaults = dict(
        name="WS-RATE", data_type="numeric", max_length=7,
        precision=2, min_value=0.0, max_value=99999.99,
    )
    defaults.update(overrides)
    return MockDomain(**defaults)


def _date_domain(**overrides) -> MockDomain:
    defaults = dict(
        name="WS-DATE", data_type="numeric", max_length=8,
        semantic_type="date",
    )
    defaults.update(overrides)
    return MockDomain(**defaults)


def _flag_domain(**overrides) -> MockDomain:
    defaults = dict(
        name="WS-FLAG", data_type="alpha", max_length=1,
        classification="flag", semantic_type="flag_bool",
        valid_88_values={"YES": "Y", "NO": "N"},
    )
    defaults.update(overrides)
    return MockDomain(**defaults)


def _status_domain(**overrides) -> MockDomain:
    defaults = dict(
        name="WS-FILE-STATUS", data_type="alpha", max_length=2,
        classification="status", semantic_type="status_file",
    )
    defaults.update(overrides)
    return MockDomain(**defaults)


# ---------------------------------------------------------------------------
# Strategy: condition_literal
# ---------------------------------------------------------------------------


class TestConditionLiteral:
    """Test the condition_literal strategy."""

    def test_picks_from_literals(self) -> None:
        domain = _alpha_domain(condition_literals=["ACTIVE", "CLOSED"])
        rng = Random(42)
        for _ in range(20):
            val = generate_value(domain, "condition_literal", rng)
            assert val in ["ACTIVE", "CLOSED"]

    def test_empty_literals_falls_back_to_random(self) -> None:
        domain = _alpha_domain(condition_literals=[])
        rng = Random(42)
        val = generate_value(domain, "condition_literal", rng)
        # Should produce a random_valid alpha string
        assert isinstance(val, str)
        assert len(val) == domain.max_length

    def test_deterministic_with_seed(self) -> None:
        domain = _alpha_domain(condition_literals=["A", "B", "C", "D"])
        val1 = generate_value(domain, "condition_literal", Random(99))
        val2 = generate_value(domain, "condition_literal", Random(99))
        assert val1 == val2


# ---------------------------------------------------------------------------
# Strategy: 88_value
# ---------------------------------------------------------------------------


class TestValue88:
    """Test the 88_value strategy."""

    def test_picks_from_88_values(self) -> None:
        domain = _flag_domain()
        rng = Random(42)
        for _ in range(20):
            val = generate_value(domain, "88_value", rng)
            assert val in ["Y", "N"]

    def test_empty_88_values_falls_back(self) -> None:
        domain = _alpha_domain(valid_88_values={})
        rng = Random(42)
        val = generate_value(domain, "88_value", rng)
        assert isinstance(val, str)

    def test_multiple_88_values(self) -> None:
        domain = _alpha_domain(
            valid_88_values={"HIGH": "H", "MED": "M", "LOW": "L"}
        )
        rng = Random(42)
        seen = set()
        for _ in range(50):
            seen.add(generate_value(domain, "88_value", rng))
        assert seen == {"H", "M", "L"}


# ---------------------------------------------------------------------------
# Strategy: boundary
# ---------------------------------------------------------------------------


class TestBoundary:
    """Test the boundary strategy."""

    def test_alpha_boundary_values(self) -> None:
        domain = _alpha_domain(max_length=5)
        rng = Random(42)
        seen = set()
        for _ in range(50):
            seen.add(generate_value(domain, "boundary", rng))
        assert "" in seen
        assert " " * 5 in seen
        assert "A" * 5 in seen

    def test_numeric_boundary_includes_min_max(self) -> None:
        domain = _numeric_domain(min_value=0, max_value=100)
        rng = Random(42)
        seen = set()
        for _ in range(100):
            seen.add(generate_value(domain, "boundary", rng))
        assert 0 in seen
        assert 100 in seen

    def test_numeric_boundary_includes_mid(self) -> None:
        domain = _numeric_domain(min_value=0, max_value=100)
        rng = Random(42)
        seen = set()
        for _ in range(100):
            seen.add(generate_value(domain, "boundary", rng))
        assert 50 in seen

    def test_numeric_boundary_includes_plus_minus_one(self) -> None:
        domain = _numeric_domain(min_value=0, max_value=100)
        rng = Random(42)
        seen = set()
        for _ in range(200):
            seen.add(generate_value(domain, "boundary", rng))
        assert 1 in seen
        assert 99 in seen

    def test_decimal_boundary_mid(self) -> None:
        domain = _decimal_domain(min_value=0.0, max_value=100.0, precision=2)
        rng = Random(42)
        seen = set()
        for _ in range(100):
            seen.add(generate_value(domain, "boundary", rng))
        # Mid should be 50.0 (not int 50 since precision > 0)
        assert 50.0 in seen

    def test_no_range_returns_zero(self) -> None:
        domain = _numeric_domain(min_value=None, max_value=None)
        rng = Random(42)
        val = generate_value(domain, "boundary", rng)
        assert val == 0


# ---------------------------------------------------------------------------
# Strategy: semantic
# ---------------------------------------------------------------------------


class TestSemantic:
    """Test the semantic strategy."""

    def test_date_format_8_digit(self) -> None:
        domain = _date_domain(max_length=8)
        rng = Random(42)
        val = generate_value(domain, "semantic", rng)
        assert isinstance(val, str)
        assert len(val) == 8
        year = int(val[:4])
        assert 2020 <= year <= 2027

    def test_date_format_6_digit(self) -> None:
        domain = _date_domain(max_length=6)
        rng = Random(42)
        val = generate_value(domain, "semantic", rng)
        assert isinstance(val, str)
        assert len(val) == 6

    def test_time_format(self) -> None:
        domain = MockDomain(
            name="WS-TIME", data_type="numeric", max_length=6,
            semantic_type="time",
        )
        rng = Random(42)
        val = generate_value(domain, "semantic", rng)
        assert isinstance(val, str)
        assert len(val) == 6
        h = int(val[:2])
        assert 0 <= h <= 23

    def test_amount_integer(self) -> None:
        domain = MockDomain(
            name="WS-AMT", data_type="numeric", max_length=9,
            precision=0, semantic_type="amount",
        )
        rng = Random(42)
        val = generate_value(domain, "semantic", rng)
        assert isinstance(val, int)
        assert 0 <= val <= 999999

    def test_amount_decimal(self) -> None:
        domain = MockDomain(
            name="WS-AMT", data_type="numeric", max_length=9,
            precision=2, semantic_type="amount",
        )
        rng = Random(42)
        val = generate_value(domain, "semantic", rng)
        assert isinstance(val, float)
        assert 0.01 <= val <= 999999.99

    def test_counter(self) -> None:
        domain = MockDomain(
            name="WS-CTR", data_type="numeric", max_length=3,
            semantic_type="counter",
        )
        rng = Random(42)
        val = generate_value(domain, "semantic", rng)
        assert isinstance(val, int)
        assert 0 <= val <= 100

    def test_identifier(self) -> None:
        domain = MockDomain(
            name="WS-ACCT-ID", data_type="numeric", max_length=10,
            semantic_type="identifier",
        )
        rng = Random(42)
        val = generate_value(domain, "semantic", rng)
        assert isinstance(val, str)
        assert len(val) == 10

    def test_status_file(self) -> None:
        domain = _status_domain()
        rng = Random(42)
        val = generate_value(domain, "semantic", rng)
        assert isinstance(val, str)
        assert len(val) == 2

    def test_status_sql(self) -> None:
        domain = MockDomain(
            name="WS-SQLCODE", data_type="numeric", max_length=4,
            semantic_type="status_sql",
        )
        rng = Random(42)
        val = generate_value(domain, "semantic", rng)
        assert isinstance(val, int)

    def test_flag_bool_with_88_values(self) -> None:
        domain = _flag_domain()
        rng = Random(42)
        for _ in range(20):
            val = generate_value(domain, "semantic", rng)
            assert val in ["Y", "N"]

    def test_flag_bool_without_88_values(self) -> None:
        domain = MockDomain(
            name="WS-FLAG", data_type="alpha", max_length=1,
            semantic_type="flag_bool", valid_88_values={},
        )
        rng = Random(42)
        for _ in range(20):
            val = generate_value(domain, "semantic", rng)
            assert val in ["Y", "N"]

    def test_unknown_semantic_falls_back_to_random(self) -> None:
        domain = _alpha_domain(semantic_type="unknown_thing")
        rng = Random(42)
        val = generate_value(domain, "semantic", rng)
        assert isinstance(val, str)
        assert len(val) == domain.max_length


# ---------------------------------------------------------------------------
# Strategy: adversarial
# ---------------------------------------------------------------------------


class TestAdversarial:
    """Test the adversarial strategy."""

    def test_alpha_adversarial(self) -> None:
        domain = _alpha_domain(max_length=5)
        rng = Random(42)
        seen = set()
        for _ in range(50):
            seen.add(generate_value(domain, "adversarial", rng))
        assert "" in seen
        assert " " * 5 in seen
        assert "9" * 5 in seen
        assert "A" * 5 in seen

    def test_numeric_adversarial_includes_zero(self) -> None:
        domain = _numeric_domain(min_value=-100, max_value=100)
        rng = Random(42)
        seen = set()
        for _ in range(100):
            seen.add(generate_value(domain, "adversarial", rng))
        assert 0 in seen

    def test_numeric_adversarial_includes_all_nines(self) -> None:
        domain = _numeric_domain(max_length=3)
        rng = Random(42)
        seen = set()
        for _ in range(100):
            seen.add(generate_value(domain, "adversarial", rng))
        assert 999 in seen

    def test_signed_numeric_includes_negative_nines(self) -> None:
        domain = _numeric_domain(max_length=3, signed=True)
        rng = Random(42)
        seen = set()
        for _ in range(100):
            seen.add(generate_value(domain, "adversarial", rng))
        assert -999 in seen

    def test_unsigned_numeric_no_negative_nines(self) -> None:
        domain = _numeric_domain(max_length=3, signed=False)
        rng = Random(42)
        seen = set()
        for _ in range(200):
            seen.add(generate_value(domain, "adversarial", rng))
        assert -999 not in seen


# ---------------------------------------------------------------------------
# Strategy: random_valid
# ---------------------------------------------------------------------------


class TestRandomValid:
    """Test the random_valid strategy."""

    def test_alpha_random_correct_length(self) -> None:
        domain = _alpha_domain(max_length=15)
        rng = Random(42)
        val = generate_value(domain, "random_valid", rng)
        assert isinstance(val, str)
        assert len(val) == 15

    def test_alpha_random_valid_chars(self) -> None:
        domain = _alpha_domain(max_length=100)
        rng = Random(42)
        val = generate_value(domain, "random_valid", rng)
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ")
        assert all(c in valid_chars for c in val)

    def test_numeric_integer_in_range(self) -> None:
        domain = _numeric_domain(min_value=10, max_value=20)
        rng = Random(42)
        for _ in range(50):
            val = generate_value(domain, "random_valid", rng)
            assert isinstance(val, int)
            assert 10 <= val <= 20

    def test_numeric_decimal_in_range(self) -> None:
        domain = _decimal_domain(min_value=1.0, max_value=10.0, precision=2)
        rng = Random(42)
        for _ in range(50):
            val = generate_value(domain, "random_valid", rng)
            assert isinstance(val, float)
            assert 1.0 <= val <= 10.0

    def test_numeric_no_range_uses_defaults(self) -> None:
        domain = _numeric_domain(min_value=None, max_value=None)
        rng = Random(42)
        val = generate_value(domain, "random_valid", rng)
        assert isinstance(val, int)
        assert 0 <= val <= 99999

    def test_alpha_min_length_one(self) -> None:
        domain = _alpha_domain(max_length=0)
        rng = Random(42)
        val = generate_value(domain, "random_valid", rng)
        assert len(val) >= 1

    def test_deterministic_with_same_seed(self) -> None:
        domain = _numeric_domain(min_value=0, max_value=1000)
        val1 = generate_value(domain, "random_valid", Random(123))
        val2 = generate_value(domain, "random_valid", Random(123))
        assert val1 == val2


# ---------------------------------------------------------------------------
# Default rng
# ---------------------------------------------------------------------------


class TestDefaultRng:
    """Test that generate_value works without explicit rng."""

    def test_no_rng_produces_value(self) -> None:
        domain = _alpha_domain()
        val = generate_value(domain, "random_valid")
        assert isinstance(val, str)


# ---------------------------------------------------------------------------
# format_value_for_mock
# ---------------------------------------------------------------------------


class TestFormatValueForMock:
    """Test the format_value_for_mock function."""

    def test_alpha_truncated_to_20(self) -> None:
        domain = _alpha_domain(max_length=30)
        result = format_value_for_mock(domain, "A" * 30)
        assert len(result) == 20

    def test_alpha_short_unchanged(self) -> None:
        domain = _alpha_domain(max_length=5)
        result = format_value_for_mock(domain, "HELLO")
        assert result == "HELLO"

    def test_numeric_int_fits(self) -> None:
        domain = _numeric_domain()
        result = format_value_for_mock(domain, 12345)
        assert result == "12345"

    def test_numeric_int_too_large_clamped(self) -> None:
        domain = _numeric_domain()
        result = format_value_for_mock(domain, 1234567890)
        assert result == "999999999"

    def test_numeric_negative_too_large_clamped(self) -> None:
        domain = _numeric_domain(signed=True)
        result = format_value_for_mock(domain, -1234567890)
        assert result == "-999999999"

    def test_numeric_float_truncated(self) -> None:
        domain = _decimal_domain(precision=2)
        result = format_value_for_mock(domain, 12345.67)
        assert len(result) <= 9

    def test_numeric_float_zero_precision(self) -> None:
        domain = MockDomain(
            name="WS-X", data_type="numeric", max_length=5,
            precision=0,
        )
        result = format_value_for_mock(domain, 42.0)
        assert result == "42"

    def test_unknown_type_treated_as_alpha(self) -> None:
        domain = MockDomain(
            name="WS-X", data_type="unknown", max_length=25,
        )
        result = format_value_for_mock(domain, "X" * 25)
        assert len(result) == 20

    def test_string_value_for_numeric_domain(self) -> None:
        domain = _numeric_domain()
        result = format_value_for_mock(domain, "00")
        assert result == "00"
