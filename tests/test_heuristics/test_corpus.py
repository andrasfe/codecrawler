"""Tests for cobol_penetrator.heuristics.corpus."""

from __future__ import annotations

from random import Random

from cobol_penetrator.heuristics.corpus import Corpus, CorpusEntry


def _make_entry(
    paras: set[str] | None = None,
    branches: set[str] | None = None,
    input_state: dict | None = None,
    stubs: dict | None = None,
    energy: float = 1.0,
) -> CorpusEntry:
    """Helper to construct a CorpusEntry with defaults."""
    return CorpusEntry(
        input_state=input_state or {},
        stubs=stubs or {},
        paragraphs_hit=frozenset(paras or set()),
        branches_hit=frozenset(branches or set()),
        energy=energy,
    )


class TestCorpusEntry:
    """CorpusEntry dataclass basics."""

    def test_defaults(self) -> None:
        entry = CorpusEntry(input_state={}, stubs={})
        assert entry.paragraphs_hit == frozenset()
        assert entry.branches_hit == frozenset()
        assert entry.energy == 1.0
        assert entry.mutation_count == 0
        assert entry.added_at == 0

    def test_custom_coverage(self) -> None:
        entry = _make_entry(paras={"A", "B"}, branches={"1:T"})
        assert "A" in entry.paragraphs_hit
        assert "1:T" in entry.branches_hit


class TestShouldAdd:
    """Test Corpus.should_add — new coverage detection."""

    def test_new_paragraph_should_add(self) -> None:
        corpus = Corpus()
        entry = _make_entry(paras={"1000-MAIN"})
        assert corpus.should_add(entry) is True

    def test_duplicate_paragraph_should_not_add(self) -> None:
        corpus = Corpus()
        entry1 = _make_entry(paras={"1000-MAIN"})
        corpus.add(entry1)

        entry2 = _make_entry(paras={"1000-MAIN"})
        assert corpus.should_add(entry2) is False

    def test_new_branch_should_add(self) -> None:
        corpus = Corpus()
        entry1 = _make_entry(paras={"A"})
        corpus.add(entry1)

        entry2 = _make_entry(branches={"1:T"})
        assert corpus.should_add(entry2) is True

    def test_subset_coverage_should_not_add(self) -> None:
        corpus = Corpus()
        entry1 = _make_entry(paras={"A", "B"}, branches={"1:T"})
        corpus.add(entry1)

        entry2 = _make_entry(paras={"A"}, branches={"1:T"})
        assert corpus.should_add(entry2) is False

    def test_empty_coverage_should_not_add(self) -> None:
        corpus = Corpus()
        entry = _make_entry()
        assert corpus.should_add(entry) is False

    def test_partial_new_coverage_should_add(self) -> None:
        corpus = Corpus()
        entry1 = _make_entry(paras={"A"})
        corpus.add(entry1)

        entry2 = _make_entry(paras={"A", "B"})
        assert corpus.should_add(entry2) is True


class TestAdd:
    """Test Corpus.add — adding entries and global coverage tracking."""

    def test_add_returns_true_for_new_coverage(self) -> None:
        corpus = Corpus()
        entry = _make_entry(paras={"A"})
        assert corpus.add(entry) is True

    def test_add_returns_false_for_no_new_coverage(self) -> None:
        corpus = Corpus()
        entry1 = _make_entry(paras={"A"})
        corpus.add(entry1)
        entry2 = _make_entry(paras={"A"})
        assert corpus.add(entry2) is False

    def test_add_updates_global_paragraphs(self) -> None:
        corpus = Corpus()
        corpus.add(_make_entry(paras={"A", "B"}))
        assert corpus.global_paragraphs == {"A", "B"}

    def test_add_updates_global_branches(self) -> None:
        corpus = Corpus()
        corpus.add(_make_entry(branches={"1:T", "2:F"}))
        assert corpus.global_branches == {"1:T", "2:F"}

    def test_add_increments_iteration(self) -> None:
        corpus = Corpus()
        e1 = _make_entry(paras={"A"})
        e2 = _make_entry(paras={"B"})
        corpus.add(e1)
        corpus.add(e2)
        assert e1.added_at == 1
        assert e2.added_at == 2

    def test_add_multiple_entries(self) -> None:
        corpus = Corpus()
        corpus.add(_make_entry(paras={"A"}))
        corpus.add(_make_entry(paras={"B"}))
        corpus.add(_make_entry(paras={"C"}))
        assert len(corpus.entries) == 3
        assert corpus.global_paragraphs == {"A", "B", "C"}

    def test_add_triggers_eviction_at_max_size(self) -> None:
        corpus = Corpus(max_size=3)
        # Add 4 entries, each covering a different paragraph
        corpus.add(_make_entry(paras={"A"}))
        corpus.add(_make_entry(paras={"B"}))
        corpus.add(_make_entry(paras={"C"}))
        # 4th should trigger eviction
        corpus.add(_make_entry(paras={"D"}))
        assert len(corpus.entries) <= 3


