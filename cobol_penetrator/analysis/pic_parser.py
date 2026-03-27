"""PIC clause parsing for COBOL data type analysis.

Parses COBOL PICTURE (PIC) clauses and USAGE directives to extract
data type information: type category, length, decimal precision,
and sign indicator.
"""

from __future__ import annotations

import re


def parse_pic(
    pic_clause: str, usage: str = ""
) -> tuple[str, int, int, bool]:
    """Parse a COBOL PIC clause and optional USAGE into type information.

    Args:
        pic_clause: The PIC clause string (e.g. "X(02)", "S9(7)V99").
        usage: The USAGE clause string (e.g. "COMP", "COMP-3", "").

    Returns:
        A 4-tuple of (pic_type, length, precision, signed) where:
        - pic_type: one of "alpha", "numeric", "packed", "comp", "group"
        - length: integer digit or character positions
        - precision: number of decimal places (after V)
        - signed: True if PIC starts with S
    """
    pic = pic_clause.strip().upper()
    usage_up = usage.strip().upper()

    # Handle empty PIC (group items)
    if not pic:
        return ("group", 0, 0, False)

    # Determine signedness from PIC S prefix
    signed = pic.startswith("S")

    # Determine precision from V (implied decimal point)
    precision = 0
    if "V" in pic:
        after_v = pic.split("V", 1)[1]
        precision = _count_nines(after_v)

    # USAGE overrides base type determination
    if "COMP-3" in usage_up or "PACKED" in usage_up:
        length = _integer_digits(pic)
        return ("packed", length, precision, signed)
    if "COMP" in usage_up or "BINARY" in usage_up:
        length = _integer_digits(pic)
        return ("comp", length, precision, signed)

    # Determine type from PIC pattern itself
    if pic.startswith("X") or "X(" in pic:
        length = _count_alpha(pic)
        return ("alpha", length, 0, False)

    # Hex literal: X'nn'
    if "X'" in pic:
        length = _count_alpha(pic)
        return ("alpha", length, 0, False)

    if (
        pic.startswith("S")
        or pic.startswith("9")
        or pic.startswith("+")
        or pic.startswith("-")
    ):
        length = _integer_digits(pic)
        return ("numeric", length, precision, signed)

    # Fallback: treat as alpha
    length = _count_alpha(pic)
    return ("alpha", length, 0, False)


def _count_alpha(pic: str) -> int:
    """Count character length from PIC X patterns.

    Handles both X(n) notation and standalone X characters.
    """
    total = 0
    for m in re.finditer(r"X\((\d+)\)", pic):
        total += int(m.group(1))
    # Remove X(n) patterns, then count remaining standalone X
    stripped = re.sub(r"X\(\d+\)", "", pic)
    total += stripped.count("X")
    if total == 0:
        # Try counting 9s for numeric display used as alpha
        total = _total_digits(pic)
    return max(total, 1)


def _count_nines(s: str) -> int:
    """Count digit positions from a PIC fragment like '99' or '9(4)'.

    Handles both 9(n) notation and standalone 9 characters.
    """
    total = 0
    for m in re.finditer(r"9\((\d+)\)", s):
        total += int(m.group(1))
    stripped = re.sub(r"9\(\d+\)", "", s)
    total += stripped.count("9")
    return total


def _integer_digits(pic: str) -> int:
    """Count integer digit positions (before V) in a PIC clause.

    Strips leading sign/fill characters (S, +, -) and splits at V.
    """
    s = pic.lstrip("S+-")
    if "V" in s:
        s = s.split("V", 1)[0]
    result = _count_nines(s)
    return max(result, 1)


def _total_digits(pic: str) -> int:
    """Count all digit positions (before and after V) in a PIC clause."""
    s = pic.lstrip("S+-")
    result = _count_nines(s)
    return max(result, 1)
