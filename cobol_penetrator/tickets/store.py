"""In-memory ticket store with JSON persistence.

Provides CRUD operations, priority-based claim logic, and crash-recovery
semantics (CLAIMED / IN_PROGRESS tickets are reset to CREATED on load).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .models import (
    BLOCKED,
    CLAIMED,
    CREATED,
    DONE,
    IN_PROGRESS,
    BranchTicket,
    ParagraphTicket,
    Ticket,
)

logger = logging.getLogger(__name__)


class DuplicateTicketError(Exception):
    """Raised when attempting to add a ticket whose ID already exists."""


class TicketNotFoundError(Exception):
    """Raised when a ticket ID is not present in the store."""


class TicketStore:
    """In-memory ticket store backed by optional JSON persistence.

    Tickets are stored in a ``dict[str, Ticket]`` keyed by ticket ID.
    Claim priority is ParagraphTickets first (shorter ``call_path`` wins),
    then BranchTickets, considering only tickets in CREATED status.
    """

    def __init__(self) -> None:
        self._tickets: dict[str, Ticket] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, ticket: Ticket) -> None:
        """Add a ticket to the store.

        Args:
            ticket: The ticket to add.

        Raises:
            DuplicateTicketError: If a ticket with the same ID already exists.
        """
        if ticket.id in self._tickets:
            raise DuplicateTicketError(
                f"Ticket with ID '{ticket.id}' already exists"
            )
        self._tickets[ticket.id] = ticket
        logger.debug("Added ticket %s", ticket.id)

    def get(self, ticket_id: str) -> Ticket:
        """Retrieve a ticket by ID.

        Args:
            ticket_id: The unique ticket identifier.

        Returns:
            The matching ticket.

        Raises:
            TicketNotFoundError: If no ticket with the given ID exists.
        """
        try:
            return self._tickets[ticket_id]
        except KeyError:
            raise TicketNotFoundError(
                f"No ticket with ID '{ticket_id}'"
            ) from None

    def claim_next(self) -> Ticket | None:
        """Claim the highest-priority CREATED ticket.

        Priority rules:
            1. ParagraphTickets before BranchTickets.
            2. Among ParagraphTickets, shorter ``call_path`` first.
            3. Among BranchTickets, ordered by ``id`` for determinism.

        The claimed ticket's status is set to CLAIMED.

        Returns:
            The claimed ticket, or ``None`` if no CREATED tickets exist.
        """
        created = [
            t for t in self._tickets.values() if t.status == CREATED
        ]
        if not created:
            return None

        paragraphs = [
            t for t in created if isinstance(t, ParagraphTicket)
        ]
        branches = [
            t for t in created if isinstance(t, BranchTicket)
        ]

        if paragraphs:
            paragraphs.sort(key=lambda t: (len(t.call_path), t.id))
            chosen = paragraphs[0]
        else:
            branches.sort(key=lambda t: t.id)
            chosen = branches[0]

        chosen.status = CLAIMED
        logger.debug("Claimed ticket %s", chosen.id)
        return chosen

    def open_tickets_exist(self) -> bool:
        """Return ``True`` if any tickets are not DONE or BLOCKED."""
        return any(
            t.status not in (DONE, BLOCKED)
            for t in self._tickets.values()
        )

    def done_paragraphs(self) -> set[str]:
        """Return the set of paragraph names with DONE ParagraphTickets."""
        return {
            t.paragraph
            for t in self._tickets.values()
            if isinstance(t, ParagraphTicket) and t.status == DONE
        }

    def all_tickets(self) -> list[Ticket]:
        """Return all tickets as a list (insertion-order)."""
        return list(self._tickets.values())

    # ------------------------------------------------------------------
    # Knowledge helpers
    # ------------------------------------------------------------------

    def get_successful_params(self, paragraph: str) -> dict | None:
        """Get successful params for a completed paragraph ticket.

        Args:
            paragraph: The paragraph name to look up.

        Returns:
            A copy of the successful params dict, or ``None`` if the
            paragraph has not been completed.
        """
        for ticket in self._tickets.values():
            if (
                isinstance(ticket, ParagraphTicket)
                and ticket.paragraph == paragraph
                and ticket.status == DONE
                and ticket.successful_params
            ):
                return dict(ticket.successful_params)
        return None

    def get_params_for_call_path(
        self, call_path: list[str]
    ) -> list[tuple[str, dict]]:
        """Get successful params for each completed paragraph in a call path.

        Args:
            call_path: Ordered list of paragraph names.

        Returns:
            A list of ``(paragraph_name, params_dict)`` tuples for each
            paragraph in the call path that has been completed.
        """
        results: list[tuple[str, dict]] = []
        for para in call_path:
            params = self.get_successful_params(para)
            if params:
                results.append((para, params))
        return results

    # ------------------------------------------------------------------
    # JSON persistence
    # ------------------------------------------------------------------

    def save(self, path: Path | str) -> None:
        """Persist current state to a JSON file.

        Each ticket is serialised via ``dataclasses.asdict`` with an
        additional ``_type`` discriminator so we can deserialise correctly.

        Args:
            path: Filesystem path for the JSON file.
        """
        path = Path(path)
        records: list[dict] = []
        for ticket in self._tickets.values():
            data = asdict(ticket)
            data["_type"] = type(ticket).__name__
            records.append(data)

        path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        logger.info("Saved %d tickets to %s", len(records), path)

    def load(self, path: Path | str) -> None:
        """Load tickets from a JSON file, applying crash-recovery resets.

        Tickets in CLAIMED or IN_PROGRESS status are reset to CREATED so
        that interrupted work is retried on restart.  The ``assigned_agent``
        field is also cleared for those tickets.

        Args:
            path: Filesystem path to read from.

        Raises:
            FileNotFoundError: If *path* does not exist.
        """
        path = Path(path)
        raw: list[dict] = json.loads(path.read_text(encoding="utf-8"))
        self._tickets.clear()

        for data in raw:
            ticket = self._deserialize(data)
            # Crash recovery: reset in-flight tickets
            if ticket.status in (CLAIMED, IN_PROGRESS):
                ticket.status = CREATED
                ticket.assigned_agent = None
            self._tickets[ticket.id] = ticket

        logger.info(
            "Loaded %d tickets from %s (crash-recovery applied)",
            len(self._tickets),
            path,
        )

    def load_or_create(self, path: Path | str) -> None:
        """Load from *path* if it exists, otherwise start with an empty store.

        Args:
            path: Filesystem path to attempt loading from.
        """
        path = Path(path)
        if path.exists():
            self.load(path)
        else:
            self._tickets.clear()
            logger.info("No existing tickets at %s — starting fresh", path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _deserialize(data: dict) -> Ticket:
        """Reconstruct a Ticket from a dict produced by ``save``.

        The ``_type`` key is used to select the correct dataclass.
        """
        type_name = data.pop("_type", None)
        if type_name == "ParagraphTicket":
            return ParagraphTicket(**data)
        if type_name == "BranchTicket":
            return BranchTicket(**data)
        raise ValueError(f"Unknown ticket type: {type_name!r}")
