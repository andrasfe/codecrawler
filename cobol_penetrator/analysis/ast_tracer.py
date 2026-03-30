"""AST-based variable dataflow extraction.

Reads ``.cbl.ast`` JSON files produced by specter and extracts dataflow
edges: which variables are assigned by which statements (MOVE, SET,
COMPUTE, EXEC) in which paragraphs.  This lets the system trace a
branch condition variable back to the stub or input that controls it.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DataflowEdge:
    """A single variable assignment in the COBOL program.

    Attributes:
        source_type: Origin kind — ``"stub"``, ``"variable"``,
            ``"literal"``, ``"compute"``, or ``"set_true"``.
        source_name: Concrete origin, e.g. ``"DLI-GU"``, ``"DIBSTAT"``,
            ``"'00'"``.
        target_variable: Variable being assigned, e.g. ``"WS-STATUS"``.
        paragraph: Paragraph where the assignment occurs.
        line_number: Source line (if known).
    """

    source_type: str
    source_name: str
    target_variable: str
    paragraph: str
    line_number: int | None = None


@dataclass
class ParagraphDataflow:
    """All dataflow edges within a single paragraph, in statement order."""

    paragraph: str
    edges: list[DataflowEdge] = field(default_factory=list)
    conditions: list[dict] = field(default_factory=list)
    # Each condition: {"condition": str, "variables": list[str],
    #                   "line": int, "assigns_on_true": list[DataflowEdge],
    #                   "assigns_on_false": list[DataflowEdge]}
    stubs: list[dict] = field(default_factory=list)
    # Each stub: {"type": "EXEC_DLI"|"EXEC_CICS", "raw_text": str,
    #              "line": int, "op": str}


@dataclass
class ProgramDataflow:
    """Complete dataflow map for a COBOL program, built from the AST."""

    program_id: str
    paragraphs: dict[str, ParagraphDataflow] = field(default_factory=dict)

    def edges_for_variable(self, variable: str) -> list[DataflowEdge]:
        """Return all edges that assign to *variable* across the program."""
        result = []
        for pdf in self.paragraphs.values():
            for edge in pdf.edges:
                if edge.target_variable == variable:
                    result.append(edge)
        return result

    def stubs_before_condition(
        self, paragraph: str, condition_text: str
    ) -> list[dict]:
        """Return stubs that execute before *condition_text* in *paragraph*.

        Useful to identify which stub outcome feeds a branch condition.
        """
        pdf = self.paragraphs.get(paragraph)
        if not pdf:
            return []
        # Find the condition's line
        cond_line = None
        for c in pdf.conditions:
            if c["condition"] == condition_text:
                cond_line = c.get("line")
                break
        if cond_line is None:
            return list(pdf.stubs)
        return [s for s in pdf.stubs if s.get("line", 0) < cond_line]

    def variable_source_chain(
        self, variable: str, paragraph: str
    ) -> list[DataflowEdge]:
        """Trace *variable* backward through MOVEs within *paragraph*.

        If *variable* is set by ``MOVE X TO variable`` and *X* is also
        set in the same paragraph, include that edge too (one level).
        """
        pdf = self.paragraphs.get(paragraph)
        if not pdf:
            return []
        direct = [e for e in pdf.edges if e.target_variable == variable]
        chain = list(direct)
        # One level of transitive tracing
        for edge in direct:
            if edge.source_type == "variable":
                indirect = [
                    e for e in pdf.edges
                    if e.target_variable == edge.source_name
                ]
                chain.extend(indirect)
        return chain


# ---------------------------------------------------------------------------
# AST parsing
# ---------------------------------------------------------------------------

_RE_EXEC_OP = re.compile(
    r"EXEC\s+(DLI|CICS)\s+(\w+)", re.IGNORECASE
)

_RE_SET_TARGET = re.compile(
    r"SET\s+([\w-]+)\s+TO\s+TRUE", re.IGNORECASE
)


def _extract_op(raw_text: str) -> str:
    """Extract operation name from EXEC raw text (e.g. 'DLI-GU')."""
    m = _RE_EXEC_OP.search(raw_text)
    if m:
        kind, verb = m.group(1).upper(), m.group(2).upper()
        return f"{kind}-{verb}"
    return ""


def _extract_condition_vars(condition: str) -> list[str]:
    """Extract variable names from a condition string.

    Simple heuristic: tokens that look like COBOL variable names
    (contain a hyphen or start with WS-/EIBRESP etc.) and are not
    literals or COBOL keywords.
    """
    keywords = {
        "AND", "OR", "NOT", "EQUAL", "EQUALS", "GREATER", "LESS",
        "THAN", "TO", "TRUE", "FALSE", "ZERO", "ZEROS", "ZEROES",
        "SPACE", "SPACES", "HIGH-VALUES", "LOW-VALUES", "DFHRESP",
        "NORMAL", "OF", "MQCC-OK", "MQRC-NO-MSG-AVAILABLE",
    }
    tokens = re.findall(r"[A-Z0-9][\w-]*", condition, re.IGNORECASE)
    vars_found = []
    for tok in tokens:
        upper = tok.upper()
        if upper in keywords:
            continue
        if tok.isdigit():
            continue
        if len(tok) <= 2 and "-" not in tok:
            continue
        vars_found.append(upper)
    return vars_found


def _walk_statements(
    statements: list[dict],
    paragraph: str,
    pdf: ParagraphDataflow,
    branch_side: str = "",
) -> None:
    """Recursively walk AST statements and extract dataflow edges."""
    last_stub: dict | None = None

    for stmt in statements:
        stype = stmt.get("type", "")
        attrs = stmt.get("attributes", {})
        line = stmt.get("line_start")
        children = stmt.get("children", [])

        if stype == "MOVE":
            source = attrs.get("source", "")
            targets = attrs.get("targets", "")
            if source and targets:
                for target in targets.split(","):
                    target = target.strip()
                    if not target:
                        continue
                    # Determine source type
                    if source.startswith("'") or source.startswith('"'):
                        src_type = "literal"
                    elif source.isdigit() or source == "0":
                        src_type = "literal"
                    elif last_stub and line and last_stub.get("line", 0) <= line:
                        src_type = "stub_result"
                    else:
                        src_type = "variable"
                    pdf.edges.append(DataflowEdge(
                        source_type=src_type,
                        source_name=source,
                        target_variable=target,
                        paragraph=paragraph,
                        line_number=line,
                    ))

        elif stype == "SET":
            text = stmt.get("text", "")
            m = _RE_SET_TARGET.search(text)
            if m:
                target = m.group(1).upper()
                pdf.edges.append(DataflowEdge(
                    source_type="set_true",
                    source_name="TRUE",
                    target_variable=target,
                    paragraph=paragraph,
                    line_number=line,
                ))

        elif stype == "COMPUTE":
            target = attrs.get("target", "")
            expr = attrs.get("expression", "")
            if target:
                pdf.edges.append(DataflowEdge(
                    source_type="compute",
                    source_name=expr or "expression",
                    target_variable=target,
                    paragraph=paragraph,
                    line_number=line,
                ))

        elif stype in ("EXEC_DLI", "EXEC_CICS"):
            raw = attrs.get("raw_text", "")
            op = _extract_op(raw)
            stub_info = {
                "type": stype,
                "raw_text": raw,
                "line": line,
                "op": op,
            }
            pdf.stubs.append(stub_info)
            last_stub = stub_info

        elif stype == "IF":
            condition = attrs.get("condition", "")
            cond_vars = _extract_condition_vars(condition)

            true_edges: list[DataflowEdge] = []
            false_edges: list[DataflowEdge] = []

            # Children before ELSE are the true branch;
            # children after ELSE are the false branch
            in_else = False
            for child in children:
                if child.get("type") == "ELSE":
                    in_else = True
                    continue
                # Recurse into child statements
                sub_pdf = ParagraphDataflow(paragraph=paragraph)
                _walk_statements([child], paragraph, sub_pdf)
                if in_else:
                    false_edges.extend(sub_pdf.edges)
                else:
                    true_edges.extend(sub_pdf.edges)

            pdf.conditions.append({
                "condition": condition,
                "variables": cond_vars,
                "line": line,
                "assigns_on_true": true_edges,
                "assigns_on_false": false_edges,
            })

            # Also add all child edges to the paragraph's flat edge list
            pdf.edges.extend(true_edges)
            pdf.edges.extend(false_edges)
            continue  # skip default children walk

        elif stype == "EVALUATE":
            # Treat WHEN children similarly to IF
            for child in children:
                _walk_statements([child], paragraph, pdf)
            continue

        # Recurse into children for other statement types
        if children and stype not in ("IF", "EVALUATE"):
            _walk_statements(children, paragraph, pdf, branch_side)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_program_dataflow(ast_path: Path | str) -> ProgramDataflow:
    """Load a ``.cbl.ast`` file and extract the full program dataflow.

    Args:
        ast_path: Path to the ``.cbl.ast`` JSON file.

    Returns:
        A :class:`ProgramDataflow` with edges, conditions, and stubs
        for every paragraph.
    """
    ast_path = Path(ast_path)
    raw = json.loads(ast_path.read_text(encoding="utf-8"))

    program_id = raw.get("program_id", ast_path.stem)
    dataflow = ProgramDataflow(program_id=program_id)

    for para in raw.get("paragraphs", []):
        name = para["name"]
        pdf = ParagraphDataflow(paragraph=name)
        _walk_statements(para.get("statements", []), name, pdf)
        dataflow.paragraphs[name] = pdf

    logger.info(
        "Loaded AST dataflow for %s: %d paragraphs, %d total edges",
        program_id,
        len(dataflow.paragraphs),
        sum(len(p.edges) for p in dataflow.paragraphs.values()),
    )
    return dataflow
