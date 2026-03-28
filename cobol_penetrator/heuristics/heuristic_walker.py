"""Coverage-guided random walk engine for COBOL penetration testing.

Combines domain-aware value generation, stub fault tables, and corpus
management into a unified engine that produces test inputs designed to
maximize code coverage in instrumented COBOL programs.

The walker operates in three modes:
- **Initial**: generates success-biased params to establish a baseline.
- **Exploratory**: generates random domain-aware params for broad coverage.
- **Mutation**: mutates known-good inputs using AFL-inspired strategies.

It also provides targeted generation for specific branches and fault
sweeps for stub operations.
"""

from __future__ import annotations

import logging
from random import Random
from typing import Any

from cobol_penetrator.heuristics.corpus import Corpus, CorpusEntry
from cobol_penetrator.heuristics.stub_fault_table import (
    fault_values_for,
    success_value_for,
)
from cobol_penetrator.heuristics.value_generator import (
    VariableDomainLike,
    generate_value,
)

logger = logging.getLogger(__name__)

# Strategy weight distributions for exploratory generation
_EXPLORATORY_WEIGHTS: list[tuple[str, float]] = [
    ("condition_literal", 0.40),
    ("random_valid", 0.30),
    ("semantic", 0.20),
    ("boundary", 0.10),
]

# Mutation probability thresholds (cumulative)
_MUT_SINGLE_VAR = 0.30
_MUT_LITERAL_GUIDED = 0.48
_MUT_MULTI_VAR = 0.66
_MUT_GATE_PRESERVING = 0.78
_MUT_CROSSOVER = 0.86
_MUT_RESET = 0.90
# Remaining 0.10 = stub-variation


