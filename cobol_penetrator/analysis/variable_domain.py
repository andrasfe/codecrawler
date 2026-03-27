"""Variable domain model for COBOL field analysis.

Provides the VariableDomain dataclass and functions to build domain
objects from parsed field definitions, including semantic type inference,
numeric range computation, and variable classification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .data_division_parser import FieldDefinition


@dataclass
class VariableDomain:
    """Unified domain model for a single COBOL variable.

    Combines type information from PIC clauses, semantic inference from
    naming conventions, value constraints from 88-level conditions, and
    runtime classification.

    Attributes:
        name: The COBOL field name (uppercase, hyphenated).
        data_type: Type category: alpha, numeric, packed, comp, flag, unknown.
        max_length: Maximum characters (PIC X) or digits (PIC 9).
        precision: Decimal places from PIC V99.
        signed: Whether the field carries a sign (PIC S...).
        min_value: Computed minimum value for numeric types, or None.
        max_value: Computed maximum value for numeric types, or None.
        condition_literals: Literal values harvested from IF/EVALUATE.
        valid_88_values: Mapping of 88-level condition name to its value.
        classification: Variable role: input, internal, status, flag.
        semantic_type: Inferred meaning: date, time, amount, etc.
        set_by_stub: The stub operation name that sets this variable.
        default_value: The default VALUE from the data definition.
    """

    name: str
    data_type: str = "unknown"
    max_length: int = 10
    precision: int = 0
    signed: bool = False
    min_value: int | float | None = None
    max_value: int | float | None = None
    condition_literals: list = field(default_factory=list)
    valid_88_values: dict[str, str] = field(default_factory=dict)
    classification: str = "internal"
    semantic_type: str = "generic"
    set_by_stub: str | None = None
    default_value: str | None = None


# ---------------------------------------------------------------------------
# Semantic type inference from naming patterns
# ---------------------------------------------------------------------------

_SEMANTIC_PATTERNS: list[tuple[list[str], str]] = [
    (["DATE", "DT", "YYDDD", "YYMMDD", "YYYYMMDD", "MMDDYY"], "date"),
    (["TIME", "TM", "HHMMSS"], "time"),
    (["AMT", "AMOUNT", "BAL", "BALANCE", "TOTAL"], "amount"),
    (["CNT", "COUNT", "FREQ", "NBR"], "counter"),
    (["KEY", "NUM", "ID", "ACCT"], "identifier"),
    (["SQLCODE", "SQLSTATE"], "status_sql"),
    (["EIBRESP", "EIBAID"], "status_cics"),
]


def _infer_semantic_type(name: str, classification: str) -> str:
    """Infer semantic type from variable name and classification.

    Uses pattern matching against known naming conventions to determine
    the semantic purpose of a COBOL variable.

    Args:
        name: The COBOL variable name (uppercase).
        classification: The variable's classification (status, flag, etc.).

    Returns:
        A semantic type string such as "date", "amount", "status_file", etc.
    """
    upper = name.upper()

    # Explicit status patterns
    if (
        upper.endswith("-STATUS")
        or upper.startswith("FS-")
        or upper.startswith("FILE-STATUS")
    ):
        return "status_file"
    if (
        "FLAG" in upper
        or "FLG" in upper
        or upper.endswith("-ON")
        or upper.endswith("-OFF")
    ):
        return "flag_bool"

    # Check naming patterns
    parts = set(upper.replace("_", "-").split("-"))
    for keywords, sem_type in _SEMANTIC_PATTERNS:
        for kw in keywords:
            if kw in parts or kw in upper:
                return sem_type

    # PCB status fields
    if "PCB-STATUS" in upper or upper.startswith("STATUS-CODE-"):
        return "status_file"

    if classification == "status":
        return "status_file"
    if classification == "flag":
        return "flag_bool"

    return "generic"


# ---------------------------------------------------------------------------
# Range computation from PIC clauses
# ---------------------------------------------------------------------------


def _compute_range(
    data_type: str,
    max_length: int,
    precision: int,
    signed: bool,
) -> tuple[int | float | None, int | float | None]:
    """Compute min/max value from PIC clause parameters.

    For numeric types, calculates the full range of representable values
    based on digit count, decimal precision, and signedness.

    Args:
        data_type: The pic_type (alpha, numeric, packed, comp, etc.).
        max_length: Number of integer digit positions.
        precision: Number of decimal digit positions.
        signed: Whether the field is signed.

    Returns:
        A (min_value, max_value) tuple, or (None, None) for non-numeric.
    """
    if data_type in ("alpha", "group", "unknown"):
        return None, None

    int_max = 10**max_length - 1
    if precision > 0:
        divisor = 10**precision
        fmax = int_max + (10**precision - 1) / divisor
        if signed:
            return -fmax, fmax
        return 0.0, fmax
    else:
        if signed:
            return -int_max, int_max
        return 0, int_max


# ---------------------------------------------------------------------------
# Variable classification from naming patterns
# ---------------------------------------------------------------------------

_STATUS_VARS = frozenset(
    {
        "SQLCODE",
        "SQLSTATE",
        "EIBRESP",
        "EIBRESP2",
        "EIBAID",
        "EIBCALEN",
        "EIBFN",
        "EIBRCODE",
        "EIBTRNID",
        "DIBSTAT",
    }
)


def _classify_variable(name: str, has_88_values: bool) -> str:
    """Classify a variable based on naming patterns and 88-level presence.

    Args:
        name: The COBOL variable name (uppercase).
        has_88_values: Whether the field has 88-level conditions attached.

    Returns:
        Classification string: "status", "flag", "input", or "internal".
    """
    upper = name.upper()

    # Status codes from external calls
    if upper in _STATUS_VARS or upper.endswith("-STATUS"):
        return "status"

    # PCB status fields
    if "PCB-STATUS" in upper or upper.startswith("STATUS-CODE-"):
        return "status"

    # File status variables
    if upper.startswith("FILE-STATUS-") or (
        upper.startswith("FS-") and len(upper) > 3
    ):
        return "status"

    # Return code fields
    if upper.endswith("-RETURN-CODE") or upper.endswith("-RESP-CD"):
        return "status"

    # Boolean flags (naming patterns and 88-level presence)
    if (
        upper.endswith("-ON")
        or upper.endswith("-OFF")
        or upper.endswith("-ERROR")
        or upper.endswith("-ERRORS")
        or upper.startswith("END-")
        or upper.startswith("NO-MORE-")
        or upper.endswith("-SUCCESS")
        or upper.endswith("-FAILED")
        or "FLG" in upper
        or "FLAG" in upper
        or upper.startswith("DEBUG-")
        or upper.startswith("QUALIFIED-")
    ):
        return "flag"

    # Fields with many 88-level values are typically flags or status
    if has_88_values:
        return "flag"

    return "internal"


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------


def build_domain(field_def: FieldDefinition) -> VariableDomain:
    """Construct a VariableDomain from a parsed FieldDefinition.

    Combines PIC clause information, semantic inference, range
    computation, and classification into a unified domain object.

    Args:
        field_def: A parsed FieldDefinition from the data division parser.

    Returns:
        A fully populated VariableDomain instance.
    """
    has_88 = bool(field_def.values_88)
    classification = _classify_variable(field_def.name, has_88)
    semantic_type = _infer_semantic_type(field_def.name, classification)

    # Map pic_type for domain; flag type gets "flag" data_type if classified
    data_type = field_def.pic_type
    if data_type == "group":
        data_type = "unknown"

    min_val, max_val = _compute_range(
        data_type,
        field_def.length,
        field_def.precision,
        field_def.signed,
    )

    # Clean default value
    default_value = field_def.value_clause
    if default_value:
        # Strip surrounding quotes from literal values
        stripped = default_value.strip()
        if stripped.startswith("'") and stripped.endswith("'"):
            default_value = stripped[1:-1]
        elif stripped.upper() in ("SPACES", "SPACE"):
            default_value = " "
        elif stripped.upper() in ("ZEROS", "ZERO", "ZEROES"):
            default_value = "0"

    return VariableDomain(
        name=field_def.name,
        data_type=data_type,
        max_length=field_def.length,
        precision=field_def.precision,
        signed=field_def.signed,
        min_value=min_val,
        max_value=max_val,
        condition_literals=[],
        valid_88_values=dict(field_def.values_88),
        classification=classification,
        semantic_type=semantic_type,
        set_by_stub=None,
        default_value=default_value,
    )
