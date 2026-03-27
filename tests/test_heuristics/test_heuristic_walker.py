"""Tests for cobol_penetrator.heuristics.heuristic_walker."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from cobol_penetrator.heuristics.heuristic_walker import HeuristicWalker


# ---------------------------------------------------------------------------
# Mock objects
# ---------------------------------------------------------------------------


@dataclass
class MockDomain:
    """Test stand-in for VariableDomainLike."""

    name: str = "WS-TEST"
    data_type: str = "alpha"
    max_length: int = 10
    precision: int = 0
    signed: bool = False
    min_value: int | float | None = None
    max_value: int | float | None = None
    condition_literals: list = field(default_factory=list)
    valid_88_values: dict[str, str] = field(default_factory=dict)
    classification: str = "data"
    semantic_type: str = ""


@dataclass
class MockFieldReport:
    """Test stand-in for a FieldReport-like object."""

    fields: dict = field(default_factory=dict)
    condition_hints: dict = field(default_factory=dict)
    stub_operations: list = field(default_factory=list)
    stub_variables: dict = field(default_factory=dict)


@dataclass
class MockResult:
    """Test stand-in for ExecutionResult."""

    paragraphs_hit: list = field(default_factory=list)
    branches_hit: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_report() -> MockFieldReport:
    """Build a realistic mock field report with several variables."""
    return MockFieldReport(
        fields={
            "WS-STATUS": MockDomain(
                name="WS-STATUS",
                data_type="alpha",
                max_length=2,
                classification="status",
                semantic_type="status_file",
                condition_literals=["00", "10", "23"],
            ),
            "WS-AMOUNT": MockDomain(
                name="WS-AMOUNT",
                data_type="numeric",
                max_length=9,
                precision=2,
                min_value=0.0,
                max_value=999999.99,
                classification="data",
                semantic_type="amount",
            ),
            "WS-FLAG": MockDomain(
                name="WS-FLAG",
                data_type="alpha",
                max_length=1,
                classification="flag",
                semantic_type="flag_bool",
                valid_88_values={"YES": "Y", "NO": "N"},
                condition_literals=["Y", "N"],
            ),
            "WS-DATE": MockDomain(
                name="WS-DATE",
                data_type="numeric",
                max_length=8,
                classification="data",
                semantic_type="date",
            ),
            "WS-COUNTER": MockDomain(
                name="WS-COUNTER",
                data_type="numeric",
                max_length=3,
                min_value=0,
                max_value=999,
                classification="data",
                semantic_type="counter",
            ),
        },
        condition_hints={
            "1": {"vars": ["WS-STATUS"], "text": "WS-STATUS = '00'"},
        },
        stub_operations=["READ-ACCOUNT", "WRITE-LOG"],
        stub_variables={
            "READ-ACCOUNT": "status_file",
            "WRITE-LOG": "status_file",
        },
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    """Test HeuristicWalker initialization."""

    def test_default_construction(self) -> None:
        walker = HeuristicWalker()
        assert walker.field_report is None
        assert walker.rng is not None
        assert walker.corpus is not None

    def test_with_field_report(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report)
        assert walker.field_report is report

    def test_with_custom_rng(self) -> None:
        rng = Random(42)
        walker = HeuristicWalker(rng=rng)
        assert walker.rng is rng


# ---------------------------------------------------------------------------
# generate_initial_params
# ---------------------------------------------------------------------------


class TestGenerateInitialParams:
    """Test success-biased initial parameter generation."""

    def test_returns_input_state_and_stubs(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.generate_initial_params()
        assert "input_state" in params
        assert "stubs" in params

    def test_all_fields_populated(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.generate_initial_params()
        for name in report.fields:
            assert name in params["input_state"]

    def test_all_stubs_populated(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.generate_initial_params()
        for op in report.stub_operations:
            assert op in params["stubs"]

    def test_stubs_have_success_values(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.generate_initial_params()
        for op in report.stub_operations:
            stub = params["stubs"][op]
            assert stub["alpha_status"] == "00"

    def test_no_field_report_returns_empty(self) -> None:
        walker = HeuristicWalker(rng=Random(42))
        params = walker.generate_initial_params()
        assert params["input_state"] == {}
        assert params["stubs"] == {}

    def test_deterministic_with_seed(self) -> None:
        report = _build_report()
        w1 = HeuristicWalker(field_report=report, rng=Random(42))
        w2 = HeuristicWalker(field_report=report, rng=Random(42))
        assert w1.generate_initial_params() == w2.generate_initial_params()


# ---------------------------------------------------------------------------
# generate_exploratory_params
# ---------------------------------------------------------------------------


class TestGenerateExploratoryParams:
    """Test random domain-aware parameter generation."""

    def test_returns_input_state_and_stubs(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.generate_exploratory_params()
        assert "input_state" in params
        assert "stubs" in params

    def test_all_fields_populated(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.generate_exploratory_params()
        for name in report.fields:
            assert name in params["input_state"]

    def test_stubs_have_fault_values(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.generate_exploratory_params()
        for op in report.stub_operations:
            assert "alpha_status" in params["stubs"][op]

    def test_produces_variety(self) -> None:
        """Multiple calls should produce different params."""
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        results = [walker.generate_exploratory_params() for _ in range(10)]
        # At least some variation in input_state values
        unique_amounts = {
            str(r["input_state"].get("WS-AMOUNT")) for r in results
        }
        assert len(unique_amounts) > 1

    def test_no_field_report_returns_empty(self) -> None:
        walker = HeuristicWalker(rng=Random(42))
        params = walker.generate_exploratory_params()
        assert params["input_state"] == {}
        assert params["stubs"] == {}


# ---------------------------------------------------------------------------
# mutate_params
# ---------------------------------------------------------------------------


class TestMutateParams:
    """Test AFL-inspired mutation of parameters."""

    def test_returns_input_state_and_stubs(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        parent = walker.generate_initial_params()
        mutated = walker.mutate_params(parent)
        assert "input_state" in mutated
        assert "stubs" in mutated

    def test_mutation_changes_at_least_something(self) -> None:
        """Over many mutations, at least one should differ from parent."""
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        parent = walker.generate_initial_params()
        any_different = False
        for _ in range(20):
            mutated = walker.mutate_params(parent)
            if mutated != parent:
                any_different = True
                break
        assert any_different

    def test_mutation_preserves_keys(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        parent = walker.generate_initial_params()
        mutated = walker.mutate_params(parent)
        assert set(mutated["input_state"].keys()) == set(
            parent["input_state"].keys()
        )

    def test_parent_not_modified(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        parent = walker.generate_initial_params()
        original_state = dict(parent["input_state"])
        walker.mutate_params(parent)
        assert parent["input_state"] == original_state

    def test_empty_params_returns_empty(self) -> None:
        walker = HeuristicWalker(rng=Random(42))
        result = walker.mutate_params({"input_state": {}, "stubs": {}})
        assert result == {"input_state": {}, "stubs": {}}

    def test_stub_mutation_occurs(self) -> None:
        """Over many mutations, at least one should change stubs."""
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        parent = walker.generate_initial_params()
        original_stubs = dict(parent["stubs"])
        any_stub_change = False
        for _ in range(100):
            mutated = walker.mutate_params(parent)
            if mutated["stubs"] != original_stubs:
                any_stub_change = True
                break
        assert any_stub_change

    def test_crossover_works_with_corpus(self) -> None:
        """When corpus has entries, crossover mutation should use them."""
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        # Populate corpus with a few entries
        for i in range(5):
            params = walker.generate_exploratory_params()
            result = MockResult(
                paragraphs_hit=[f"PARA-{i}"],
                branches_hit={str(i): "T"},
            )
            walker.record_result(params, result)

        parent = walker.generate_initial_params()
        # Run many mutations — some should use crossover
        mutated_set = set()
        for _ in range(50):
            m = walker.mutate_params(parent)
            mutated_set.add(str(m["input_state"]))
        assert len(mutated_set) > 1


# ---------------------------------------------------------------------------
# suggest_params_for_branch
# ---------------------------------------------------------------------------


class TestSuggestParamsForBranch:
    """Test targeted branch parameter generation."""

    def test_returns_input_state_and_stubs(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.suggest_params_for_branch(
            branch_id="1",
            direction="T",
            condition_vars=["WS-STATUS"],
        )
        assert "input_state" in params
        assert "stubs" in params

    def test_condition_var_uses_literal(self) -> None:
        """If condition var has literals, one should be chosen."""
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.suggest_params_for_branch(
            branch_id="1",
            direction="T",
            condition_vars=["WS-STATUS"],
        )
        assert params["input_state"]["WS-STATUS"] in ["00", "10", "23"]

    def test_stubs_populated_with_success(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.suggest_params_for_branch(
            branch_id="1",
            direction="T",
            condition_vars=["WS-STATUS"],
        )
        for op in report.stub_operations:
            assert op in params["stubs"]

    def test_unknown_condition_var_ignored(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.suggest_params_for_branch(
            branch_id="1",
            direction="T",
            condition_vars=["NONEXISTENT-VAR"],
        )
        assert "NONEXISTENT-VAR" not in params["input_state"]

    def test_false_direction_uses_adversarial(self) -> None:
        """For False branch with no literals, adversarial values are used."""
        report = MockFieldReport(
            fields={
                "WS-AMOUNT": MockDomain(
                    name="WS-AMOUNT",
                    data_type="numeric",
                    max_length=9,
                    min_value=0,
                    max_value=999999999,
                    classification="data",
                    semantic_type="amount",
                ),
            },
            stub_operations=[],
        )
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        params = walker.suggest_params_for_branch(
            branch_id="5",
            direction="F",
            condition_vars=["WS-AMOUNT"],
        )
        # adversarial for numeric includes 0 and extreme values
        assert "WS-AMOUNT" in params["input_state"]

    def test_uses_corpus_seed_when_available(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))

        # Add a corpus entry
        params = walker.generate_initial_params()
        result = MockResult(
            paragraphs_hit=["1000-MAIN"],
            branches_hit={"1": "T"},
        )
        walker.record_result(params, result)

        suggested = walker.suggest_params_for_branch(
            branch_id="2",
            direction="T",
            condition_vars=["WS-FLAG"],
        )
        # Should have been seeded from the corpus entry
        assert "input_state" in suggested

    def test_no_field_report_returns_minimal(self) -> None:
        walker = HeuristicWalker(rng=Random(42))
        params = walker.suggest_params_for_branch(
            branch_id="1",
            direction="T",
            condition_vars=["WS-X"],
        )
        assert "input_state" in params
        assert "stubs" in params


# ---------------------------------------------------------------------------
# suggest_fault_sweep
# ---------------------------------------------------------------------------


class TestSuggestFaultSweep:
    """Test fault sweep generation for stub operations."""

    def test_returns_list_of_params(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        sweep = walker.suggest_fault_sweep("READ-ACCOUNT")
        assert isinstance(sweep, list)
        assert len(sweep) > 0

    def test_each_entry_has_different_fault(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        sweep = walker.suggest_fault_sweep("READ-ACCOUNT")
        fault_values = [
            s["stubs"]["READ-ACCOUNT"]["alpha_status"] for s in sweep
        ]
        assert len(set(fault_values)) == len(fault_values)

    def test_covers_all_file_status_codes(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        sweep = walker.suggest_fault_sweep("READ-ACCOUNT")
        fault_values = {
            s["stubs"]["READ-ACCOUNT"]["alpha_status"] for s in sweep
        }
        assert "00" in fault_values
        assert "10" in fault_values
        assert "23" in fault_values

    def test_unknown_stub_uses_file_status_fallback(self) -> None:
        report = MockFieldReport(
            fields={},
            stub_operations=["UNKNOWN-OP"],
            stub_variables={},
        )
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        sweep = walker.suggest_fault_sweep("UNKNOWN-OP")
        assert len(sweep) > 0

    def test_each_entry_has_input_state(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))
        sweep = walker.suggest_fault_sweep("READ-ACCOUNT")
        for params in sweep:
            assert "input_state" in params
            assert "stubs" in params

    def test_no_field_report_still_produces_sweep(self) -> None:
        walker = HeuristicWalker(rng=Random(42))
        sweep = walker.suggest_fault_sweep("SOME-OP")
        assert len(sweep) > 0


# ---------------------------------------------------------------------------
# record_result
# ---------------------------------------------------------------------------


class TestRecordResult:
    """Test execution result recording into corpus."""

    def test_new_coverage_returns_true(self) -> None:
        walker = HeuristicWalker(rng=Random(42))
        params = {"input_state": {"X": "1"}, "stubs": {}}
        result = MockResult(
            paragraphs_hit=["1000-MAIN"],
            branches_hit={"1": "T"},
        )
        assert walker.record_result(params, result) is True

    def test_duplicate_coverage_returns_false(self) -> None:
        walker = HeuristicWalker(rng=Random(42))
        params = {"input_state": {"X": "1"}, "stubs": {}}
        result = MockResult(
            paragraphs_hit=["1000-MAIN"],
            branches_hit={"1": "T"},
        )
        walker.record_result(params, result)

        params2 = {"input_state": {"X": "2"}, "stubs": {}}
        result2 = MockResult(
            paragraphs_hit=["1000-MAIN"],
            branches_hit={"1": "T"},
        )
        assert walker.record_result(params2, result2) is False

    def test_incremental_coverage_added(self) -> None:
        walker = HeuristicWalker(rng=Random(42))

        r1 = MockResult(paragraphs_hit=["A"], branches_hit={})
        walker.record_result({"input_state": {}, "stubs": {}}, r1)

        r2 = MockResult(paragraphs_hit=["B"], branches_hit={})
        added = walker.record_result({"input_state": {}, "stubs": {}}, r2)
        assert added is True
        assert len(walker.corpus.entries) == 2

    def test_corpus_tracks_global_coverage(self) -> None:
        walker = HeuristicWalker(rng=Random(42))
        for i in range(5):
            result = MockResult(
                paragraphs_hit=[f"PARA-{i}"],
                branches_hit={str(i): "T"},
            )
            walker.record_result(
                {"input_state": {}, "stubs": {}}, result
            )
        assert len(walker.corpus.global_paragraphs) == 5
        assert len(walker.corpus.global_branches) == 5

    def test_branches_dict_normalized(self) -> None:
        """branches_hit as a dict should be normalized to 'id:direction' strings."""
        walker = HeuristicWalker(rng=Random(42))
        result = MockResult(
            paragraphs_hit=["A"],
            branches_hit={"1": "T", "2": "F"},
        )
        walker.record_result({"input_state": {}, "stubs": {}}, result)
        entry = walker.corpus.entries[0]
        assert "1:T" in entry.branches_hit
        assert "2:F" in entry.branches_hit

    def test_empty_result_not_added(self) -> None:
        walker = HeuristicWalker(rng=Random(42))
        result = MockResult(paragraphs_hit=[], branches_hit={})
        added = walker.record_result(
            {"input_state": {}, "stubs": {}}, result
        )
        assert added is False
        assert len(walker.corpus.entries) == 0

    def test_energy_updated_after_add(self) -> None:
        walker = HeuristicWalker(rng=Random(42))
        result = MockResult(
            paragraphs_hit=["A", "B"],
            branches_hit={"1": "T"},
        )
        walker.record_result({"input_state": {}, "stubs": {}}, result)
        entry = walker.corpus.entries[0]
        # Energy should have been recalculated after add
        assert entry.energy > 0


# ---------------------------------------------------------------------------
# Integration: full workflow
# ---------------------------------------------------------------------------


class TestFullWorkflow:
    """Integration test: generate -> execute -> record -> mutate loop."""

    def test_generate_record_mutate_cycle(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))

        # Initial params
        params = walker.generate_initial_params()
        assert len(params["input_state"]) == 5
        assert len(params["stubs"]) == 2

        # Record result
        result = MockResult(
            paragraphs_hit=["1000-MAIN", "2000-VALIDATE"],
            branches_hit={"1": "T"},
        )
        added = walker.record_result(params, result)
        assert added is True

        # Explore
        exploratory = walker.generate_exploratory_params()
        result2 = MockResult(
            paragraphs_hit=["1000-MAIN", "3000-PROCESS"],
            branches_hit={"1": "T", "2": "F"},
        )
        walker.record_result(exploratory, result2)

        # Mutate
        mutated = walker.mutate_params(params)
        assert mutated is not params

        # Fault sweep
        sweep = walker.suggest_fault_sweep("READ-ACCOUNT")
        assert len(sweep) >= 5

    def test_many_iterations_grow_corpus(self) -> None:
        report = _build_report()
        walker = HeuristicWalker(field_report=report, rng=Random(42))

        for i in range(20):
            params = walker.generate_exploratory_params()
            result = MockResult(
                paragraphs_hit=[f"PARA-{i % 7}"],
                branches_hit={str(i % 10): ["T", "F"][i % 2]},
            )
            walker.record_result(params, result)

        # Should have grown corpus with unique coverage
        assert len(walker.corpus.entries) > 0
        assert len(walker.corpus.global_paragraphs) > 0
