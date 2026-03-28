"""Shared knowledge store for cross-ticket intelligence.

Accumulates learned information across the entire penetration run so that
child agents can reuse successful parameters from parent tickets, branch
agents can leverage sibling branch data, and all agents benefit from
variable observations and failed-attempt history.
"""

from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket, Ticket
    from cobol_penetrator.trace_parser import ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class LearnedKnowledge:
    """Accumulates intelligence across the entire penetration run.

    Attributes:
        successful_params: Mapping of paragraph name to the params that
            first reached it.
        branch_params: Mapping of ``"branch_id:direction"`` to the params
            that produced that branch hit.
        variable_observations: Mapping of variable name to a list of
            unique observed values from ``@@V`` snapshots.
        stub_outcomes: Mapping of stub operation to a list of outcomes
            that contributed to coverage.
        failed_attempts: Mapping of target (paragraph or
            ``"BRANCH-<id>"`` ) to a list of dicts recording failed
            attempts, capped at 20 per target.
        call_path_params: Mapping of ``"caller->callee"`` to the params
            that exercised that call edge.
    """

    successful_params: dict[str, dict] = field(default_factory=dict)
    branch_params: dict[str, dict] = field(default_factory=dict)
    variable_observations: dict[str, list[str]] = field(
        default_factory=dict
    )
    stub_outcomes: dict[str, list[str]] = field(default_factory=dict)
    failed_attempts: dict[str, list[dict]] = field(default_factory=dict)
    call_path_params: dict[str, dict] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_execution(
        self,
        params: dict,
        result: ExecutionResult,
        ticket: Ticket | None = None,
    ) -> None:
        """Record an execution result into the knowledge base.

        Updates every applicable section of the knowledge store:
        variable observations, branch hits, stub outcomes, paragraph
        hits, call chain edges, and (optionally) failed-attempt history.

        Args:
            params: The params dict that was executed.
            result: The structured execution result.
            ticket: The ticket being worked on, if any. Used to record
                failures when the target was not reached.
        """
        # Record variable observations from @@V snapshots
        for _bid, vars_dict in result.variable_snapshots.items():
            for var, val in vars_dict.items():
                obs = self.variable_observations.setdefault(var, [])
                str_val = str(val)
                if str_val not in obs:
                    obs.append(str_val)

        # Record branch hits
        for bid, direction in result.branches_hit.items():
            key = f"{bid}:{direction}"
            if key not in self.branch_params:
                self.branch_params[key] = dict(params)

        # Record stub outcomes that produced coverage
        for op in result.mock_ops:
            self.stub_outcomes.setdefault(op, [])

        # Record paragraph hits
        for para in set(result.paragraphs_hit):
            if para not in self.successful_params:
                self.successful_params[para] = dict(params)

        # Record call chain params
        for caller, callee in result.call_chain:
            key = f"{caller}->{callee}"
            if key not in self.call_path_params:
                self.call_path_params[key] = dict(params)

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
            target = f"BRANCH-{ticket.branch_id}"
            is_hit = (
                ticket.branch_id in result.branches_hit
                and result.branches_hit[ticket.branch_id] == ticket.direction
            )
        else:
            return

        if not is_hit:
            fails = self.failed_attempts.setdefault(target, [])
            if len(fails) < 20:  # cap stored failures
                fails.append(
                    {
                        "params": params,
                        "paragraphs_hit": list(set(result.paragraphs_hit))[
                            :10
                        ],
                    }
                )

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get_parent_params(self, call_path: list[str]) -> dict | None:
        """Get successful params from the nearest completed parent in call_path.

        Walks the call path backward (skipping the last element, which is
        the target itself) and returns the first match found in
        ``successful_params``.

        Args:
            call_path: Ordered list of paragraphs from entry to target.

        Returns:
            A copy of the parent's params dict, or ``None`` if no parent
            has been successfully reached.
        """
        if not call_path or len(call_path) < 2:
            return None
        for para in reversed(call_path[:-1]):  # Walk backward, skip self
            if para in self.successful_params:
                return copy.deepcopy(self.successful_params[para])
        return None

    def get_sibling_branch_params(
        self, branch_id: str
    ) -> dict[str, dict]:
        """Get params that hit other directions of the same branch.

        Useful for a BranchAgent trying to flip a branch: knowing what
        params produced the *opposite* direction is a strong starting
        point.

        Args:
            branch_id: The branch identifier (e.g. ``"1"``).

        Returns:
            A dict mapping ``"branch_id:direction"`` to params for every
            recorded direction of the given branch.
        """
        result: dict[str, dict] = {}
        for key, params in self.branch_params.items():
            if key.startswith(f"{branch_id}:"):
                result[key] = params
        return result

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Persist the knowledge store to a JSON file.

        ``failed_attempts`` are excluded because they can be very large.

        Args:
            path: Filesystem path for the JSON file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "successful_params": self.successful_params,
            "branch_params": self.branch_params,
            "variable_observations": self.variable_observations,
            "stub_outcomes": self.stub_outcomes,
            "call_path_params": self.call_path_params,
            # Don't save failed_attempts (too large)
        }
        path.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
        logger.debug("Saved knowledge to %s", path)

    @classmethod
    def load(cls, path: Path) -> LearnedKnowledge:
        """Load a knowledge store from a JSON file.

        Returns an empty store if the file does not exist.

        Args:
            path: Filesystem path to read from.

        Returns:
            A populated ``LearnedKnowledge`` instance.
        """
        path = Path(path)
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning(
                "Failed to load knowledge from %s — starting fresh", path
            )
            return cls()
        return cls(
            successful_params=data.get("successful_params", {}),
            branch_params=data.get("branch_params", {}),
            variable_observations=data.get("variable_observations", {}),
            stub_outcomes=data.get("stub_outcomes", {}),
            call_path_params=data.get("call_path_params", {}),
        )
