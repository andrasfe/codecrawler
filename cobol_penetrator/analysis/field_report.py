"""Unified field report builder for COBOL data type analysis.

Combines parsed field definitions, variable domains, condition literals,
and stub relationships into a single FieldReport that can be consumed
by penetration agents to generate better test parameters.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..mock_reader import ProgramStructure
from .condition_harvester import harvest_conditions
from .data_division_parser import parse_working_storage
from .variable_domain import VariableDomain, build_domain

logger = logging.getLogger(__name__)

# Regex to find SPECTER-MOCK operations and the variable they set.
# The operation key is a sequence of word characters and hyphens,
# stopping before quotes, periods, or other punctuation.
_RE_MOCK_OP = re.compile(
    r"SPECTER-MOCK:([A-Za-z0-9][-A-Za-z0-9]*)", re.IGNORECASE
)
_RE_MOVE_FROM_MOCK = re.compile(
    r"MOVE\s+MOCK-(?:ALPHA-STATUS|NUM-STATUS)\s+TO\s+([A-Z][A-Z0-9-]*)",
    re.IGNORECASE,
)


@dataclass
class FieldReport:
    """Complete field analysis report for an instrumented COBOL program.

    Attributes:
        fields: Mapping of field name to its VariableDomain.
        condition_hints: Mapping of field name to literal values from
            IF/EVALUATE conditions in the PROCEDURE DIVISION.
        stub_variables: Mapping of variable name to the stub operation
            that sets it (e.g. WS-STATUS -> READ-ACCOUNT).
        stub_operations: List of all stub operation keys found in the
            program.
    """

    fields: dict[str, VariableDomain]
    condition_hints: dict[str, list]
    stub_variables: dict[str, str]
    stub_operations: list[str]


def build_field_report(
    mock_cbl_path: Path,
    structure: ProgramStructure,
) -> FieldReport:
    """Build a complete field report from a .mock.cbl and program structure.

    Orchestrates the full analysis pipeline:
    1. Parse WORKING-STORAGE to get field definitions
    2. Build VariableDomain for each field
    3. Harvest condition literals from PROCEDURE DIVISION
    4. Map stub operations to the variables they set
    5. Merge condition hints into domain objects

    Args:
        mock_cbl_path: Path to the instrumented .mock.cbl file.
        structure: The ProgramStructure from mock_reader.parse_mock_structure.

    Returns:
        A fully populated FieldReport.
    """
    mock_cbl_path = Path(mock_cbl_path)

    # Step 1: Parse WORKING-STORAGE field definitions
    field_defs = parse_working_storage(mock_cbl_path)

    # Step 2: Build domain objects
    fields: dict[str, VariableDomain] = {}
    for fdef in field_defs:
        if fdef.is_filler:
            continue
        domain = build_domain(fdef)
        fields[domain.name] = domain

    # Step 3: Harvest condition literals from PROCEDURE DIVISION
    condition_hints = harvest_conditions(mock_cbl_path)

    # Step 4: Merge condition hints into domain objects
    for var_name, literals in condition_hints.items():
        if var_name in fields:
            existing = set(fields[var_name].condition_literals)
            for lit in literals:
                if lit not in existing:
                    fields[var_name].condition_literals.append(lit)
                    existing.add(lit)

    # Step 5: Map stub operations to variables
    stub_variables, stub_operations = _map_stubs_to_variables(
        mock_cbl_path
    )

    # Update domain objects with stub relationships
    for var_name, stub_op in stub_variables.items():
        if var_name in fields:
            fields[var_name].set_by_stub = stub_op

    logger.info(
        "Built field report: %d fields, %d condition hints, %d stubs",
        len(fields),
        len(condition_hints),
        len(stub_operations),
    )

    return FieldReport(
        fields=fields,
        condition_hints=condition_hints,
        stub_variables=stub_variables,
        stub_operations=stub_operations,
    )


def _map_stubs_to_variables(
    mock_cbl_path: Path,
) -> tuple[dict[str, str], list[str]]:
    """Scan PROCEDURE DIVISION for stub operations and the variables they set.

    Looks for patterns like:
        DISPLAY 'SPECTER-MOCK:READ-ACCOUNT'
        READ MOCK-FILE INTO MOCK-RECORD
        ...
        MOVE MOCK-ALPHA-STATUS TO WS-STATUS

    Args:
        mock_cbl_path: Path to the .mock.cbl file.

    Returns:
        A tuple of (stub_variables, stub_operations) where:
        - stub_variables maps variable name to stub op key
        - stub_operations is the list of all unique stub op keys
    """
    lines = mock_cbl_path.read_text(encoding="utf-8").splitlines()

    # Find PROCEDURE DIVISION
    proc_start = 0
    for idx, line in enumerate(lines):
        if re.search(r"PROCEDURE\s+DIVISION", line, re.IGNORECASE):
            proc_start = idx
            break

    stub_variables: dict[str, str] = {}
    stub_operations: list[str] = []
    current_stub: str | None = None

    for idx in range(proc_start, len(lines)):
        line = lines[idx]
        stripped = line.strip()

        # Skip comments
        if len(line) > 6 and line[6] == "*":
            continue

        # Detect SPECTER-MOCK operation
        m = _RE_MOCK_OP.search(stripped)
        if m:
            current_stub = m.group(1)
            if current_stub not in stub_operations:
                stub_operations.append(current_stub)
            continue

        # If we're tracking a stub, look for MOVE from mock status
        if current_stub:
            m = _RE_MOVE_FROM_MOCK.search(stripped)
            if m:
                var_name = m.group(1).upper()
                stub_variables[var_name] = current_stub

            # Reset stub tracking at paragraph boundary or next stub
            upper = stripped.upper()
            if (
                upper.startswith("END-IF")
                or upper.startswith("END-EVALUATE")
                or (
                    len(stripped) > 0
                    and not stripped.startswith(" ")
                    and stripped.endswith(".")
                    and "MOCK" not in upper
                    and "MOVE" not in upper
                    and "READ" not in upper
                    and "AT" not in upper
                )
            ):
                current_stub = None

    return stub_variables, stub_operations
