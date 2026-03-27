"""Tests for cobol_penetrator.analysis.pic_parser.

Validates PIC clause parsing for all major COBOL data type patterns:
alphanumeric, numeric, signed, packed decimal, computational, and
edge cases.
"""

from __future__ import annotations

import pytest

from cobol_penetrator.analysis.pic_parser import parse_pic


# ---------------------------------------------------------------------------
# Alphanumeric PIC X patterns
# ---------------------------------------------------------------------------

class TestAlphaPic:
    """Verify parsing of PIC X (alphanumeric) clauses."""

    def test_pic_x_with_length(self) -> None:
        pic_type, length, precision, signed = parse_pic("X(02)")
        assert pic_type == "alpha"
        assert length == 2
        assert precision == 0
        assert signed is False

    def test_pic_x_single(self) -> None:
        pic_type, length, precision, signed = parse_pic("X")
        assert pic_type == "alpha"
        assert length == 1

    def test_pic_x_large(self) -> None:
        pic_type, length, precision, signed = parse_pic("X(256)")
        assert pic_type == "alpha"
        assert length == 256

    def test_pic_xx(self) -> None:
        """PIC XX is shorthand for X(2)."""
        pic_type, length, precision, signed = parse_pic("XX")
        assert pic_type == "alpha"
        assert length == 2

    def test_pic_x_mixed(self) -> None:
        """PIC X(10)XX means 12 characters."""
        pic_type, length, precision, signed = parse_pic("X(10)XX")
        assert pic_type == "alpha"
        assert length == 12

    def test_pic_x_not_signed(self) -> None:
        _, _, _, signed = parse_pic("X(30)")
        assert signed is False


# ---------------------------------------------------------------------------
# Numeric PIC 9 patterns
# ---------------------------------------------------------------------------

class TestNumericPic:
    """Verify parsing of PIC 9 (numeric) clauses."""

    def test_pic_9_with_length(self) -> None:
        pic_type, length, precision, signed = parse_pic("9(09)")
        assert pic_type == "numeric"
        assert length == 9
        assert precision == 0
        assert signed is False

    def test_pic_9_single(self) -> None:
        pic_type, length, precision, signed = parse_pic("9")
        assert pic_type == "numeric"
        assert length == 1

    def test_pic_99(self) -> None:
        """PIC 99 is shorthand for 9(2)."""
        pic_type, length, precision, signed = parse_pic("99")
        assert pic_type == "numeric"
        assert length == 2

    def test_pic_9_five_digits(self) -> None:
        pic_type, length, precision, signed = parse_pic("9(05)")
        assert pic_type == "numeric"
        assert length == 5

    def test_pic_9_eleven_digits(self) -> None:
        pic_type, length, precision, signed = parse_pic("9(11)")
        assert pic_type == "numeric"
        assert length == 11


# ---------------------------------------------------------------------------
# Signed numeric PIC S9 patterns
# ---------------------------------------------------------------------------

class TestSignedNumericPic:
    """Verify parsing of PIC S9 (signed numeric) clauses."""

    def test_pic_s9_basic(self) -> None:
        pic_type, length, precision, signed = parse_pic("S9(09)")
        assert pic_type == "numeric"
        assert length == 9
        assert precision == 0
        assert signed is True

    def test_pic_s9_with_decimal(self) -> None:
        pic_type, length, precision, signed = parse_pic("S9(07)V99")
        assert pic_type == "numeric"
        assert length == 7
        assert precision == 2
        assert signed is True

    def test_pic_s9_v9_4(self) -> None:
        pic_type, length, precision, signed = parse_pic("S9(05)V9(4)")
        assert pic_type == "numeric"
        assert length == 5
        assert precision == 4
        assert signed is True

    def test_pic_s9_small(self) -> None:
        pic_type, length, precision, signed = parse_pic("S9(4)")
        assert pic_type == "numeric"
        assert length == 4
        assert signed is True


# ---------------------------------------------------------------------------
# Decimal precision (V) patterns
# ---------------------------------------------------------------------------

class TestDecimalPrecision:
    """Verify parsing of implied decimal point (V) in PIC clauses."""

    def test_v99(self) -> None:
        _, _, precision, _ = parse_pic("9(5)V99")
        assert precision == 2

    def test_v9_4(self) -> None:
        _, _, precision, _ = parse_pic("9(3)V9(4)")
        assert precision == 4

    def test_v9_6(self) -> None:
        _, _, precision, _ = parse_pic("S9(18)V9(6)")
        assert precision == 6

    def test_no_decimal(self) -> None:
        _, _, precision, _ = parse_pic("9(9)")
        assert precision == 0


# ---------------------------------------------------------------------------
# COMP / COMP-3 (USAGE clause) patterns
# ---------------------------------------------------------------------------

class TestCompUsage:
    """Verify parsing with COMP and COMP-3 USAGE clauses."""

    def test_comp_3(self) -> None:
        pic_type, length, precision, signed = parse_pic(
            "S9(07)V99", "COMP-3"
        )
        assert pic_type == "packed"
        assert length == 7
        assert precision == 2
        assert signed is True

    def test_comp(self) -> None:
        pic_type, length, precision, signed = parse_pic(
            "S9(09)", "COMP"
        )
        assert pic_type == "comp"
        assert length == 9
        assert signed is True

    def test_binary(self) -> None:
        pic_type, length, precision, signed = parse_pic(
            "S9(9)", "BINARY"
        )
        assert pic_type == "comp"
        assert length == 9

    def test_packed_decimal_usage(self) -> None:
        pic_type, length, precision, signed = parse_pic(
            "S9(15)", "PACKED-DECIMAL"
        )
        assert pic_type == "packed"
        assert length == 15

    def test_comp_3_with_decimal(self) -> None:
        pic_type, length, precision, signed = parse_pic(
            "S9(09)V99", "COMP-3"
        )
        assert pic_type == "packed"
        assert length == 9
        assert precision == 2

    def test_comp_unsigned(self) -> None:
        pic_type, length, precision, signed = parse_pic(
            "9(4)", "COMP"
        )
        assert pic_type == "comp"
        assert length == 4
        assert signed is False


# ---------------------------------------------------------------------------
# Group items (empty PIC)
# ---------------------------------------------------------------------------

class TestGroupItems:
    """Verify handling of group items with no PIC clause."""

    def test_empty_pic(self) -> None:
        pic_type, length, precision, signed = parse_pic("")
        assert pic_type == "group"
        assert length == 0
        assert precision == 0
        assert signed is False

    def test_whitespace_pic(self) -> None:
        pic_type, length, precision, signed = parse_pic("  ")
        assert pic_type == "group"
        assert length == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Verify edge cases and unusual PIC clause formats."""

    def test_leading_plus(self) -> None:
        """PIC +9(5) should be numeric."""
        pic_type, length, _, signed = parse_pic("+9(5)")
        assert pic_type == "numeric"
        assert length == 5

    def test_leading_minus(self) -> None:
        """PIC -9(5) should be numeric."""
        pic_type, length, _, signed = parse_pic("-9(5)")
        assert pic_type == "numeric"
        assert length == 5

    def test_case_insensitive(self) -> None:
        """PIC clauses should be case-insensitive."""
        pic_type, length, _, _ = parse_pic("x(10)")
        assert pic_type == "alpha"
        assert length == 10

    def test_pic_with_spaces(self) -> None:
        """PIC clause with surrounding spaces."""
        pic_type, length, _, _ = parse_pic("  X(05)  ")
        assert pic_type == "alpha"
        assert length == 5