class TestSelectSeed:
    """Test Corpus.select_seed — energy-weighted selection."""

    def test_empty_corpus_returns_none(self) -> None:
        corpus = Corpus()
        rng = Random(42)
        assert corpus.select_seed(rng) is None

    def test_single_entry_always_selected(self) -> None:
        corpus = Corpus()
        entry = _make_entry(paras={"A"})
        corpus.add(entry)
        rng = Random(42)
        for _ in range(10):
            assert corpus.select_seed(rng) is entry

    def test_higher_energy_selected_more_often(self) -> None:
        corpus = Corpus()
        low = _make_entry(paras={"A"}, energy=0.1)
        high = _make_entry(paras={"B"}, energy=10.0)
        corpus.add(low)
        corpus.add(high)

        rng = Random(42)
        counts = {id(low): 0, id(high): 0}
        for _ in range(1000):
            selected = corpus.select_seed(rng)
            counts[id(selected)] += 1

        assert counts[id(high)] > counts[id(low)]

    def test_zero_energy_falls_back_to_random(self) -> None:
        corpus = Corpus()
        e1 = _make_entry(paras={"A"}, energy=0.0)
        e2 = _make_entry(paras={"B"}, energy=0.0)
        corpus.add(e1)
        corpus.add(e2)

        rng = Random(42)
        result = corpus.select_seed(rng)
        assert result in (e1, e2)

    def test_deterministic_with_seed(self) -> None:
        corpus = Corpus()
        corpus.add(_make_entry(paras={"A"}, energy=1.0))
        corpus.add(_make_entry(paras={"B"}, energy=1.0))
        corpus.add(_make_entry(paras={"C"}, energy=1.0))

        result1 = corpus.select_seed(Random(99))
        result2 = corpus.select_seed(Random(99))
        assert result1 is result2


class TestUpdateEnergy:
    """Test Corpus.update_energy — rarity-based energy calculation."""

    def test_empty_corpus_no_error(self) -> None:
        corpus = Corpus()
        corpus.update_energy()  # Should not raise

    def test_single_entry_gets_energy(self) -> None:
        corpus = Corpus()
        entry = _make_entry(paras={"A"})
        corpus.add(entry)
        corpus.update_energy()
        assert entry.energy > 0

    def test_rare_coverage_gets_higher_energy(self) -> None:
        corpus = Corpus()
        # Both cover "A", but only e2 covers "B" (which is rare)
        e1 = _make_entry(paras={"A"})
        e2 = _make_entry(paras={"A", "B"})
        corpus.add(e1)
        corpus.add(e2)
        corpus.update_energy()
        # e2 covers "B" (unique to it), so it should have more energy
        assert e2.energy > e1.energy

    def test_all_shared_coverage_equal_energy(self) -> None:
        corpus = Corpus()
        e1 = _make_entry(paras={"A"})
        e2 = _make_entry(paras={"A", "B"})
        e3 = _make_entry(paras={"B"})
        corpus.add(e1)
        corpus.add(e2)
        corpus.add(e3)
        corpus.update_energy()
        # e2 covers both A and B (each shared by 2 entries) -> 0.5 + 0.5 = 1.0
        # e1 covers A (shared by 2) -> 0.5
        # e3 covers B (shared by 2) -> 0.5
        assert e2.energy > e1.energy
        assert e2.energy > e3.energy

    def test_minimum_energy_enforced(self) -> None:
        corpus = Corpus()
        # Entry with no coverage should still get minimum energy
        entry = _make_entry(paras={"X"})
        corpus.add(entry)
        corpus.update_energy()
        assert entry.energy >= 0.01


class TestEvict:
    """Test Corpus.evict — removing lowest-energy redundant entries."""

    def test_single_entry_not_evicted(self) -> None:
        corpus = Corpus()
        entry = _make_entry(paras={"A"})
        corpus.add(entry)
        corpus.evict()
        assert len(corpus.entries) == 1

    def test_redundant_entry_evicted(self) -> None:
        corpus = Corpus(max_size=2)
        # e1 covers {A}, e2 covers {A, B}, e3 covers {B}
        e1 = _make_entry(paras={"A"}, energy=0.1)
        e2 = _make_entry(paras={"A", "B"}, energy=5.0)
        e3 = _make_entry(paras={"B"}, energy=0.2)
        corpus.add(e1)
        corpus.add(e2)
        corpus.add(e3)
        # Force eviction
        corpus.evict()
        # e1 is redundant (A is also covered by e2) and lowest energy
        assert e1 not in corpus.entries

    def test_non_redundant_lowest_energy_evicted(self) -> None:
        corpus = Corpus(max_size=2)
        # Each covers unique paragraphs only, so none are redundant
        e1 = _make_entry(paras={"A"}, energy=0.1)
        e2 = _make_entry(paras={"B"}, energy=5.0)
        corpus.add(e1)
        corpus.add(e2)
        corpus.evict()
        # Lowest energy is removed
        assert e1 not in corpus.entries
        assert e2 in corpus.entries

    def test_eviction_preserves_unique_coverage(self) -> None:
        corpus = Corpus(max_size=3)
        e1 = _make_entry(paras={"A"}, energy=10.0)
        e2 = _make_entry(paras={"A", "B"}, energy=5.0)
        e3 = _make_entry(paras={"C"}, energy=1.0)
        corpus.add(e1)
        corpus.add(e2)
        corpus.add(e3)
        corpus.evict()
        # e1 is redundant (A covered by e2) and should be evicted
        # despite higher energy, e1 is lowest-energy redundant
        # Actually: e1 has energy=10 and e2 has energy=5.
        # Sorted by energy: e3(1), e2(5), e1(10)
        # e3 is not redundant (C unique), e2 is not redundant (B unique)
        # e1 IS redundant (A covered by e2) -> e1 evicted? No: we iterate
        # lowest-energy first. e3 covers {C} which has count 1 -> not redundant.
        # e2 covers {A,B}: A has count 2, B has count 1 -> not redundant.
        # e1 covers {A}: A has count 2 -> redundant. e1 evicted.
        assert e1 not in corpus.entries
        assert e2 in corpus.entries
        assert e3 in corpus.entries


class TestCorpusMaxSize:
    """Test the max_size property."""

    def test_default_max_size(self) -> None:
        corpus = Corpus()
        assert corpus.max_size == 500

    def test_custom_max_size(self) -> None:
        corpus = Corpus(max_size=10)
        assert corpus.max_size == 10
