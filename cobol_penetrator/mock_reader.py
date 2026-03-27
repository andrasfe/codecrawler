"""Parse .mock.cbl for paragraph/branch/call structure.

This module reads an instrumented COBOL source file (.mock.cbl) produced by
specter and extracts the structural information needed by penetration agents:
paragraphs, branch probes, PERFORM call relationships, and IF-condition text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for parsing instrumented COBOL
# ---------------------------------------------------------------------------

# Paragraph header: identifier in Area A (columns 8-11), ending with period.
# COBOL convention: 6-7 leading spaces, then the name starting at column 8.
_RE_PARAGRAPH = re.compile(r"^\s{6,7}([A-Z0-9][-A-Z0-9]*)\.\s*$")

# Branch probe inserted by specter: DISPLAY "@@B:<id>:<direction>"
_RE_BRANCH_PROBE = re.compile(r"@@B:(\d+):(T|F|W1|WO)")

# PERFORM <paragraph-name>
_RE_PERFORM = re.compile(r"PERFORM\s+([A-Z0-9][-A-Z0-9]*)")

# Variable names inside conditions (uppercase identifiers with optional hyphens).
_RE_VARIABLE = re.compile(r"[A-Z][-A-Z0-9]*")

# PROCEDURE DIVISION marker
_RE_PROCEDURE_DIV = re.compile(r"PROCEDURE\s+DIVISION", re.IGNORECASE)

# Lines that are COBOL division / section headers (not paragraphs)
_RE_DIVISION_OR_SECTION = re.compile(
    r"^\s{6,7}(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION",
    re.IGNORECASE,
)
_RE_SECTION_HEADER = re.compile(
    r"^\s{6,7}[A-Z][-A-Z0-9]*\s+SECTION\s*\.", re.IGNORECASE
)

# COBOL reserved words that should NOT be treated as variable names when
# extracting condition variables from IF statements.
_COBOL_KEYWORDS: frozenset[str] = frozenset({
    "IF", "ELSE", "END-IF", "THEN", "NOT", "AND", "OR",
    "EQUAL", "EQUALS", "GREATER", "LESS", "THAN", "TO",
    "NUMERIC", "ALPHABETIC", "ALPHANUMERIC",
    "PERFORM", "MOVE", "DISPLAY", "ADD", "SUBTRACT",
    "MULTIPLY", "DIVIDE", "COMPUTE", "EVALUATE", "WHEN",
    "GO", "STOP", "RUN", "EXIT", "CONTINUE",
    "WORKING-STORAGE", "SECTION", "DIVISION", "PROCEDURE",
    "IDENTIFICATION", "PROGRAM-ID", "DATA", "ENVIRONMENT",
    "PIC", "PICTURE", "VALUE", "SPACES", "ZEROS", "ZEROES",
    "HIGH-VALUES", "LOW-VALUES", "ALL", "TRUE", "FALSE",
    "THRU", "THROUGH", "UNTIL", "VARYING", "WITH", "TEST",
    "BEFORE", "AFTER", "ALSO", "OTHER", "SIZE", "INTO",
    "GIVING", "REMAINDER", "ON", "OVERFLOW", "END-PERFORM",
    "END-EVALUATE", "END-COMPUTE", "END-ADD", "END-SUBTRACT",
    "END-MULTIPLY", "END-DIVIDE", "END-READ", "END-WRITE",
    "END-CALL", "END-STRING", "END-UNSTRING", "END-SEARCH",
    "CALL", "STRING", "UNSTRING", "SEARCH", "READ", "WRITE",
    "OPEN", "CLOSE", "DELETE", "REWRITE", "START", "RETURN",
    "ACCEPT", "SET", "INITIALIZE", "INSPECT", "REPLACING",
    "TALLYING", "LEADING", "TRAILING", "FIRST", "INITIAL",
    "REFERENCE", "CONTENT", "LENGTH", "FUNCTION", "IS", "ARE",
    "OF", "IN", "BY", "FROM", "ZERO", "SPACE",
})


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParagraphInfo:
    """Metadata for a single COBOL paragraph in the instrumented source."""

    name: str
    line_start: int
    line_end: int
    source_code: str
    branches: list[str] = field(default_factory=list)
    performs: list[str] = field(default_factory=list)


@dataclass
class BranchInfo:
    """Metadata for a single branch probe found in the instrumented source."""

    id: str
    paragraph: str
    condition_text: str = ""
    condition_vars: list[str] = field(default_factory=list)
    directions: list[str] = field(default_factory=list)


@dataclass
class ProgramStructure:
    """Complete structural representation of a parsed .mock.cbl file."""

    entry_paragraph: str
    paragraphs: dict[str, ParagraphInfo]
    branches: dict[str, BranchInfo]
    call_graph: dict[str, list[str]]

    def branches_in(self, paragraph: str) -> list[str]:
        """Return branch IDs belonging to the given paragraph.

        Args:
            paragraph: The paragraph name to query.

        Returns:
            List of branch ID strings found in that paragraph.

        Raises:
            KeyError: If the paragraph is not in the structure.
        """
        if paragraph not in self.paragraphs:
            raise KeyError(f"Unknown paragraph: {paragraph!r}")
        return list(self.paragraphs[paragraph].branches)

    def branch_condition(self, branch_id: str) -> str:
        """Return the condition text associated with a branch probe.

        Args:
            branch_id: The numeric branch ID as a string (e.g. "1").

        Returns:
            The extracted condition text, or empty string if unknown.

        Raises:
            KeyError: If the branch ID is not in the structure.
        """
        if branch_id not in self.branches:
            raise KeyError(f"Unknown branch ID: {branch_id!r}")
        return self.branches[branch_id].condition_text

    def get_paragraph_code(self, paragraph: str) -> str:
        """Return the raw source code of a paragraph.

        Args:
            paragraph: The paragraph name to query.

        Returns:
            The source lines for that paragraph joined as a single string.

        Raises:
            KeyError: If the paragraph is not in the structure.
        """
        if paragraph not in self.paragraphs:
            raise KeyError(f"Unknown paragraph: {paragraph!r}")
        return self.paragraphs[paragraph].source_code


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _find_procedure_division(lines: list[str]) -> int:
    """Return the 0-based line index of the PROCEDURE DIVISION header.

    Raises:
        ValueError: If PROCEDURE DIVISION is not found.
    """
    for idx, line in enumerate(lines):
        if _RE_PROCEDURE_DIV.search(line):
            return idx
    raise ValueError("PROCEDURE DIVISION not found in source")


def _is_paragraph_header(line: str) -> str | None:
    """If *line* is a paragraph header, return the paragraph name; else None.

    Filters out COBOL division headers, section headers, and lines that
    look like paragraph headers but are actually reserved constructs.
    """
    if _RE_DIVISION_OR_SECTION.match(line):
        return None
    if _RE_SECTION_HEADER.match(line):
        return None
    m = _RE_PARAGRAPH.match(line)
    if m:
        name = m.group(1)
        # Reject names that are pure COBOL keywords
        if name in _COBOL_KEYWORDS:
            return None
        return name
    return None


def _extract_condition_text(lines: list[str], probe_line_idx: int) -> str:
    """Walk backwards from a branch probe to find the governing IF condition.

    Scans up to 10 lines backwards looking for an IF statement, then
    collects the condition text between IF and the branch probe line.

    Args:
        lines: All source lines of the file.
        probe_line_idx: 0-based index of the line containing the @@B: probe.

    Returns:
        Extracted condition text, stripped and joined. Empty string if no IF found.
    """
    # Search backwards for the IF keyword
    search_start = max(0, probe_line_idx - 10)
    if_line_idx: int | None = None

    for i in range(probe_line_idx - 1, search_start - 1, -1):
        stripped = lines[i].strip()
        if stripped.upper().startswith("IF ") or stripped.upper() == "IF":
            if_line_idx = i
            break
        # Stop searching backwards if we hit another branch probe or paragraph
        if "@@B:" in lines[i] or _is_paragraph_header(lines[i]):
            break

    if if_line_idx is None:
        return ""

    # Gather condition text: from IF line up to (but not including) probe line
    condition_parts: list[str] = []
    for i in range(if_line_idx, probe_line_idx):
        stripped = lines[i].strip()
        # Skip DISPLAY lines (branch probes, traces)
        if stripped.upper().startswith("DISPLAY"):
            continue
        condition_parts.append(stripped)

    condition = " ".join(condition_parts)

    # Strip the leading IF keyword
    if condition.upper().startswith("IF "):
        condition = condition[3:]

    # Strip trailing THEN
    if condition.upper().endswith(" THEN"):
        condition = condition[:-5]

    return condition.strip()


def _extract_condition_vars(condition_text: str) -> list[str]:
    """Extract variable names from a condition string.

    Finds all uppercase identifiers and filters out COBOL reserved words
    and string/numeric literals.

    Args:
        condition_text: The condition text (without IF keyword).

    Returns:
        Deduplicated list of variable names, preserving first-occurrence order.
    """
    if not condition_text:
        return []

    candidates = _RE_VARIABLE.findall(condition_text)
    seen: set[str] = set()
    variables: list[str] = []

    for name in candidates:
        if name in _COBOL_KEYWORDS:
            continue
        if name in seen:
            continue
        # Skip single-character identifiers that are likely noise (e.g. "X", "Y"
        # as PIC type indicators) -- but keep them if they look like real vars
        # (actually, single-char COBOL vars are valid, so keep them)
        seen.add(name)
        variables.append(name)

    return variables


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_mock_structure(mock_cbl_path: Path) -> ProgramStructure:
    """Parse a .mock.cbl file and extract the program structure.

    Reads the instrumented COBOL source, identifies paragraphs (from
    PROCEDURE DIVISION onward), extracts branch probes with their
    conditions, and builds a call graph from PERFORM statements.

    Args:
        mock_cbl_path: Path to the .mock.cbl file.

    Returns:
        A ProgramStructure capturing paragraphs, branches, and call graph.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If PROCEDURE DIVISION is not found or no paragraphs exist.
    """
    mock_cbl_path = Path(mock_cbl_path)
    if not mock_cbl_path.exists():
        raise FileNotFoundError(f"Mock CBL file not found: {mock_cbl_path}")

    lines = mock_cbl_path.read_text(encoding="utf-8").splitlines()
    logger.debug("Read %d lines from %s", len(lines), mock_cbl_path)

    proc_div_idx = _find_procedure_division(lines)
    logger.debug("PROCEDURE DIVISION at line %d", proc_div_idx + 1)

    # -----------------------------------------------------------------------
    # Pass 1: Identify paragraph boundaries (within PROCEDURE DIVISION)
    # -----------------------------------------------------------------------
    paragraph_starts: list[tuple[str, int]] = []  # (name, 0-based line index)

    for idx in range(proc_div_idx + 1, len(lines)):
        name = _is_paragraph_header(lines[idx])
        if name is not None:
            paragraph_starts.append((name, idx))

    if not paragraph_starts:
        raise ValueError("No paragraphs found after PROCEDURE DIVISION")

    # -----------------------------------------------------------------------
    # Pass 2: Build ParagraphInfo objects with line boundaries
    # -----------------------------------------------------------------------
    paragraphs: dict[str, ParagraphInfo] = {}
    entry_paragraph = paragraph_starts[0][0]

    for i, (name, start_idx) in enumerate(paragraph_starts):
        if i + 1 < len(paragraph_starts):
            end_idx = paragraph_starts[i + 1][1] - 1
        else:
            end_idx = len(lines) - 1

        source_lines = lines[start_idx : end_idx + 1]
        source_code = "\n".join(source_lines)

        paragraphs[name] = ParagraphInfo(
            name=name,
            line_start=start_idx + 1,  # 1-based for human readability
            line_end=end_idx + 1,
            source_code=source_code,
        )

    # -----------------------------------------------------------------------
    # Pass 3: Extract branches, PERFORMs, and conditions per paragraph
    # -----------------------------------------------------------------------
    branches: dict[str, BranchInfo] = {}
    call_graph: dict[str, list[str]] = {}

    for para_name, para_info in paragraphs.items():
        performs: list[str] = []
        branch_ids: list[str] = []

        # Iterate over the paragraph's lines using original indices
        para_start_0 = para_info.line_start - 1  # back to 0-based
        para_end_0 = para_info.line_end - 1

        for idx in range(para_start_0, para_end_0 + 1):
            line = lines[idx]

            # Check for branch probes
            for m in _RE_BRANCH_PROBE.finditer(line):
                bid = m.group(1)
                direction = m.group(2)

                if bid not in branches:
                    condition_text = _extract_condition_text(lines, idx)
                    condition_vars = _extract_condition_vars(condition_text)
                    branches[bid] = BranchInfo(
                        id=bid,
                        paragraph=para_name,
                        condition_text=condition_text,
                        condition_vars=condition_vars,
                        directions=[direction],
                    )
                    if bid not in branch_ids:
                        branch_ids.append(bid)
                else:
                    # Same branch, additional direction (e.g. T after F)
                    if direction not in branches[bid].directions:
                        branches[bid].directions.append(direction)
                    if bid not in branch_ids:
                        branch_ids.append(bid)

            # Check for PERFORM statements (skip PERFORM UNTIL, etc. that
            # don't reference a paragraph name -- our regex already handles
            # this by requiring the target to look like a paragraph name).
            for m in _RE_PERFORM.finditer(line):
                target = m.group(1)
                # Only record if it looks like a paragraph reference
                # (not a COBOL keyword like PERFORM UNTIL)
                if target not in _COBOL_KEYWORDS and target not in performs:
                    performs.append(target)

        para_info.branches = branch_ids
        para_info.performs = performs
        call_graph[para_name] = performs

    logger.info(
        "Parsed %s: %d paragraphs, %d branches, entry=%s",
        mock_cbl_path.name,
        len(paragraphs),
        len(branches),
        entry_paragraph,
    )

    return ProgramStructure(
        entry_paragraph=entry_paragraph,
        paragraphs=paragraphs,
        branches=branches,
        call_graph=call_graph,
    )
