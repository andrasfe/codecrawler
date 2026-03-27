"""Harvest condition literals from PROCEDURE DIVISION in .mock.cbl files.

Scans IF statements and EVALUATE/WHEN blocks to extract literal values
that are compared against variables, building a map of variable names
to their observed comparison values.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Comparison operators in COBOL conditions
_CMP_RE = re.compile(
    r"\bNOT\s+EQUAL(?:\s+TO)?\b|\bEQUAL(?:\s+TO)?\b"
    r"|\bNOT\s+=\b|\bGREATER(?:\s+THAN)?\b|\bLESS(?:\s+THAN)?\b"
    r"|[><=]+|=",
    re.IGNORECASE,
)

# COBOL keywords to exclude from variable name detection
_KEYWORDS = frozenset(
    {
        "IF",
        "ELSE",
        "END-IF",
        "THEN",
        "NOT",
        "AND",
        "OR",
        "EQUAL",
        "EQUALS",
        "GREATER",
        "LESS",
        "THAN",
        "TO",
        "NUMERIC",
        "ALPHABETIC",
        "ALPHANUMERIC",
        "PERFORM",
        "MOVE",
        "DISPLAY",
        "ADD",
        "SUBTRACT",
        "MULTIPLY",
        "DIVIDE",
        "COMPUTE",
        "EVALUATE",
        "WHEN",
        "GO",
        "STOP",
        "RUN",
        "EXIT",
        "CONTINUE",
        "WORKING-STORAGE",
        "SECTION",
        "DIVISION",
        "PROCEDURE",
        "IDENTIFICATION",
        "PROGRAM-ID",
        "DATA",
        "ENVIRONMENT",
        "PIC",
        "PICTURE",
        "VALUE",
        "SPACES",
        "ZEROS",
        "ZEROES",
        "HIGH-VALUES",
        "LOW-VALUES",
        "ALL",
        "TRUE",
        "FALSE",
        "THRU",
        "THROUGH",
        "UNTIL",
        "VARYING",
        "WITH",
        "TEST",
        "BEFORE",
        "AFTER",
        "ALSO",
        "OTHER",
        "SIZE",
        "INTO",
        "GIVING",
        "REMAINDER",
        "ON",
        "OVERFLOW",
        "END-PERFORM",
        "END-EVALUATE",
        "IS",
        "ARE",
        "OF",
        "IN",
        "BY",
        "FROM",
        "ZERO",
        "SPACE",
        "SET",
        "INITIALIZE",
    }
)

# Figurative constant mapping for literal harvesting
_FIGURATIVE_LITERALS: dict[str, str | int] = {
    "SPACES": " ",
    "SPACE": " ",
    "ZEROS": 0,
    "ZERO": 0,
    "ZEROES": 0,
    "LOW-VALUES": "",
    "LOW-VALUE": "",
    "HIGH-VALUES": "\xff",
    "HIGH-VALUE": "\xff",
}


def harvest_conditions(mock_cbl_path: Path) -> dict[str, list]:
    """Harvest condition literals from the PROCEDURE DIVISION.

    Reads the .mock.cbl file, finds the PROCEDURE DIVISION, and scans
    IF statements and EVALUATE/WHEN blocks to extract literal values
    compared against variables.

    Args:
        mock_cbl_path: Path to the instrumented .mock.cbl file.

    Returns:
        Dict mapping variable names to lists of literal values found
        in conditions. Values may be strings or numeric types.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If PROCEDURE DIVISION is not found.
    """
    mock_cbl_path = Path(mock_cbl_path)
    if not mock_cbl_path.exists():
        raise FileNotFoundError(
            f"Mock CBL file not found: {mock_cbl_path}"
        )

    lines = mock_cbl_path.read_text(encoding="utf-8").splitlines()
    proc_start = _find_procedure_division(lines)
    proc_lines = lines[proc_start:]

    result: dict[str, list] = {}

    # Harvest from IF conditions
    _harvest_if_conditions(proc_lines, result)

    # Harvest from EVALUATE/WHEN blocks
    _harvest_evaluate_conditions(proc_lines, result)

    logger.info(
        "Harvested conditions for %d variables from %s",
        len(result),
        mock_cbl_path.name,
    )

    return result


def _find_procedure_division(lines: list[str]) -> int:
    """Find the 0-based line index of PROCEDURE DIVISION."""
    for idx, line in enumerate(lines):
        if re.search(r"PROCEDURE\s+DIVISION", line, re.IGNORECASE):
            return idx
    raise ValueError("PROCEDURE DIVISION not found in source")


def _harvest_if_conditions(
    lines: list[str], result: dict[str, list]
) -> None:
    """Extract literals from IF statements.

    Handles patterns like:
        IF WS-STATUS = '00'
        IF WS-STATUS = '00' OR '10'
        IF WS-AMOUNT > 1000
        IF WS-FLAG NOT = 'Y'
    """
    for line in lines:
        stripped = line.strip()

        # Skip comment lines
        if stripped.startswith("*"):
            continue

        upper = stripped.upper()

        # Match IF statements
        if not upper.startswith("IF "):
            continue

        condition = stripped[3:].strip()
        _harvest_from_condition(condition, result)


def _harvest_evaluate_conditions(
    lines: list[str], result: dict[str, list]
) -> None:
    """Extract literals from EVALUATE/WHEN blocks.

    Handles patterns like:
        EVALUATE WS-STATUS
            WHEN '00'
            WHEN '10'
            WHEN OTHER
    Also handles:
        EVALUATE TRUE
            WHEN WS-FLAG = 'Y'
    """
    current_subject: str | None = None

    for line in lines:
        stripped = line.strip()

        # Skip comment lines
        if stripped.startswith("*"):
            continue

        upper = stripped.upper()

        # Detect EVALUATE subject
        if upper.startswith("EVALUATE "):
            subject = stripped[9:].strip()
            subject_upper = subject.upper()
            if subject_upper == "TRUE" or subject_upper == "FALSE":
                current_subject = None  # EVALUATE TRUE uses conditions
            else:
                # Subject is a variable name
                current_subject = _clean_var_name(subject_upper)
                if current_subject in _KEYWORDS:
                    current_subject = None

        elif upper.startswith("END-EVALUATE"):
            current_subject = None

        elif upper.startswith("WHEN "):
            when_value = stripped[5:].strip()
            when_upper = when_value.upper()

            if when_upper == "OTHER" or when_upper == "OTHERS":
                continue

            if current_subject:
                # EVALUATE <variable> / WHEN <literal>
                literals = _extract_literals(when_value)
                if literals:
                    _add_literals(result, current_subject, literals)
            else:
                # EVALUATE TRUE / WHEN <condition>
                _harvest_from_condition(when_value, result)


def _harvest_from_condition(
    condition: str, result: dict[str, list]
) -> None:
    """Extract variable-literal pairs from a COBOL condition string.

    Splits the condition around comparison operators and extracts
    the variable name from the left side and literal values from
    the right side.
    """
    if not condition:
        return

    text = condition.strip()
    if text.upper().startswith("UNTIL "):
        text = text[6:].strip()

    # Split into segments around comparison operators
    parts = _CMP_RE.split(text)
    ops = _CMP_RE.findall(text)

    for idx, op in enumerate(ops):
        lhs_raw = parts[idx].strip() if idx < len(parts) else ""
        rhs_raw = parts[idx + 1].strip() if idx + 1 < len(parts) else ""

        if not lhs_raw or not rhs_raw:
            continue

        # Extract variable name from LHS (last identifier-looking token)
        lhs_tokens = re.findall(
            r"[A-Z][A-Z0-9-]*(?:\([^)]*\))?|'[^']*'|-?\d+\.?\d*",
            lhs_raw,
            re.IGNORECASE,
        )
        if not lhs_tokens:
            continue

        var_name = None
        for tok in reversed(lhs_tokens):
            tok_upper = tok.upper()
            if (
                tok_upper not in _KEYWORDS
                and tok_upper not in ("AND", "OR", "NOT")
                and tok_upper not in _FIGURATIVE_LITERALS
                and not tok.startswith("'")
                and not re.match(r"^-?\d+\.?\d*$", tok)
            ):
                var_name = _clean_var_name(tok_upper)
                break

        if not var_name or len(var_name) < 2:
            continue

        # Parse RHS for literal values (may contain OR-separated lists)
        literals = _extract_literals(rhs_raw)

        # For ordering comparisons, add boundary values
        op_upper = op.upper().strip()
        is_ordering = any(
            c in op_upper for c in (">", "<", "GREATER", "LESS")
        )

        if is_ordering:
            expanded: list = []
            for lit in literals:
                expanded.append(lit)
                if isinstance(lit, int):
                    expanded.extend([lit - 1, lit + 1])
            literals = expanded

        if literals:
            _add_literals(result, var_name, literals)


def _extract_literals(text: str) -> list:
    """Extract literal values from a COBOL expression fragment.

    Handles quoted strings, numeric literals, figurative constants,
    and OR-separated multi-value lists.
    """
    tokens = re.findall(
        r"'[^']*'|-?\d+\.?\d*|[A-Z][A-Z0-9-]*(?:\([^)]*\))?",
        text,
        re.IGNORECASE,
    )

    literals: list = []
    for tok in tokens:
        tok_upper = tok.upper()
        if tok_upper in ("AND", "OR", "NOT", "IS", "NUMERIC"):
            continue
        if tok_upper in _FIGURATIVE_LITERALS:
            literals.append(_FIGURATIVE_LITERALS[tok_upper])
        elif tok.startswith("'") and tok.endswith("'"):
            literals.append(tok[1:-1])  # Strip quotes
        elif re.match(r"^-?\d+$", tok):
            literals.append(int(tok))
        elif re.match(r"^-?\d+\.\d+$", tok):
            literals.append(float(tok))
        # else: variable reference -- skip

    return literals


def _clean_var_name(name: str) -> str:
    """Strip subscripts and trailing punctuation from a variable name."""
    paren = name.find("(")
    if paren >= 0:
        name = name[:paren]
    return name.rstrip(".,;:'")


def _add_literals(
    result: dict[str, list],
    var_name: str,
    literals: list,
) -> None:
    """Add literal values to the result dict, deduplicating."""
    if var_name not in result:
        result[var_name] = []
    existing = set(result[var_name])
    for lit in literals:
        if lit not in existing:
            result[var_name].append(lit)
            existing.add(lit)
