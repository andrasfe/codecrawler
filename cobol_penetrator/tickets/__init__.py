"""Ticket system — data models, in-memory store, and state-machine engine.

Public API
----------
Models:
    ParagraphTicket, BranchTicket, Ticket

Status constants:
    CREATED, CLAIMED, IN_PROGRESS, DONE, BLOCKED

Store:
    TicketStore, DuplicateTicketError, TicketNotFoundError

Engine:
    TicketEngine, InvalidTransitionError
"""

from .engine import InvalidTransitionError, TicketEngine
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
from .store import DuplicateTicketError, TicketNotFoundError, TicketStore

__all__ = [
    # Models
    "ParagraphTicket",
    "BranchTicket",
    "Ticket",
    # Status constants
    "CREATED",
    "CLAIMED",
    "IN_PROGRESS",
    "DONE",
    "BLOCKED",
    # Store
    "TicketStore",
    "DuplicateTicketError",
    "TicketNotFoundError",
    # Engine
    "TicketEngine",
    "InvalidTransitionError",
]
