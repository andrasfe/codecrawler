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
