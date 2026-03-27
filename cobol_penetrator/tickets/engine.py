"""Ticket state-machine engine.

Wraps :class:`TicketStore` with lifecycle operations that enforce the
ticket state machine:

    CREATED -> CLAIMED -> IN_PROGRESS -> DONE
                 \\                \\
                  \\-> BLOCKED      \\-> BLOCKED

All state transitions are validated; invalid transitions raise
:class:`InvalidTransitionError`.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import (
    BLOCKED,
    CLAIMED,
    CREATED,
    DONE,
    IN_PROGRESS,
    BranchTicket,
    ParagraphTicket,
    Ticket,
    _now_iso,
)
from .store import TicketStore

logger = logging.getLogger(__name__)

# Default maximum attempts before auto-blocking a ticket.
DEFAULT_MAX_ATTEMPTS = 5


class InvalidTransitionError(Exception):
    """Raised when a ticket state transition is not allowed."""


class TicketEngine:
    """High-level ticket lifecycle manager.

    Owns a :class:`TicketStore` and exposes operations that enforce the
    state machine.  All mutations go through this class so that
    transition rules are applied consistently.

    Args:
        store: The backing ticket store. If ``None`` a fresh store is created.
        max_attempts: Number of attempts before a ticket is auto-blocked.
    """

    def __init__(
        self,
        store: TicketStore | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        self.store = store or TicketStore()
        self.max_attempts = max_attempts

    # ------------------------------------------------------------------
    # Ticket creation helpers
    # ------------------------------------------------------------------

    def create_entry_ticket(self, paragraph: str) -> ParagraphTicket:
        """Create the initial ParagraphTicket for the program entry point.

        The ``call_path`` contains only the entry paragraph itself and
        no stubs are required.

        Args:
            paragraph: The entry paragraph name, e.g. ``"1000-MAIN"``.

        Returns:
            The newly created ticket.
        """
        ticket = ParagraphTicket(
            id=f"PARA-{paragraph}",
            paragraph=paragraph,
            call_path=[paragraph],
        )
        self.store.add(ticket)
        logger.info("Created entry ticket %s", ticket.id)
        return ticket

    def create_paragraph_ticket(
        self,
        paragraph: str,
        call_path: list[str],
        required_stubs: list[str] | None = None,
    ) -> ParagraphTicket:
        """Create a ParagraphTicket for a discovered callee.

        Args:
            paragraph: Target paragraph name.
            call_path: Ordered call chain from entry to *paragraph*.
            required_stubs: Stub operations needed to reach this paragraph.

        Returns:
            The newly created ticket.
        """
        ticket = ParagraphTicket(
            id=f"PARA-{paragraph}",
            paragraph=paragraph,
            call_path=list(call_path),
            required_stubs=list(required_stubs) if required_stubs else [],
        )
        self.store.add(ticket)
        logger.info("Created paragraph ticket %s", ticket.id)
        return ticket

    def create_branch_ticket(
        self,
        branch_id: str,
        direction: str,
        paragraph: str,
        condition_text: str = "",
        condition_vars: list[str] | None = None,
    ) -> BranchTicket:
        """Create a BranchTicket for a specific branch direction.

        Args:
            branch_id: The numeric branch probe identifier.
            direction: Target direction (``"T"``, ``"F"``, ``"W1"``, etc.).
            paragraph: The paragraph containing this branch.
            condition_text: Readable condition expression.
            condition_vars: COBOL variables involved in the condition.

        Returns:
            The newly created ticket.
        """
        ticket = BranchTicket(
            id=f"BRANCH-{branch_id}-{direction}",
            branch_id=branch_id,
            direction=direction,
            paragraph=paragraph,
            condition_text=condition_text,
            condition_vars=list(condition_vars) if condition_vars else [],
        )
        self.store.add(ticket)
        logger.info("Created branch ticket %s", ticket.id)
        return ticket

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def claim_next(self) -> Ticket | None:
        """Claim the next available ticket from the store.

        Delegates priority logic to :meth:`TicketStore.claim_next`.

        Returns:
            The claimed ticket, or ``None`` if nothing is available.
        """
        return self.store.claim_next()

    def start_work(self, ticket: Ticket) -> None:
        """Transition a CLAIMED ticket to IN_PROGRESS.

        Args:
            ticket: The ticket to start working on.

        Raises:
            InvalidTransitionError: If the ticket is not in CLAIMED status.
        """
        self._assert_status(ticket, CLAIMED, IN_PROGRESS)
        ticket.status = IN_PROGRESS
        ticket.updated_at = _now_iso()
        logger.debug("Ticket %s -> IN_PROGRESS", ticket.id)

    def complete(
        self,
        ticket: Ticket,
        params: dict[str, Any],
        result: dict[str, Any] | None = None,
    ) -> None:
        """Mark a ticket as DONE with the successful parameters.

        Args:
            ticket: The ticket to complete.
            params: The input parameters that achieved success.
            result: Optional execution result metadata.

        Raises:
            InvalidTransitionError: If the ticket is not in IN_PROGRESS status.
        """
        self._assert_status(ticket, IN_PROGRESS, DONE)
        ticket.status = DONE
        ticket.successful_params = dict(params)
        ticket.updated_at = _now_iso()
        if result and isinstance(ticket, ParagraphTicket):
            ticket.branches_discovered = result.get(
                "branches_discovered", []
            )
        if result and isinstance(ticket, BranchTicket):
            ticket.variable_snapshot = result.get("variable_snapshot")
        logger.info("Ticket %s -> DONE", ticket.id)

    def block(self, ticket: Ticket) -> None:
        """Block a ticket that cannot make progress.

        Valid from CLAIMED or IN_PROGRESS.

        Args:
            ticket: The ticket to block.

        Raises:
            InvalidTransitionError: If the ticket is not in a blockable status.
        """
        if ticket.status not in (CLAIMED, IN_PROGRESS):
            raise InvalidTransitionError(
                f"Cannot block ticket {ticket.id}: "
                f"status is {ticket.status!r}, expected CLAIMED or IN_PROGRESS"
            )
        ticket.status = BLOCKED
        ticket.updated_at = _now_iso()
        logger.info("Ticket %s -> BLOCKED", ticket.id)

    def record_attempt(self, ticket: Ticket) -> None:
        """Increment the attempt counter; auto-block if limit reached.

        Args:
            ticket: The ticket being attempted.
        """
        ticket.attempts += 1
        ticket.updated_at = _now_iso()
        if ticket.attempts >= self.max_attempts:
            logger.warning(
                "Ticket %s reached max attempts (%d) — blocking",
                ticket.id,
                self.max_attempts,
            )
            # Force block regardless of current status so the ticket
            # does not linger.  The status is overwritten directly because
            # this is an automatic safety-net, not a normal transition.
            ticket.status = BLOCKED

    # ------------------------------------------------------------------
    # Delegated queries
    # ------------------------------------------------------------------

    def open_tickets_exist(self) -> bool:
        """Return ``True`` if any tickets are still workable."""
        return self.store.open_tickets_exist()

    def done_paragraphs(self) -> set[str]:
        """Return paragraph names that have been completed."""
        return self.store.done_paragraphs()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _assert_status(
        ticket: Ticket, expected: str, target: str
    ) -> None:
        """Validate that *ticket* is in *expected* status.

        Args:
            ticket: The ticket to check.
            expected: Required current status.
            target: The status we intend to move to (used in the error message).

        Raises:
            InvalidTransitionError: If the current status does not match.
        """
        if ticket.status != expected:
            raise InvalidTransitionError(
                f"Cannot transition ticket {ticket.id} to {target}: "
                f"status is {ticket.status!r}, expected {expected!r}"
            )
