"""Coverage tracking for the COBOL penetration agent system.

Tracks which paragraphs and branches have been exercised, computes
cumulative coverage percentage, and persists state to JSON for
resume and reporting.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from cobol_penetrator.mock_reader import ProgramStructure
from cobol_penetrator.trace_parser import ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class CoverageState:
    """Snapshot of coverage metrics.

    Attributes:
        total_paragraphs: Number of paragraphs in the program structure.
        hit_paragraphs: Paragraph names that have been executed.
        total_branches: Total number of branch directions in the program.
        hit_branches: Mapping of branch ID to direction for branches hit.
        coverage_pct: Combined coverage percentage (paragraphs + branches).
        history: List of ``{"iteration": int, "coverage_pct": float}`` dicts
            recording coverage after each successful execution.
    """

    total_paragraphs: int = 0
    hit_paragraphs: list[str] = field(default_factory=list)
    total_branches: int = 0
    hit_branches: dict[str, str] = field(default_factory=dict)
    coverage_pct: float = 0.0
    history: list[dict] = field(default_factory=list)


class CoverageTracker:
    """Tracks paragraph and branch coverage across execution iterations.

    Coverage is computed as the ratio of (hit paragraphs + hit branch
    directions) to (total paragraphs + total branch directions). This
    combined metric captures both paragraph reachability and branch
    direction diversity.

    Args:
        structure: The parsed program structure providing totals.
    """

    def __init__(self, structure: ProgramStructure) -> None:
        # Count total branch directions (each direction is a target).
        total_branch_directions = sum(
            len(branch_info.directions)
            for branch_info in structure.branches.values()
        )

        self.state = CoverageState(
            total_paragraphs=len(structure.paragraphs),
            total_branches=total_branch_directions,
        )
        self._iteration = 0

    def update(self, result: ExecutionResult) -> None:
        """Incorporate an execution result into the coverage state.

        Newly hit paragraphs and branch directions are added (duplicates
        are ignored). Coverage percentage is recalculated and the new
        value is appended to the history.

        Args:
            result: The execution result to incorporate.
        """
        # Add newly hit paragraphs.
        for para in result.paragraphs_hit:
            if para not in self.state.hit_paragraphs:
                self.state.hit_paragraphs.append(para)

        # Add newly hit branch directions.
        # The key in hit_branches is "<branch_id>:<direction>" to track
        # each direction independently. A single branch ID can have
        # both T and F hit in different executions.
        for branch_id, direction in result.branches_hit.items():
            composite_key = f"{branch_id}:{direction}"
            if composite_key not in self.state.hit_branches:
                self.state.hit_branches[composite_key] = direction

        # Recalculate coverage.
        self.state.coverage_pct = self._calculate_pct()

        # Record history.
        self._iteration += 1
        self.state.history.append({
            "iteration": self._iteration,
            "coverage_pct": self.state.coverage_pct,
        })

        logger.debug(
            "Coverage update: paragraphs=%d/%d, branches=%d/%d, pct=%.1f%%",
            len(self.state.hit_paragraphs),
            self.state.total_paragraphs,
            len(self.state.hit_branches),
            self.state.total_branches,
            self.state.coverage_pct,
        )

    @property
    def coverage_pct(self) -> float:
        """Current coverage percentage (0.0 to 100.0)."""
        return self.state.coverage_pct

    def _calculate_pct(self) -> float:
        """Compute the combined coverage percentage.

        Returns:
            The coverage as a float between 0.0 and 100.0.
            Returns 0.0 if there are no paragraphs or branches to cover.
        """
        total = self.state.total_paragraphs + self.state.total_branches
        if total == 0:
            return 0.0
        hit = len(self.state.hit_paragraphs) + len(self.state.hit_branches)
        return round((hit / total) * 100.0, 2)

    def save(self, path: Path) -> None:
        """Write the coverage state to a JSON file.

        Creates parent directories if they do not exist.

        Args:
            path: Filesystem path for the JSON output.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "total_paragraphs": self.state.total_paragraphs,
            "hit_paragraphs": self.state.hit_paragraphs,
            "total_branches": self.state.total_branches,
            "hit_branches": self.state.hit_branches,
            "coverage_pct": self.state.coverage_pct,
            "history": self.state.history,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Coverage saved to %s (%.1f%%)", path, self.state.coverage_pct)

    @classmethod
    def load(cls, path: Path, structure: ProgramStructure) -> CoverageTracker:
        """Load a CoverageTracker from a previously saved JSON file.

        The loaded state is applied to a new tracker initialized from
        the given structure. The iteration counter is restored from the
        history length.

        Args:
            path: Filesystem path to the saved JSON file.
            structure: The program structure (used for totals).

        Returns:
            A CoverageTracker with restored state.

        Raises:
            FileNotFoundError: If *path* does not exist.
        """
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))

        tracker = cls(structure)
        tracker.state.hit_paragraphs = data.get("hit_paragraphs", [])
        tracker.state.hit_branches = data.get("hit_branches", {})
        tracker.state.coverage_pct = data.get("coverage_pct", 0.0)
        tracker.state.history = data.get("history", [])
        tracker._iteration = len(tracker.state.history)

        logger.info(
            "Coverage loaded from %s (%.1f%%, %d iterations)",
            path,
            tracker.state.coverage_pct,
            tracker._iteration,
        )
        return tracker
