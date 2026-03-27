"""Coverage-guided corpus management for the heuristic walker.

Maintains a set of interesting test inputs (corpus entries) that each
contribute unique coverage. Provides energy-weighted seed selection
and eviction of redundant entries when the corpus grows too large.

This is a simplified port of the corpus management in specter's
monte_carlo module, adapted for the coverage penetration agent system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random


@dataclass
class CorpusEntry:
    """A single corpus entry representing an executed test case.

    Attributes:
        input_state: Variable name-to-value mapping used as input.
        stubs: Stub operation outcomes used for this test case.
        paragraphs_hit: Set of paragraph names reached.
        branches_hit: Set of branch identifiers reached.
        energy: Selection weight — higher means more likely to be
            chosen as a mutation seed.
        mutation_count: How many times this entry has been mutated.
        added_at: Iteration number when this entry was added.
    """

    input_state: dict
    stubs: dict
    paragraphs_hit: frozenset[str] = field(default_factory=frozenset)
    branches_hit: frozenset[str] = field(default_factory=frozenset)
    energy: float = 1.0
    mutation_count: int = 0
    added_at: int = 0


class Corpus:
    """Coverage-guided corpus for interesting test inputs.

    Tracks global coverage (paragraphs and branches) and only admits
    entries that contribute previously unseen coverage. Uses
    energy-weighted selection to bias mutation toward entries that
    cover rare paths.

    Args:
        max_size: Maximum number of entries before eviction triggers.
    """

    def __init__(self, max_size: int = 500) -> None:
        self.entries: list[CorpusEntry] = []
        self.global_paragraphs: set[str] = set()
        self.global_branches: set[str] = set()
        self._iteration: int = 0
        self._max_size: int = max_size

    @property
    def max_size(self) -> int:
        """Return the maximum corpus size (set at init via __init__ default)."""
        return self._max_size

    def should_add(self, entry: CorpusEntry) -> bool:
        """Check if entry covers paragraphs or branches not yet in global coverage.

        Args:
            entry: The candidate corpus entry.

        Returns:
            True if the entry contributes at least one new paragraph
            or branch to global coverage.
        """
        new_paras = entry.paragraphs_hit - self.global_paragraphs
        new_branches = entry.branches_hit - self.global_branches
        return bool(new_paras or new_branches)

    def add(self, entry: CorpusEntry) -> bool:
        """Add entry if it provides new coverage.

        Updates global coverage sets and triggers eviction if the
        corpus exceeds max_size.

        Args:
            entry: The corpus entry to add.

        Returns:
            True if the entry was added, False if it provided no
            new coverage.
        """
        if not self.should_add(entry):
            return False

        self._iteration += 1
        entry.added_at = self._iteration
        self.entries.append(entry)
        self.global_paragraphs.update(entry.paragraphs_hit)
        self.global_branches.update(entry.branches_hit)

        if len(self.entries) > self._max_size:
            self.evict()

        return True

    def select_seed(self, rng: Random) -> CorpusEntry | None:
        """Select a seed entry weighted by energy.

        Higher-energy entries are more likely to be selected. If the
        corpus is empty, returns None.

        Args:
            rng: Random number generator.

        Returns:
            A corpus entry, or None if the corpus is empty.
        """
        if not self.entries:
            return None

        total = sum(e.energy for e in self.entries)
        if total <= 0:
            return rng.choice(self.entries)

        r = rng.random() * total
        cumulative = 0.0
        for entry in self.entries:
            cumulative += entry.energy
            if cumulative >= r:
                return entry

        return self.entries[-1]

    def update_energy(self) -> None:
        """Recalculate energy for all entries.

        Entries covering rare paragraphs or branches (those covered by
        fewer corpus entries) receive higher energy. This biases seed
        selection toward inputs that explore less-traveled paths.
        """
        if not self.entries:
            return

        # Count how many entries cover each paragraph and branch
        para_counts: dict[str, int] = {}
        branch_counts: dict[str, int] = {}

        for entry in self.entries:
            for p in entry.paragraphs_hit:
                para_counts[p] = para_counts.get(p, 0) + 1
            for b in entry.branches_hit:
                branch_counts[b] = branch_counts.get(b, 0) + 1

        # Energy = sum of inverse frequency for each covered element
        for entry in self.entries:
            energy = 0.0
            for p in entry.paragraphs_hit:
                count = para_counts.get(p, 1)
                energy += 1.0 / count
            for b in entry.branches_hit:
                count = branch_counts.get(b, 1)
                energy += 1.0 / count
            # Ensure minimum energy so no entry is completely ignored
            entry.energy = max(energy, 0.01)

    def evict(self) -> None:
        """Remove lowest-energy entry whose coverage is redundantly covered.

        Uses a coverage reference-count approach: an entry is
        redundant if every paragraph and branch it covers is also
        covered by at least one other entry. Among redundant entries,
        the one with lowest energy is removed. If no entry is fully
        redundant, the lowest-energy entry is removed unconditionally.
        """
        if len(self.entries) <= 1:
            return

        # Build coverage counters
        para_counts: dict[str, int] = {}
        branch_counts: dict[str, int] = {}

        for entry in self.entries:
            for p in entry.paragraphs_hit:
                para_counts[p] = para_counts.get(p, 0) + 1
            for b in entry.branches_hit:
                branch_counts[b] = branch_counts.get(b, 0) + 1

        # Sort indices by energy (lowest first)
        candidates = sorted(
            range(len(self.entries)),
            key=lambda i: self.entries[i].energy,
        )

        # Try to evict the lowest-energy redundant entry
        for idx in candidates:
            entry = self.entries[idx]
            paras_redundant = all(
                para_counts.get(p, 0) > 1 for p in entry.paragraphs_hit
            )
            branches_redundant = all(
                branch_counts.get(b, 0) > 1 for b in entry.branches_hit
            )
            if paras_redundant and branches_redundant:
                self.entries.pop(idx)
                return

        # No redundant entry found — drop lowest energy unconditionally
        self.entries.pop(candidates[0])
