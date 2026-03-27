"""Static fault code tables for COBOL stub operations.

Maps semantic types (file status, SQL return code, CICS response, etc.)
to their known status values. Used by the heuristic walker to generate
fault sweeps and by the value generator for semantic-aware generation.

The tables are derived from IBM mainframe documentation and represent
the most commonly encountered status/return code values in production
COBOL programs.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Fault code tables
# ---------------------------------------------------------------------------

FILE_STATUS_CODES: list[str] = [
    "00", "10", "23", "35", "39", "41", "46", "47",
]
"""Common FILE STATUS values.

00 = success, 10 = end-of-file, 23 = key not found,
35 = file not found, 39 = attribute conflict,
41 = file already open, 46 = no valid next record,
47 = READ on file not opened INPUT/IO.
"""

SQL_STATUS_CODES: list[int] = [0, 100, -803, -805, -811, -904]
"""Common SQLCODE values.

0 = success, 100 = not found, -803 = duplicate key,
-805 = program not in plan, -811 = multiple rows,
-904 = resource unavailable.
"""

CICS_STATUS_CODES: list[int] = [0, 12, 13, 16, 22, 26, 27, 70, 84]
"""Common EIBRESP values.

0 = NORMAL, 12 = FILENOTFOUND, 13 = NOTFND,
16 = INVREQ, 22 = LENGERR, 26 = ITEMERR,
27 = PGMIDERR, 70 = TERMERR, 84 = DISABLED.
"""

DLI_STATUS_CODES: list[str] = ["  ", "II", "GE", "GB", "GG", "AI"]
"""Common IMS/DL-I status codes.

'  ' = success, II = segment inserted,
GE = segment not found, GB = end of database,
GG = unqualified GN, AI = insert failed.
"""

RETURN_CODES: list[int] = [0, 4, 8, 12, 16]
"""Standard COBOL RETURN-CODE values.

0 = success, 4 = warning, 8 = error,
12 = severe error, 16 = critical.
"""

EIBAID_VALUES: list[str] = [
    "DFHENTER", "DFHPF3", "DFHPF7", "DFHPF8", "DFHCLEAR",
]
"""Common EIBAID (Attention Identifier) values for CICS.

DFHENTER = Enter key, DFHPF3 = PF3 (exit),
DFHPF7 = PF7 (page up), DFHPF8 = PF8 (page down),
DFHCLEAR = Clear key.
"""

# ---------------------------------------------------------------------------
# Lookup tables mapping semantic_type -> fault table
# ---------------------------------------------------------------------------

_FAULT_TABLE: dict[str, list] = {
    "status_file": FILE_STATUS_CODES,
    "status_sql": SQL_STATUS_CODES,
    "status_cics": CICS_STATUS_CODES,
    "status_dli": DLI_STATUS_CODES,
    "return_code": RETURN_CODES,
    "eibaid": EIBAID_VALUES,
}

_SUCCESS_VALUE: dict[str, str | int] = {
    "status_file": "00",
    "status_sql": 0,
    "status_cics": 0,
    "status_dli": "  ",
    "return_code": 0,
    "eibaid": "DFHENTER",
}


def fault_values_for(semantic_type: str) -> list:
    """Return the fault table for a given semantic type.

    Args:
        semantic_type: One of "status_file", "status_sql", "status_cics",
            "status_dli", "return_code", "eibaid".

    Returns:
        A list of known status/fault values for the type, or an empty
        list if the semantic type is not recognized.
    """
    return list(_FAULT_TABLE.get(semantic_type, []))


def success_value_for(semantic_type: str) -> str | int:
    """Return the canonical success value for a given semantic type.

    Args:
        semantic_type: One of "status_file", "status_sql", "status_cics",
            "status_dli", "return_code", "eibaid".

    Returns:
        The success value (e.g. ``"00"`` for file status, ``0`` for SQL),
        or ``""`` if the semantic type is not recognized.
    """
    return _SUCCESS_VALUE.get(semantic_type, "")
