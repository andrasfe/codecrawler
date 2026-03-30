"""Prompt enrichment helpers for LLM-based strategies.

Converts FieldReport data into human-readable sections that are appended
to LLM prompts, giving the model concrete type/domain information about
COBOL variables so it can produce better test parameters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cobol_penetrator.analysis.field_report import FieldReport
    from cobol_penetrator.knowledge import LearnedKnowledge
    from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket, Ticket


def format_variable_metadata(
    field_report: FieldReport,
    relevant_vars: list[str] | None = None,
) -> str:
    """Format variable metadata for LLM prompts.

    Produces a human-readable summary of each variable's PIC clause,
    data type, semantic classification, and known value constraints.

    Args:
        field_report: The FieldReport containing variable domains.
        relevant_vars: If provided, only include these variable names.
            If None, include all fields from the report.

    Returns:
        A formatted string describing the variables, or an empty string
        if no variables match.

    Example output::

        Variable Definitions:
          WS-STATUS: PIC X(02), type=alpha, semantic=status_file
            Known values: '00', '10', '23'
          WS-AMOUNT: PIC 9(9), type=numeric, range=0..999999999, semantic=amount
    """
    fields = field_report.fields
    if not fields:
        return ""

    if relevant_vars is not None:
        names = [v for v in relevant_vars if v in fields]
    else:
        names = list(fields.keys())

    if not names:
        return ""

    lines: list[str] = ["Variable Definitions:"]
    for name in names:
        domain = fields[name]

        # Build PIC description
        pic_desc = _format_pic(domain)

        # Build type + semantic
        parts = [pic_desc, f"type={domain.data_type}"]
        if domain.semantic_type and domain.semantic_type != "generic":
            parts.append(f"semantic={domain.semantic_type}")
        if domain.min_value is not None and domain.max_value is not None:
            parts.append(f"range={domain.min_value}..{domain.max_value}")
        if domain.set_by_stub:
            parts.append(f"set_by_stub={domain.set_by_stub}")

        lines.append(f"  {name}: {', '.join(parts)}")

        # Known values (condition literals + 88-level)
        known_values = _collect_known_values(domain)
        if known_values:
            formatted = ", ".join(repr(v) for v in known_values[:10])
            lines.append(f"    Known values: {formatted}")

        # Default value
        if domain.default_value is not None:
            lines.append(f"    Default: {domain.default_value!r}")

    return "\n".join(lines)


def format_condition_hints(
    field_report: FieldReport,
    relevant_vars: list[str] | None = None,
) -> str:
    """Format harvested condition literal values.

    Extracts the condition values that appear in IF/EVALUATE statements
    for each variable, giving the LLM concrete values to use.

    Args:
        field_report: The FieldReport containing condition hints.
        relevant_vars: If provided, only include these variable names.
            If None, include all variables with condition hints.

    Returns:
        A formatted string describing condition values, or an empty
        string if no condition hints exist.

    Example output::

        Condition values found in program:
          WS-STATUS is compared to: '00', '10', '23'
          WS-FLAG is compared to: 'Y', 'N'
    """
    hints = field_report.condition_hints
    if not hints:
        return ""

    if relevant_vars is not None:
        names = [v for v in relevant_vars if v in hints]
    else:
        names = list(hints.keys())

    if not names:
        return ""

    lines: list[str] = ["Condition values found in program:"]
    for name in names:
        values = hints[name]
        if values:
            formatted = ", ".join(repr(v) for v in values[:10])
            lines.append(f"  {name} is compared to: {formatted}")

    # Only return if we actually added condition lines
    if len(lines) <= 1:
        return ""

    return "\n".join(lines)


def format_execution_history(
    history: list[dict],
    max_entries: int = 5,
) -> str:
    """Format prior execution attempts for LLM context.

    Gives the LLM information about what has already been tried so it
    can avoid repeating failed approaches and build on partial successes.

    Args:
        history: List of dicts, each with keys like ``"input_state"``,
            ``"stubs"``, ``"paragraphs_hit"``, ``"branches_hit"``.
            Most recent entries should be first.
        max_entries: Maximum number of entries to include.

    Returns:
        A formatted string describing prior attempts, or an empty string
        if the history is empty.

    Example output::

        Prior attempts (most recent first):
          Attempt 1: input_state={WS-STATUS: '00'}, stubs={...} -> hit 3 paragraphs
          Attempt 2: input_state={WS-STATUS: '10'}, stubs={...} -> hit 1 paragraph
    """
    if not history:
        return ""

    entries = history[:max_entries]
    lines: list[str] = ["Prior attempts (most recent first):"]

    for idx, entry in enumerate(entries, 1):
        input_state = entry.get("input_state", {})
        stubs = entry.get("stubs", {})
        paras_hit = entry.get("paragraphs_hit", [])
        branches_hit = entry.get("branches_hit", {})

        # Compact formatting for input state
        state_parts = [
            f"{k}: {v!r}" for k, v in list(input_state.items())[:5]
        ]
        state_text = ", ".join(state_parts) if state_parts else "empty"
        if len(input_state) > 5:
            state_text += f", ... (+{len(input_state) - 5} more)"

        # Compact formatting for stubs
        stub_count = len(stubs)
        stub_text = f"{stub_count} stub(s)" if stub_count else "none"

        # Results
        para_count = len(paras_hit) if isinstance(paras_hit, (list, set, frozenset)) else 0
        branch_count = len(branches_hit) if isinstance(branches_hit, (dict, set, frozenset)) else 0

        lines.append(
            f"  Attempt {idx}: input={{{state_text}}}, "
            f"stubs={stub_text} -> "
            f"hit {para_count} paragraph(s), "
            f"{branch_count} branch(es)"
        )

    return "\n".join(lines)


def format_knowledge_context(
    knowledge: LearnedKnowledge,
    ticket: Ticket,
    field_report: Any = None,
) -> str:
    """Format shared knowledge for LLM prompt enrichment.

    Selects and formats the most relevant knowledge for the given ticket
    type: parent params for paragraph tickets, sibling branch data for
    branch tickets, variable observations, stub outcomes, and recent
    failed attempts.

    Args:
        knowledge: The shared knowledge store.
        ticket: The ticket currently being worked on.
        field_report: Optional field report (unused currently but
            reserved for future enrichment).

    Returns:
        A formatted string with relevant knowledge sections, or an
        empty string if no relevant knowledge exists.
    """
    from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket

    sections: list[str] = []

    # Parent success params
    if isinstance(ticket, ParagraphTicket) and ticket.call_path:
        parent_params = knowledge.get_parent_params(ticket.call_path)
        if parent_params:
            sections.append(
                f"Parent paragraph's successful params:\n"
                f"  {parent_params}"
            )

    # Containing paragraph params for branch tickets
    if isinstance(ticket, BranchTicket):
        para_params = knowledge.successful_params.get(ticket.paragraph)
        if para_params:
            sections.append(
                f"Containing paragraph reached with: {para_params}"
            )

    # Failed attempts (so agents don't repeat the same failing params)
    if isinstance(ticket, ParagraphTicket):
        target = ticket.paragraph
    elif isinstance(ticket, BranchTicket):
        target = f"BRANCH-{ticket.branch_id}-{ticket.direction}"
    else:
        target = ""

    fails = knowledge.failed_attempts.get(target, [])
    if fails:
        sections.append(
            f"Prior failed attempts ({len(fails)} total):"
        )
        for f in fails[-3:]:  # Show last 3
            sections.append(f"  Tried: {f}")

    return "\n\n".join(sections) if sections else ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def format_ast_dataflow(
    dataflow: Any,
    paragraph: str,
    condition_vars: list[str],
    condition_text: str = "",
) -> str:
    """Format AST-derived dataflow for a branch's condition variables.

    Shows the LLM exactly where each condition variable gets its value
    (MOVE from another variable, stub result, literal, etc.) and which
    stubs execute before the branch condition.

    Args:
        dataflow: A :class:`ProgramDataflow` instance (or ``None``).
        paragraph: The paragraph containing the branch.
        condition_vars: Variables in the branch condition.
        condition_text: The condition expression.

    Returns:
        Formatted string, or empty string if no dataflow info.
    """
    if dataflow is None:
        return ""

    pdf = dataflow.paragraphs.get(paragraph)
    if not pdf:
        return ""

    lines: list[str] = [
        f"AST dataflow analysis for paragraph {paragraph}:"
    ]

    # Show how each condition variable is assigned
    for var in condition_vars:
        chain = dataflow.variable_source_chain(var, paragraph)
        if chain:
            for edge in chain:
                lines.append(
                    f"  {edge.target_variable} ← {edge.source_type}: "
                    f"{edge.source_name} (line {edge.line_number})"
                )
        else:
            # Check across the whole program
            all_edges = dataflow.edges_for_variable(var)
            if all_edges:
                for edge in all_edges[:3]:
                    lines.append(
                        f"  {edge.target_variable} ← {edge.source_type}: "
                        f"{edge.source_name} in {edge.paragraph} "
                        f"(line {edge.line_number})"
                    )
            else:
                lines.append(f"  {var}: no assignment found (may be 88-level)")

    # Show stubs that execute before the condition
    if condition_text:
        stubs = dataflow.stubs_before_condition(paragraph, condition_text)
        if stubs:
            lines.append(f"  Stubs before condition:")
            for s in stubs:
                lines.append(f"    {s['op']} (line {s['line']})")

    if len(lines) <= 1:
        return ""
    return "\n".join(lines)


def format_directional_feedback(
    execution_history: list[dict],
    branch_id: str,
    target_direction: str,
    condition_text: str,
) -> str:
    """Format feedback on *why* prior attempts missed the target direction.

    For each prior execution that reached the branch, reports the actual
    direction taken and the variable values at that point.

    Args:
        execution_history: Prior turn dicts (must include ``branches_hit``
            and optionally ``variable_snapshots``).
        branch_id: The target branch ID.
        target_direction: The desired direction (T/F/W1/WO).
        condition_text: The branch condition expression.

    Returns:
        Formatted feedback string, or empty string if no relevant data.
    """
    if not execution_history:
        return ""

    lines: list[str] = []
    for i, entry in enumerate(execution_history, 1):
        branches = entry.get("branches_hit", {})
        snapshots = entry.get("variable_snapshots", {})
        paras = entry.get("paragraphs_hit", [])

        if branch_id in branches:
            actual = branches[branch_id]
            snap = snapshots.get(branch_id, {})
            snap_text = ", ".join(
                f"{v}='{val}'" for v, val in snap.items()
            ) if snap else "no snapshot"
            lines.append(
                f"  Turn {i}: Branch {branch_id} took {actual} "
                f"(need {target_direction}). At evaluation: {snap_text}."
            )
            if actual != target_direction and condition_text:
                lines.append(
                    f"    Condition: {condition_text}"
                )
        else:
            # Check if paragraph was even reached
            paragraph_info = entry.get("paragraph", "")
            if paragraph_info and paragraph_info not in paras:
                lines.append(
                    f"  Turn {i}: Branch {branch_id} not reached "
                    f"(paragraph {paragraph_info} not hit)."
                )
            else:
                lines.append(
                    f"  Turn {i}: Branch {branch_id} not evaluated."
                )

    if not lines:
        return ""
    return "Directional feedback from prior attempts:\n" + "\n".join(lines)


def format_stub_fingerprint(
    fingerprint: Any,
    branch_id: str,
    target_direction: str,
) -> str:
    """Format empirical stub fingerprint data for a branch.

    Shows which FIFO position perturbations flip the branch to the
    target direction, including side-effect warnings.

    Args:
        fingerprint: A :class:`StubFingerprint` instance (or ``None``).
        branch_id: The target branch ID.
        target_direction: The desired direction.

    Returns:
        Formatted string, or empty string if no triggers found.
    """
    if fingerprint is None:
        return ""

    triggers = fingerprint.get_triggers(branch_id, target_direction)
    if not triggers:
        return ""

    lines: list[str] = [
        f"Empirical stub fingerprint for branch {branch_id} "
        f"direction {target_direction}:"
    ]
    for pos, fv in triggers[:5]:  # cap at 5
        op = fingerprint.op_name(pos)
        lines.append(f"  Position {pos} ({op}) with value '{fv}' "
                      f"flips {branch_id} to {target_direction}.")
        # Side-effect warnings
        side = fingerprint.get_side_effects(pos, fv)
        other = {s for s in side if not s.startswith(f"{branch_id}:")}
        if other:
            lines.append("  WARNING: this also changes:")
            for s in sorted(other)[:3]:
                lines.append(f"    - {s}")

    return "\n".join(lines)


def format_variable_differential(
    fingerprint: Any,
    branch_id: str,
) -> str:
    """Format variable value differences at a branch point.

    Compares variable snapshots between baseline and the first
    perturbation that changed this branch.

    Args:
        fingerprint: A :class:`StubFingerprint` instance (or ``None``).
        branch_id: The branch ID to compare.

    Returns:
        Formatted string, or empty string if no diff data.
    """
    if fingerprint is None:
        return ""

    diffs = fingerprint.get_variable_diff(branch_id)
    if not diffs:
        return ""

    lines = [f"Variable differences at branch {branch_id}:"]

    base_snap = fingerprint.baseline.variable_snapshots.get(branch_id, {})
    if base_snap:
        vals = ", ".join(f"{v}='{val}'" for v, val in base_snap.items())
        lines.append(f"  Baseline: {vals}")

    changed: list[str] = []
    unchanged: list[str] = []
    for var, (old, new) in diffs.items():
        changed.append(f"{var} ('{old}' -> '{new}')")

    if base_snap:
        for var in base_snap:
            if var not in diffs:
                unchanged.append(var)

    if changed:
        lines.append(f"  Changed: {', '.join(changed)}")
    if unchanged:
        lines.append(f"  Unchanged: {', '.join(unchanged)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_pic(domain: Any) -> str:
    """Format a PIC-like description from a VariableDomain."""
    if domain.data_type == "alpha":
        return f"PIC X({domain.max_length:02d})"
    elif domain.data_type in ("numeric", "packed", "comp"):
        pic = f"PIC {'S' if domain.signed else ''}9({domain.max_length})"
        if domain.precision > 0:
            pic += f"V9({domain.precision})"
        return pic
    return f"PIC ?({domain.max_length})"


def _collect_known_values(domain: Any) -> list:
    """Collect all known values for a variable domain.

    Merges condition_literals and 88-level values into a deduplicated
    list, preserving order.
    """
    seen: set = set()
    values: list = []

    for lit in getattr(domain, "condition_literals", []):
        if lit not in seen:
            seen.add(lit)
            values.append(lit)

    for _name, val in getattr(domain, "valid_88_values", {}).items():
        if val not in seen:
            seen.add(val)
            values.append(val)

    return values
