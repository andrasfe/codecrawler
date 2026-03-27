"""Parse WORKING-STORAGE SECTION from instrumented .mock.cbl files.

Extracts field definitions including level numbers, PIC clauses, VALUE
clauses, 88-level condition names, and parent-child relationships.
Filters out specter instrumentation infrastructure fields.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from .pic_parser import parse_pic

logger = logging.getLogger(__name__)

# Specter infrastructure prefixes/names to filter out
_SPECTER_FILTER_PREFIXES = (
    "MOCK-RECORD",
    "MOCK-OP-KEY",
    "MOCK-ALPHA-STATUS",
    "MOCK-NUM-STATUS",
    "MOCK-FILLER",
    "MOCK-FILE-STATUS",
    "MOCK-FILE-RECORD",
    "MOCK-FILE",
    "SPECTER-",
)

# Regex to detect a COBOL data definition line.
# Matches: optional spaces, level number, field name (or FILLER), then rest.
_RE_DATA_LINE = re.compile(
    r"^\s{6,7}\s*(\d{2})\s+"
    r"(FILLER|[A-Z][A-Z0-9-]*)"
    r"(.*?)\.\s*$",
    re.IGNORECASE,
)

# Regex for PIC clause extraction
_RE_PIC = re.compile(
    r"\bPIC(?:TURE)?\s+(\S+(?:\s*\(\d+\))?)",
    re.IGNORECASE,
)

# Regex for USAGE clause extraction
_RE_USAGE = re.compile(
    r"\bUSAGE\s+(?:IS\s+)?(COMP(?:-3)?|BINARY|PACKED-DECIMAL|DISPLAY)",
    re.IGNORECASE,
)

# Regex for standalone COMP/COMP-3/BINARY at end (without USAGE keyword)
_RE_USAGE_SHORTHAND = re.compile(
    r"\b(COMP-3|COMP|BINARY|PACKED-DECIMAL)\b(?!\s*[-'])",
    re.IGNORECASE,
)

# Regex for VALUE clause extraction
_RE_VALUE = re.compile(
    r"\bVALUE\s+(?:IS\s+)?(.+?)(?:\.|$)",
    re.IGNORECASE,
)

# Regex for REDEFINES clause
_RE_REDEFINES = re.compile(r"\bREDEFINES\b", re.IGNORECASE)

# Regex for OCCURS clause
_RE_OCCURS = re.compile(r"\bOCCURS\b", re.IGNORECASE)

# 88-level value extraction: VALUE 'xx' or VALUE 'xx', 'yy'
_RE_88_VALUE = re.compile(
    r"\bVALUE\s+(?:IS\s+|ARE\s+)?(.+?)(?:\.|$)",
    re.IGNORECASE,
)


@dataclass
class FieldDefinition:
    """A single field definition extracted from WORKING-STORAGE.

    Attributes:
        level: COBOL level number (01, 05, 10, 15, 88).
        name: Field name (e.g. WS-STATUS).
        pic_clause: Raw PIC clause string or None for group items.
        pic_type: Parsed type: alpha, numeric, packed, comp, group.
        length: Field length in characters or digits.
        precision: Decimal precision (digits after V).
        signed: Whether the field has a sign (PIC S...).
        usage: USAGE clause value (COMP, COMP-3, etc.).
        value_clause: Default VALUE clause string or None.
        parent_name: Name of the parent group field, or None for 01-level.
        is_filler: True if the field is a FILLER item.
        values_88: Mapping of 88-level condition names to their values.
    """

    level: int
    name: str
    pic_clause: str | None
    pic_type: str
    length: int
    precision: int
    signed: bool
    usage: str
    value_clause: str | None
    parent_name: str | None
    is_filler: bool
    values_88: dict[str, str] = field(default_factory=dict)


def parse_working_storage(mock_cbl_path: Path) -> list[FieldDefinition]:
    """Parse WORKING-STORAGE SECTION from a .mock.cbl file.

    Reads lines before PROCEDURE DIVISION, locates WORKING-STORAGE
    SECTION, and extracts all field definitions. Specter infrastructure
    fields are filtered out. 88-level items are attached to their
    parent field. REDEFINES groups are skipped.

    Args:
        mock_cbl_path: Path to the instrumented .mock.cbl file.

    Returns:
        List of FieldDefinition objects for program-defined fields.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If WORKING-STORAGE SECTION is not found.
    """
    mock_cbl_path = Path(mock_cbl_path)
    if not mock_cbl_path.exists():
        raise FileNotFoundError(
            f"Mock CBL file not found: {mock_cbl_path}"
        )

    lines = mock_cbl_path.read_text(encoding="utf-8").splitlines()

    # Find WORKING-STORAGE SECTION and PROCEDURE DIVISION boundaries
    ws_start = _find_working_storage(lines)
    proc_start = _find_procedure_division(lines)

    logger.debug(
        "WORKING-STORAGE at line %d, PROCEDURE DIVISION at line %d",
        ws_start + 1,
        proc_start + 1,
    )

    # Parse field definitions between WORKING-STORAGE and PROCEDURE DIVISION
    raw_fields = _parse_fields(lines, ws_start + 1, proc_start)

    # Filter out specter infrastructure
    filtered = _filter_specter_fields(raw_fields)

    # Attach 88-level items to their parents
    result = _attach_88_levels(filtered)

    logger.info(
        "Parsed %d fields from WORKING-STORAGE in %s",
        len(result),
        mock_cbl_path.name,
    )

    return result


def _find_working_storage(lines: list[str]) -> int:
    """Find the 0-based line index of WORKING-STORAGE SECTION."""
    for idx, line in enumerate(lines):
        if re.search(r"WORKING-STORAGE\s+SECTION", line, re.IGNORECASE):
            return idx
    raise ValueError("WORKING-STORAGE SECTION not found in source")


def _find_procedure_division(lines: list[str]) -> int:
    """Find the 0-based line index of PROCEDURE DIVISION."""
    for idx, line in enumerate(lines):
        if re.search(r"PROCEDURE\s+DIVISION", line, re.IGNORECASE):
            return idx
    raise ValueError("PROCEDURE DIVISION not found in source")


def _is_specter_field(name: str) -> bool:
    """Check if a field name belongs to specter infrastructure."""
    upper = name.upper()
    for prefix in _SPECTER_FILTER_PREFIXES:
        if upper.startswith(prefix):
            return True
    return False


def _extract_usage(rest: str) -> str:
    """Extract USAGE clause from the rest of a data definition line."""
    m = _RE_USAGE.search(rest)
    if m:
        return m.group(1).upper()
    m = _RE_USAGE_SHORTHAND.search(rest)
    if m:
        # Make sure it's not part of a PIC clause
        pic_m = _RE_PIC.search(rest)
        if pic_m:
            pic_end = pic_m.end()
            if m.start() < pic_end:
                # The COMP is inside the PIC clause, look for another
                m2 = _RE_USAGE_SHORTHAND.search(rest, pic_end)
                if m2:
                    return m2.group(1).upper()
                return ""
        return m.group(1).upper()
    return ""


def _extract_value(rest: str) -> str | None:
    """Extract VALUE clause from the rest of a data definition line."""
    m = _RE_VALUE.search(rest)
    if m:
        val = m.group(1).strip().rstrip(".")
        return val if val else None
    return None


def _parse_fields(
    lines: list[str], start: int, end: int
) -> list[FieldDefinition]:
    """Parse data definition lines into raw FieldDefinition objects."""
    fields: list[FieldDefinition] = []
    # Track parent stack: (level, name) pairs for nesting
    parent_stack: list[tuple[int, str]] = []
    # Track if we're inside a REDEFINES group to skip
    skip_redefines_level: int | None = None

    for idx in range(start, end):
        line = lines[idx]

        # Skip comment lines (column 7 = *)
        if len(line) > 6 and line[6] == "*":
            continue

        m = _RE_DATA_LINE.match(line)
        if not m:
            continue

        level = int(m.group(1))
        name = m.group(2).upper()
        rest = m.group(3)

        # Handle REDEFINES: skip the redefined group and its children
        if _RE_REDEFINES.search(rest) and level != 88:
            if skip_redefines_level is None:
                skip_redefines_level = level
                continue
        if skip_redefines_level is not None:
            if level <= skip_redefines_level and level != 88:
                # We've exited the REDEFINES group
                skip_redefines_level = None
            else:
                continue

        is_filler = name == "FILLER"

        # Extract PIC clause
        pic_m = _RE_PIC.search(rest)
        pic_clause = pic_m.group(1).upper() if pic_m else None

        # Extract USAGE
        usage = _extract_usage(rest)

        # Handle 88-level items
        if level == 88:
            val_m = _RE_88_VALUE.search(rest)
            value_str = val_m.group(1).strip().rstrip(".") if val_m else ""
            # 88-level has no PIC; store raw for later attachment
            fields.append(
                FieldDefinition(
                    level=88,
                    name=name,
                    pic_clause=None,
                    pic_type="flag",
                    length=0,
                    precision=0,
                    signed=False,
                    usage="",
                    value_clause=value_str,
                    parent_name=_current_parent(parent_stack),
                    is_filler=False,
                )
            )
            continue

        # Parse PIC clause for type info
        if pic_clause:
            pic_type, length, precision, signed = parse_pic(
                pic_clause, usage
            )
        else:
            # Group item (no PIC clause)
            pic_type = "group"
            length = 0
            precision = 0
            signed = False

        # Extract VALUE clause
        value_clause = _extract_value(rest)

        # Update parent stack
        _update_parent_stack(parent_stack, level, name)
        parent_name = _parent_for_level(parent_stack, level)

        fields.append(
            FieldDefinition(
                level=level,
                name=name,
                pic_clause=pic_clause,
                pic_type=pic_type,
                length=length,
                precision=precision,
                signed=signed,
                usage=usage,
                value_clause=value_clause,
                parent_name=parent_name,
                is_filler=is_filler,
            )
        )

    return fields


def _current_parent(parent_stack: list[tuple[int, str]]) -> str | None:
    """Return the current parent name from the stack."""
    return parent_stack[-1][1] if parent_stack else None


def _parent_for_level(
    parent_stack: list[tuple[int, str]], level: int
) -> str | None:
    """Find the parent name for a given level number."""
    # Walk backwards through the stack to find the nearest lower level
    for plevel, pname in reversed(parent_stack):
        if plevel < level:
            return pname
    return None


def _update_parent_stack(
    parent_stack: list[tuple[int, str]], level: int, name: str
) -> None:
    """Update the parent tracking stack when a new field is encountered."""
    # Pop entries at the same or deeper level
    while parent_stack and parent_stack[-1][0] >= level:
        parent_stack.pop()
    parent_stack.append((level, name))


def _filter_specter_fields(
    fields: list[FieldDefinition],
) -> list[FieldDefinition]:
    """Remove specter infrastructure fields and their children."""
    filtered: list[FieldDefinition] = []
    skip_parent: str | None = None

    for fld in fields:
        # Skip 88-level children of filtered parents
        if fld.level == 88 and fld.parent_name and _is_specter_field(
            fld.parent_name
        ):
            continue

        # Skip specter infrastructure fields
        if _is_specter_field(fld.name):
            if fld.pic_type == "group":
                skip_parent = fld.name
            continue

        # Skip children of specter group fields
        if skip_parent and fld.parent_name:
            if fld.parent_name.upper() == skip_parent.upper():
                continue

        # Reset skip_parent when we encounter a new 01-level
        if fld.level == 1:
            skip_parent = None

        filtered.append(fld)

    return filtered


def _attach_88_levels(
    fields: list[FieldDefinition],
) -> list[FieldDefinition]:
    """Attach 88-level conditions to their parent fields.

    Removes 88-level items from the list and stores their name/value
    pairs in the parent's values_88 dict.
    """
    result: list[FieldDefinition] = []
    # Index the non-88 fields by name for quick lookup
    parent_map: dict[str, FieldDefinition] = {}

    for fld in fields:
        if fld.level != 88:
            result.append(fld)
            parent_map[fld.name] = fld

    # Second pass: attach 88-level items
    for fld in fields:
        if fld.level == 88 and fld.parent_name:
            parent = parent_map.get(fld.parent_name)
            if parent is not None:
                parent.values_88[fld.name] = fld.value_clause or ""

    return result
