"""Construct structured feedback for EvoSkill learning.

Builds the ``input_prompt`` / ``agent_output`` / ``reviewer_feedback``
dicts that :pymod:`evoskill` expects when synthesising new skills from
codecrawler execution outcomes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket
    from cobol_penetrator.trace_parser import ExecutionResult


def build_success_feedback(
    ticket: ParagraphTicket | BranchTicket,
    params: dict,
    result: ExecutionResult,
) -> dict[str, str]:
    """Build a feedback dict for a successful execution.

    Args:
        ticket: The ticket that was completed.
        params: The parameters that reached the target.
        result: The structured execution result.

    Returns:
        A dict with ``input_prompt``, ``agent_output``, and
        ``reviewer_feedback`` keys suitable for
        :meth:`evoskill.SkillStore.alearn_from_feedback`.
    """
    from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket

    if isinstance(ticket, ParagraphTicket):
        return {
            "input_prompt": (
                f"Reach paragraph {ticket.paragraph} via call path "
                f"{ticket.call_path}"
            ),
            "agent_output": str(params),
            "reviewer_feedback": (
                f"SUCCESS: Reached {ticket.paragraph}. "
                f"Hit {len(set(result.paragraphs_hit))} paragraphs total. "
                f"Stubs used: {params.get('stubs', {})}. "
                f"Remember this parameter pattern for similar call chains."
            ),
        }

    # BranchTicket
    assert isinstance(ticket, BranchTicket)
    snapshot = result.variable_snapshots.get(ticket.branch_id, {})
    return {
        "input_prompt": (
            f"Flip branch {ticket.branch_id} in {ticket.paragraph} "
            f"to direction {ticket.direction}. "
            f"Condition: {ticket.condition_text}"
        ),
        "agent_output": str(params),
        "reviewer_feedback": (
            f"SUCCESS: Branch {ticket.branch_id} took direction "
            f"{ticket.direction}. Variable snapshot: {snapshot}. "
            f"Key: the controlling variables were set by these "
            f"stubs/inputs."
        ),
    }


def build_failure_feedback(
    ticket: ParagraphTicket | BranchTicket,
    attempt_count: int,
    result: ExecutionResult | None,
) -> dict[str, str]:
    """Build a feedback dict for a ticket that exhausted its attempts.

    Args:
        ticket: The ticket that was blocked.
        attempt_count: Number of attempts made so far.
        result: The last execution result, or ``None``.

    Returns:
        A dict with ``input_prompt``, ``agent_output``, and
        ``reviewer_feedback`` keys suitable for
        :meth:`evoskill.SkillStore.alearn_from_feedback`.
    """
    from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket

    if isinstance(ticket, ParagraphTicket):
        hit_paras = (
            list(set(result.paragraphs_hit))[:10] if result else []
        )
        return {
            "input_prompt": (
                f"Reach paragraph {ticket.paragraph} via call path "
                f"{ticket.call_path}"
            ),
            "agent_output": f"(failed after {attempt_count} attempts)",
            "reviewer_feedback": (
                f"FAILURE: Could not reach {ticket.paragraph} after "
                f"{attempt_count} attempts. Last run hit: {hit_paras}. "
                f"Avoid repeating these parameter patterns. Consider "
                f"different stub values or input state combinations."
            ),
        }

    # BranchTicket
    assert isinstance(ticket, BranchTicket)
    return {
        "input_prompt": (
            f"Flip branch {ticket.branch_id} to {ticket.direction}. "
            f"Condition: {ticket.condition_text}"
        ),
        "agent_output": f"(failed after {attempt_count} attempts)",
        "reviewer_feedback": (
            f"FAILURE: Could not flip branch {ticket.branch_id} to "
            f"{ticket.direction} after {attempt_count} attempts. "
            f"The condition variables {ticket.condition_vars} may be "
            f"set by a stub that was not targeted. Try different fault "
            f"injection positions."
        ),
    }


def build_stub_discovery_feedback(
    fault_value: str,
    position: int,
    operation: str,
    new_branch_count: int,
) -> dict[str, str]:
    """Build feedback for a stub-sequencing branch discovery.

    Args:
        fault_value: The fault value that was injected (e.g. ``"GE"``).
        position: The cycle position where the fault was injected.
        operation: The mock operation at that position.
        new_branch_count: Number of new branch directions found.

    Returns:
        A feedback dict suitable for EvoSkill learning.
    """
    return {
        "input_prompt": "Discover branch coverage via stub fault injection",
        "agent_output": (
            f"Injected '{fault_value}' at position {position} "
            f"({operation})"
        ),
        "reviewer_feedback": (
            f"Injecting fault value '{fault_value}' at cycle position "
            f"{position} (operation {operation}) discovered "
            f"{new_branch_count} new branch directions. This "
            f"position-to-fault mapping is reusable for similar "
            f"programs."
        ),
    }
