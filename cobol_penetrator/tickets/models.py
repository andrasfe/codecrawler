"""Ticket data models for the COBOL penetration agent system.

Defines ParagraphTicket and BranchTicket dataclasses that represent
units of work in the coverage penetration pipeline. Tickets follow
a state machine: CREATED -> CLAIMED -> IN_PROGRESS -> DONE | BLOCKED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Union

# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

CREATED = "CREATED"
CLAIMED = "CLAIMED"
IN_PROGRESS = "IN_PROGRESS"
DONE = "DONE"
BLOCKED = "BLOCKED"

ALL_STATUSES = frozenset({CREATED, CLAIMED, IN_PROGRESS, DONE, BLOCKED})


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ParagraphTicket
# ---------------------------------------------------------------------------


@dataclass
class ParagraphTicket:
    """A ticket to reach and exercise a specific COBOL paragraph.

    Attributes:
        id: Unique identifier, e.g. ``"PARA-2000-VALIDATE"``.
        paragraph: Target paragraph name, e.g. ``"2000-VALIDATE"``.
        status: Current lifecycle state (see status constants).
        assigned_agent: Name of the agent class working on this ticket.
        call_path: Ordered list of paragraphs from entry to target.
        required_stubs: Stub operations that must succeed to reach this paragraph.
        successful_params: Input parameters that successfully reached the paragraph.
        branches_discovered: Branch IDs found inside the paragraph once reached.
        attempts: Number of execution attempts so far.
        created_at: ISO-8601 timestamp of creation.
        updated_at: ISO-8601 timestamp of last modification.
    """

    id: str
    paragraph: str
    status: str = CREATED
    assigned_agent: str | None = None
    call_path: list[str] = field(default_factory=list)
    required_stubs: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    successful_params: dict | None = None
    branches_discovered: list[str] = field(default_factory=list)
    attempts: int = 0
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)


# ---------------------------------------------------------------------------
# BranchTicket
# ---------------------------------------------------------------------------


@dataclass
class BranchTicket:
    """A ticket to hit a specific branch direction inside a paragraph.

    Attributes:
        id: Unique identifier, e.g. ``"BRANCH-5-T"``.
        branch_id: Numeric branch probe identifier, e.g. ``"5"``.
        direction: Target direction — ``"T"``, ``"F"``, ``"W1"``, ``"WO"``, etc.
        paragraph: Paragraph that contains this branch.
        condition_text: Human-readable condition, e.g. ``"WS-STATUS = '00'"``.
        condition_vars: COBOL variables involved in the condition.
        status: Current lifecycle state.
        assigned_agent: Name of the agent class working on this ticket.
        successful_params: Input parameters that hit this branch + direction.
        variable_snapshot: ``@@V:`` data captured when the branch was taken.
        attempts: Number of execution attempts so far.
        created_at: ISO-8601 timestamp of creation.
        updated_at: ISO-8601 timestamp of last modification.
    """

    id: str
    branch_id: str
    direction: str
    paragraph: str
    condition_text: str = ""
    condition_vars: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    status: str = CREATED
    assigned_agent: str | None = None
    successful_params: dict | None = None
    variable_snapshot: dict | None = None
    attempts: int = 0
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)


# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

Ticket = Union[ParagraphTicket, BranchTicket]
