"""Causal stub fingerprinting for branch coverage.

Observes which (position, fault_value) perturbations in the FIFO mock
data flip which branch directions, building a causal map that the LLM
can use to generate targeted parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PerturbationResult:
    """Result of a single stub perturbation during the position sweep.

    Attributes:
        position: FIFO position that was perturbed (-1 for baseline).
        fault_value: Value injected at that position ("" for baseline).
        branch_directions: All ``"branch_id:direction"`` strings observed.
        variable_snapshots: ``@@V:`` data keyed by branch_id.
        paragraphs_hit: Paragraphs entered during this execution.
    """

    position: int
    fault_value: str
    branch_directions: set[str]
    variable_snapshots: dict[str, dict[str, str]]
    paragraphs_hit: set[str]


@dataclass
class StubFingerprint:
    """Causal map from stub perturbations to branch effects.

    Built after the position-aware sweep by comparing each perturbation's
    branch outcomes against the baseline.

    Attributes:
        baseline: The unperturbed execution result.
        perturbations: All perturbation results collected during the sweep.
        branch_triggers: Maps ``"branch_id:direction"`` to the list of
            ``(position, fault_value)`` perturbations that produced it.
        variable_diffs: Maps ``branch_id`` to a dict of variable names
            whose values differ between baseline and the first perturbation
            that changed this branch.  Values are ``(baseline_val, new_val)``.
        branch_side_effects: Maps ``(position, fault_value)`` to the set
            of ``"branch_id:direction"`` strings that changed (appeared or
            disappeared) relative to baseline.
        mock_ops: Operation names from the baseline FIFO cycle, used to
            label positions with human-readable names.
    """

    baseline: PerturbationResult
    perturbations: list[PerturbationResult]
    branch_triggers: dict[str, list[tuple[int, str]]] = field(
        default_factory=dict
    )
    variable_diffs: dict[str, dict[str, tuple[str, str]]] = field(
        default_factory=dict
    )
    branch_side_effects: dict[tuple[int, str], set[str]] = field(
        default_factory=dict
    )
    mock_ops: list[str] = field(default_factory=list)

    def get_triggers(
        self, branch_id: str, direction: str
    ) -> list[tuple[int, str]]:
        """Return perturbations that caused *branch_id* to take *direction*."""
        key = f"{branch_id}:{direction}"
        return list(self.branch_triggers.get(key, []))

    def get_side_effects(
        self, position: int, fault_value: str
    ) -> set[str]:
        """Return branch:direction pairs affected by this perturbation."""
        return set(self.branch_side_effects.get((position, fault_value), set()))

    def get_variable_diff(
        self, branch_id: str
    ) -> dict[str, tuple[str, str]]:
        """Return variable value differences at *branch_id* vs baseline."""
        return dict(self.variable_diffs.get(branch_id, {}))

    def op_name(self, position: int) -> str:
        """Return the operation name for a FIFO position, or ``pos N``."""
        if self.mock_ops and 0 <= position < len(self.mock_ops):
            return self.mock_ops[position]
        return f"pos {position}"


def build_fingerprint(
    baseline: PerturbationResult,
    perturbations: list[PerturbationResult],
    mock_ops: list[str] | None = None,
) -> StubFingerprint:
    """Build a :class:`StubFingerprint` by comparing perturbations to baseline.

    Args:
        baseline: Execution result with no faults injected.
        perturbations: Results from each ``(position, fault_value)`` sweep.
        mock_ops: Operation names for the FIFO cycle (for labelling).

    Returns:
        A fully analysed ``StubFingerprint``.
    """
    triggers: dict[str, list[tuple[int, str]]] = {}
    side_effects: dict[tuple[int, str], set[str]] = {}
    var_diffs: dict[str, dict[str, tuple[str, str]]] = {}

    for p in perturbations:
        # New branch directions not in baseline
        new_dirs = p.branch_directions - baseline.branch_directions
        for d in new_dirs:
            triggers.setdefault(d, []).append((p.position, p.fault_value))

        # All changes (symmetric difference) for side-effect tracking
        changed = p.branch_directions.symmetric_difference(
            baseline.branch_directions
        )
        if changed:
            side_effects[(p.position, p.fault_value)] = changed

        # Variable snapshot diffs at each branch point
        for bid, snap in p.variable_snapshots.items():
            base_snap = baseline.variable_snapshots.get(bid, {})
            diffs: dict[str, tuple[str, str]] = {}
            for var, val in snap.items():
                base_val = base_snap.get(var, "")
                if val != base_val:
                    diffs[var] = (base_val, val)
            if diffs and bid not in var_diffs:
                var_diffs[bid] = diffs

    return StubFingerprint(
        baseline=baseline,
        perturbations=perturbations,
        branch_triggers=triggers,
        variable_diffs=var_diffs,
        branch_side_effects=side_effects,
        mock_ops=list(mock_ops) if mock_ops else [],
    )
