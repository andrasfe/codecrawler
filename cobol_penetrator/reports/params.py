"""Successful parameters documentation.

Saves the input parameters that successfully reached a ticket's target
to individual JSON files for traceability and replay.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from cobol_penetrator.tickets.models import Ticket

logger = logging.getLogger(__name__)


def save_successful_params(
    ticket: Ticket,
    params: dict,
    output_dir: Path,
) -> Path:
    """Save successful parameters for a ticket as a JSON file.

    The file is named ``<ticket.id>.json`` and contains the ticket ID,
    ticket type, and the parameters that achieved the target.

    Args:
        ticket: The ticket that was successfully completed.
        params: The input parameters (``input_state`` and ``stubs``) that
            achieved the ticket's target.
        output_dir: Directory in which to write the JSON file.

    Returns:
        The path of the written file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sanitise ticket ID for filesystem safety.
    safe_id = ticket.id.replace("/", "_").replace("\\", "_")
    file_path = output_dir / f"{safe_id}.json"

    data = {
        "ticket_id": ticket.id,
        "ticket_type": type(ticket).__name__,
        "params": params,
    }

    file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.debug("Saved successful params for %s to %s", ticket.id, file_path)
    return file_path