class HeuristicWalker:
    """Coverage-guided random walk engine.

    Generates, mutates, and records test inputs for instrumented COBOL
    programs. Uses a corpus to track which inputs produced new coverage
    and biases future generation toward unexplored paths.

    Args:
        field_report: A FieldReport-like object with ``.fields``
            (dict[str, VariableDomainLike]), ``.condition_hints`` (dict),
            ``.stub_operations`` (list), and optionally
            ``.stub_variables`` (dict). Can be None for basic operation.
        rng: Random number generator for deterministic behavior.
        knowledge: Optional shared knowledge store. When provided, the
            walker can seed parameter generation from proven successful
            params instead of starting from scratch.
    """

    def __init__(
        self,
        field_report: Any = None,
        rng: Random | None = None,
        knowledge: Any = None,
    ) -> None:
        self.field_report = field_report
        self.rng = rng or Random()
        self.corpus = Corpus()
        self.knowledge = knowledge

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_fields(self) -> dict[str, VariableDomainLike]:
        """Return the field map from field_report, or empty dict."""
        if self.field_report is None:
            return {}
        return getattr(self.field_report, "fields", {})

    def _get_stub_operations(self) -> list[str]:
        """Return the stub operations list from field_report, or empty list."""
        if self.field_report is None:
            return []
        return getattr(self.field_report, "stub_operations", [])

    def _get_stub_variables(self) -> dict[str, str]:
        """Return stub variable to semantic_type mapping, or empty dict."""
        if self.field_report is None:
            return {}
        return getattr(self.field_report, "stub_variables", {})

    def _pick_strategy(self) -> str:
        """Pick a generation strategy based on exploratory weights."""
        r = self.rng.random()
        cumulative = 0.0
        for strategy, weight in _EXPLORATORY_WEIGHTS:
            cumulative += weight
            if r < cumulative:
                return strategy
        return "random_valid"

    def _generate_value_for_field(
        self, domain: VariableDomainLike, strategy: str
    ) -> str | int | float:
        """Generate a value for a single field using the given strategy."""
        return generate_value(domain, strategy, self.rng)

    def _make_stub_success(self, op: str) -> dict[str, str]:
        """Create a success-valued stub entry for a given operation.

        Infers the semantic type from stub_variables if available,
        otherwise defaults to file status success ("00").
        """
        stub_vars = self._get_stub_variables()
        sem_type = stub_vars.get(op, "status_file")
        val = success_value_for(sem_type)
        if val == "":
            val = "00"
        return {"alpha_status": str(val), "num_status": "0"}

    def _make_stub_random(self, op: str) -> dict[str, str]:
        """Create a random fault-valued stub entry for a given operation."""
        stub_vars = self._get_stub_variables()
        sem_type = stub_vars.get(op, "status_file")
        values = fault_values_for(sem_type)
        if values:
            val = self.rng.choice(values)
        else:
            val = "00"
        return {"alpha_status": str(val), "num_status": str(val) if isinstance(val, int) else "0"}

    # ------------------------------------------------------------------
    # Knowledge seeding
    # ------------------------------------------------------------------

    def seed_from_knowledge(
        self, paragraph: str | None = None
    ) -> dict:
        """Start from proven working params instead of random.

        If a specific paragraph is requested and its params are known,
        those are returned. Otherwise falls back to the most recently
        recorded successful params, or empty params as a last resort.

        Args:
            paragraph: Optional target paragraph to look up.

        Returns:
            A params dict with ``"input_state"`` and ``"stubs"`` keys.
        """
        if self.knowledge is not None:
            if (
                paragraph
                and hasattr(self.knowledge, "successful_params")
                and paragraph in self.knowledge.successful_params
            ):
                return dict(self.knowledge.successful_params[paragraph])
            if (
                hasattr(self.knowledge, "successful_params")
                and self.knowledge.successful_params
            ):
                # Use the most recently successful params as baseline
                return dict(
                    list(self.knowledge.successful_params.values())[-1]
                )
        return {"input_state": {}, "stubs": {}}

    # ------------------------------------------------------------------
    # Public API: Parameter generation
    # ------------------------------------------------------------------

    def generate_initial_params(self) -> dict:
        """Generate domain-aware initial params with success bias.

        When shared knowledge is available, seeds from proven successful
        params. For each known input variable, generates a semantic value
        (defaulting to the success path). For each known stub
        operation, uses the canonical success value.

        Returns:
            A dict with ``"input_state"`` and ``"stubs"`` keys.
        """
        # Seed from knowledge if available
        seed = self.seed_from_knowledge()
        seed_input = seed.get("input_state", {})
        seed_stubs = seed.get("stubs", {})

        fields = self._get_fields()
        stub_ops = self._get_stub_operations()

        input_state: dict[str, str | int | float] = {}
        # Start with knowledge-seeded values
        for k, v in seed_input.items():
            input_state[k] = v
        # Fill in any remaining fields from domain generation
        for name, domain in fields.items():
            if name not in input_state:
                input_state[name] = self._generate_value_for_field(
                    domain, "semantic"
                )

        stubs: dict[str, dict[str, str]] = {}
        # Start with knowledge-seeded stubs
        for k, v in seed_stubs.items():
            if isinstance(v, dict):
                stubs[k] = v
        # Fill in remaining stubs
        for op in stub_ops:
            if op not in stubs:
                stubs[op] = self._make_stub_success(op)

        return {"input_state": input_state, "stubs": stubs}

    def generate_exploratory_params(self) -> dict:
        """Generate random domain-aware params for exploration.

        When shared knowledge is available, seeds from proven successful
        params and then mutates a subset of fields. Uses a mix of
        strategies: 40% condition_literal, 30% random_valid, 20%
        semantic, 10% boundary.

        Returns:
            A dict with ``"input_state"`` and ``"stubs"`` keys.
        """
        # Seed from knowledge if available
        seed = self.seed_from_knowledge()
        seed_input = seed.get("input_state", {})

        fields = self._get_fields()
        stub_ops = self._get_stub_operations()

        input_state: dict[str, str | int | float] = {}
        # Start with knowledge-seeded values
        for k, v in seed_input.items():
            input_state[k] = v
        # Then apply exploratory generation on top
        for name, domain in fields.items():
            strategy = self._pick_strategy()
            input_state[name] = self._generate_value_for_field(
                domain, strategy
            )

        stubs: dict[str, dict[str, str]] = {}
        for op in stub_ops:
            stubs[op] = self._make_stub_random(op)

        return {"input_state": input_state, "stubs": stubs}

    def mutate_params(self, parent: dict) -> dict:
        """Mutate parent params using AFL-inspired strategies.

        Distribution:
            - 30% single-var flip
            - 18% literal-guided
            - 18% multi-var flip (2-4 variables)
            - 12% gate-preserving (only non-status variables)
            - 8% crossover from corpus
            - 4% reset to zero/empty
            - 10% stub-variation

        Args:
            parent: A params dict with ``"input_state"`` and ``"stubs"`` keys.

        Returns:
            A new mutated params dict (the parent is not modified).
        """
        fields = self._get_fields()
        input_state = dict(parent.get("input_state", {}))
        stubs = dict(parent.get("stubs", {}))
        var_names = list(input_state.keys())

        if not var_names and not stubs:
            return {"input_state": input_state, "stubs": stubs}

        r = self.rng.random()

        if r < _MUT_SINGLE_VAR and var_names:
            # Single-var flip
            name = self.rng.choice(var_names)
            if name in fields:
                input_state[name] = self._generate_value_for_field(
                    fields[name], "random_valid"
                )

        elif r < _MUT_LITERAL_GUIDED and var_names:
            # Literal-guided: prefer variables with condition literals
            candidates = [
                n for n in var_names
                if n in fields and fields[n].condition_literals
            ]
            if candidates:
                name = self.rng.choice(candidates)
                input_state[name] = self.rng.choice(
                    fields[name].condition_literals
                )
            elif var_names:
                name = self.rng.choice(var_names)
                if name in fields:
                    input_state[name] = self._generate_value_for_field(
                        fields[name], "random_valid"
                    )

        elif r < _MUT_MULTI_VAR and len(var_names) >= 2:
            # Multi-var flip (2-4 variables)
            n_changes = self.rng.randint(2, max(2, min(4, len(var_names))))
            for name in self.rng.sample(var_names, n_changes):
                if name in fields:
                    input_state[name] = self._generate_value_for_field(
                        fields[name], "random_valid"
                    )

        elif r < _MUT_GATE_PRESERVING and var_names:
            # Gate-preserving: only mutate non-status variables
            non_status = [
                n for n in var_names
                if n in fields
                and fields[n].classification not in ("status",)
            ]
            if non_status:
                n_changes = self.rng.randint(1, min(3, len(non_status)))
                for name in self.rng.sample(non_status, n_changes):
                    input_state[name] = self._generate_value_for_field(
                        fields[name], "random_valid"
                    )
            elif var_names:
                name = self.rng.choice(var_names)
                if name in fields:
                    input_state[name] = self._generate_value_for_field(
                        fields[name], "random_valid"
                    )

        elif r < _MUT_CROSSOVER and var_names:
            # Crossover from a different corpus entry
            if len(self.corpus.entries) >= 2:
                donor = self.rng.choice(self.corpus.entries)
                n_vars = self.rng.randint(1, min(3, len(var_names)))
                for name in self.rng.sample(var_names, n_vars):
                    if name in donor.input_state:
                        input_state[name] = donor.input_state[name]
                if donor.stubs:
                    stubs = dict(donor.stubs)
            else:
                name = self.rng.choice(var_names)
                if name in fields:
                    input_state[name] = self._generate_value_for_field(
                        fields[name], "random_valid"
                    )

        elif r < _MUT_RESET and var_names:
            # Reset one variable to zero/empty default
            name = self.rng.choice(var_names)
            if name in fields:
                domain = fields[name]
                if domain.classification == "status":
                    input_state[name] = " "
                elif domain.classification == "flag":
                    input_state[name] = "N"
                else:
                    input_state[name] = ""

        else:
            # Stub-variation
            stub_ops = list(stubs.keys())
            if stub_ops:
                n_ops = self.rng.randint(1, min(3, len(stub_ops)))
                for op in self.rng.sample(stub_ops, n_ops):
                    stubs[op] = self._make_stub_random(op)
            elif var_names:
                # Fallback: single-var flip
                name = self.rng.choice(var_names)
                if name in fields:
                    input_state[name] = self._generate_value_for_field(
                        fields[name], "random_valid"
                    )

        return {"input_state": input_state, "stubs": stubs}

    def suggest_params_for_branch(
        self,
        branch_id: str,
        direction: str,
        condition_vars: list[str],
        condition_text: str = "",
    ) -> dict:
        """Generate params targeting a specific branch direction.

        Uses condition_literals for the condition variables if
        available, otherwise uses semantic or random_valid generation.

        Args:
            branch_id: The branch identifier to target.
            direction: Desired direction (e.g. "T", "F").
            condition_vars: Variable names involved in the branch
                condition.
            condition_text: Optional raw condition text for context.

        Returns:
            A params dict with ``"input_state"`` and ``"stubs"`` keys
            biased toward taking the specified branch direction.
        """
        fields = self._get_fields()
        stub_ops = self._get_stub_operations()

        # Start with current best seed if available
        seed = self.corpus.select_seed(self.rng)
        if seed is not None:
            input_state = dict(seed.input_state)
            stubs = dict(seed.stubs)
        else:
            input_state = {}
            stubs = {}

        # Bias condition variables toward taking the target direction
        for var_name in condition_vars:
            if var_name in fields:
                domain = fields[var_name]
                # Try condition_literal first, then boundary, then semantic
                if domain.condition_literals:
                    input_state[var_name] = self.rng.choice(
                        domain.condition_literals
                    )
                elif direction == "T":
                    # For True branch, try boundary max or semantic
                    input_state[var_name] = self._generate_value_for_field(
                        domain, "boundary"
                    )
                else:
                    # For False branch, try adversarial/zero
                    input_state[var_name] = self._generate_value_for_field(
                        domain, "adversarial"
                    )

        # Fill stubs with success values for non-targeted branches
        for op in stub_ops:
            if op not in stubs:
                stubs[op] = self._make_stub_success(op)

        return {"input_state": input_state, "stubs": stubs}

    def suggest_fault_sweep(self, stub_op: str) -> list[dict]:
        """Generate a sweep of fault values for a stub operation.

        Produces one params dict for each known fault value of the
        stub operation's semantic type. This is useful for exercising
        all error-handling paths for a particular I/O operation.

        Args:
            stub_op: The stub operation key (e.g. "READ-ACCOUNT").

        Returns:
            A list of params dicts, one per fault value. Each has
            the stub operation set to a different fault code while
            other stubs use success values.
        """
        stub_vars = self._get_stub_variables()
        sem_type = stub_vars.get(stub_op, "status_file")
        fault_vals = fault_values_for(sem_type)

        if not fault_vals:
            # Unknown type — produce a minimal sweep with file status codes
            fault_vals = fault_values_for("status_file")

        # Start from initial params as a base
        base = self.generate_initial_params()
        results: list[dict] = []

        for val in fault_vals:
            params = {
                "input_state": dict(base["input_state"]),
                "stubs": dict(base["stubs"]),
            }
            params["stubs"][stub_op] = {
                "alpha_status": str(val),
                "num_status": str(val) if isinstance(val, int) else "0",
            }
            results.append(params)

        return results

    # ------------------------------------------------------------------
    # Public API: Result recording
    # ------------------------------------------------------------------

    def record_result(self, params: dict, result: Any) -> bool:
        """Record execution result into corpus.

        Creates a CorpusEntry from the params and result, and adds it
        to the corpus if it provides new coverage. Also triggers an
        energy update after adding.

        Args:
            params: The params dict that produced this result.
            result: An object with ``.paragraphs_hit`` and
                ``.branches_hit`` attributes (e.g. ExecutionResult).

        Returns:
            True if new coverage was found and the entry was added.
        """
        paragraphs_hit = frozenset(
            getattr(result, "paragraphs_hit", [])
        )
        branches_hit_raw = getattr(result, "branches_hit", {})

        # branches_hit may be a dict (branch_id -> direction) or a
        # set/list. Normalize to frozenset of strings.
        if isinstance(branches_hit_raw, dict):
            branches_hit = frozenset(
                f"{k}:{v}" for k, v in branches_hit_raw.items()
            )
        else:
            branches_hit = frozenset(branches_hit_raw)

        entry = CorpusEntry(
            input_state=params.get("input_state", {}),
            stubs=params.get("stubs", {}),
            paragraphs_hit=paragraphs_hit,
            branches_hit=branches_hit,
        )

        added = self.corpus.add(entry)
        if added:
            self.corpus.update_energy()
            logger.debug(
                "New coverage: %d paragraphs, %d branches (corpus size: %d)",
                len(self.corpus.global_paragraphs),
                len(self.corpus.global_branches),
                len(self.corpus.entries),
            )

        return added
