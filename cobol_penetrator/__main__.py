"""CLI entry point for cobol-penetrator.

Usage:
    # Run penetration
    python -m cobol_penetrator \\
        --executable .specter_build_RCO100B/RCO100B \\
        --mock-cbl .specter_build_RCO100B/RCO100B.mock.cbl \\
        --budget 10000 --timeout 3600

    # Resume from prior run
    python -m cobol_penetrator \\
        --executable .specter_build_RCO100B/RCO100B \\
        --mock-cbl .specter_build_RCO100B/RCO100B.mock.cbl \\
        --resume

    # Status report
    python -m cobol_penetrator --status --tickets-path .tickets.json
    
    # Restart (clear all state and start fresh with execution)  
    python -m cobol_penetrator --restart \\
        --executable .specter_build_RCO100B/RCO100B \\
        --mock-cbl .specter_build_RCO100B/RCO100B.mock.cbl \\
        --budget 100 --timeout 300
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path

from cobol_penetrator.config import load_config

logger = logging.getLogger(__name__)


def restart_clean(config) -> None:
    """Clear all state files and directories to start fresh.
    
    Removes:
    - Ticket store (.tickets.json)
    - Knowledge store (.knowledge.json)
    - Reports directory (reports/)
    - EvoSkill data directory (evoskill_data/)
    
    Args:
        config: The penetrator configuration with file paths.
    """
    cleaned = []
    
    # Remove ticket store
    if config.tickets_path.exists():
        config.tickets_path.unlink()
        cleaned.append(str(config.tickets_path))
    
    # Remove knowledge store
    if config.knowledge_path.exists():
        config.knowledge_path.unlink()
        cleaned.append(str(config.knowledge_path))
    
    # Remove reports directory
    reports_dir = config.coverage_path.parent
    if reports_dir.exists() and reports_dir.name == "reports":
        shutil.rmtree(reports_dir)
        cleaned.append(str(reports_dir))
    
    # Remove EvoSkill data directory
    if config.evoskill_path.exists():
        shutil.rmtree(config.evoskill_path)
        cleaned.append(str(config.evoskill_path))
    
    print("=== COBOL Penetrator Restart ===")
    if cleaned:
        print("Cleaned state files and directories:")
        for item in cleaned:
            print(f"  - {item}")
    else:
        print("No state files found to clean.")
    print("Ready to start fresh!")


def show_status(config) -> None:
    """Show current ticket and coverage status.

    Reads the ticket store and (if available) the coverage file, then
    prints a human-readable summary to stdout.

    Args:
        config: The penetrator configuration with file paths.
    """
    from cobol_penetrator.tickets import TicketStore

    store = TicketStore()
    store.load_or_create(config.tickets_path)
    tickets = store.all_tickets()

    # Count by status.
    status_counts: dict[str, int] = {}
    for t in tickets:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1

    print("=== COBOL Penetrator Status ===")
    print(f"Tickets file: {config.tickets_path}")
    print(f"Total tickets: {len(tickets)}")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    # Show coverage if available.
    coverage_path = Path(config.coverage_path)
    if coverage_path.exists():
        data = json.loads(coverage_path.read_text(encoding="utf-8"))
        print(f"\nCoverage: {data.get('coverage_pct', 0.0):.1f}%")
        print(
            f"  Paragraphs hit: {len(data.get('hit_paragraphs', []))}"
            f"/{data.get('total_paragraphs', 0)}"
        )
        print(
            f"  Branches hit: {len(data.get('hit_branches', {}))}"
            f"/{data.get('total_branches', 0)}"
        )
        history = data.get("history", [])
        if history:
            print(f"  Iterations: {len(history)}")
    else:
        print(f"\nNo coverage data at {coverage_path}")


def main() -> None:
    """Main entry point for the cobol-penetrator CLI."""
    # Configure logging before anything else.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    # Check for --status or --restart in sys.argv before argparse consumes it,
    # so we can handle them without requiring --executable / --mock-cbl.
    if "--status" in sys.argv:
        config = load_config()
        show_status(config)
        return
    
    config = load_config()

    if config.restart:
        restart_clean(config)

    if not config.executable.exists():
        print(
            f"Error: executable not found: {config.executable}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not config.mock_cbl.exists():
        print(
            f"Error: mock.cbl not found: {config.mock_cbl}",
            file=sys.stderr,
        )
        sys.exit(1)

    from cobol_penetrator.orchestrator import run

    result = asyncio.run(run(config))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
