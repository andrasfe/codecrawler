"""Within-run knowledge for cross-ticket param inheritance and failure tracking.

This is the lightweight, ephemeral counterpart to EvoSkill's persistent
cross-run skill store.  LearnedKnowledge lives for a single penetration
run and provides:

1. **Parent param inheritance** — child tickets start from their parent's
   proven working params instead of scratch.
2. **Failure dedup** — agents see what was already tried so they don't
   repeat the same failing params.

EvoSkill handles cross-run learning (persisted skills, LLM-distilled
insights).  LearnedKnowledge handles within-run plumbing (raw param
dicts passed between tickets).

Not persisted to disk — rebuilt on each run.  Resume uses EvoSkill
skills instead.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket, Ticket
    from cobol_penetrator.trace_parser import ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class LearnedKnowledge:
    """Within-run knowledge store for param inheritance and failure tracking.

    Attributes:
        successful_params: Paragraph name -> first params that reached it.
            Used by child agents to inherit parent's working params.
        failed_attempts: Target -> list of failed param dicts (capped at 10).
            Used by agents to avoid repeating the same failing inputs.
    """

    successful_params: dict[str, dict] = field(default_factory=dict)
    failed_attempts: dict[str, list[dict]] = field(default_factory=dict)

    def record_execution(
        self,
        params: dict,
        result: ExecutionResult,
        ticket: Ticket | None = None,
    ) -> None:
        """Record an execution result.

        Stores the first successful params per paragraph and tracks
        failures per ticket target.
        """
        # Record first successful params per paragraph
        for para in set(result.paragraphs_hit):
            if para not in self.successful_params:
                self.successful_params[para] = dict(params)

        # Record failures for targeted ticket
        if ticket is not None:
            self._record_failure_if_missed(params, result, ticket)

    def _record_failure_if_missed(
        self,
        params: dict,
        result: ExecutionResult,
        ticket: Ticket,
    ) -> None:
        """Record a failed attempt if the ticket target was not reached."""
        from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket

        if isinstance(ticket, ParagraphTicket):
            target = ticket.paragraph
            is_hit = target in result.paragraphs_hit
        elif isinstance(ticket, BranchTicket):
            target = f"BRANCH-{ticket.branch_id}-{ticket.direction}"
            is_hit = (
                ticket.branch_id in result.branches_hit
                and result.branches_hit[ticket.branch_id] == ticket.direction
            )
        else:
            return

        if not is_hit:
            fails = self.failed_attempts.setdefault(target, [])
            if len(fails) < 10:
                fails.append(dict(params))

    def get_parent_params(self, call_path: list[str]) -> dict | None:
        """Get successful params from the nearest completed parent.

        Walks the call path backward (skipping self) and returns the
        first match.
        """
        if not call_path or len(call_path) < 2:
            return None
        for para in reversed(call_path[:-1]):
            if para in self.successful_params:
                return copy.deepcopy(self.successful_params[para])
        return None

    def get_failed_params(self, target: str) -> list[dict]:
        """Get list of previously failed param dicts for a target."""
        return list(self.failed_attempts.get(target, []))
