"""Heuristic value generation and coverage-guided random walk.

This package provides domain-aware parameter generation for COBOL
coverage penetration, complementing the LLM-based agents with
deterministic and randomized strategies.

Public API:
    - ``HeuristicWalker``: The main random walk engine.
    - ``Corpus``, ``CorpusEntry``: Coverage-guided corpus management.
    - ``generate_value``, ``format_value_for_mock``: Value generation.
    - ``VariableDomainLike``: Protocol for variable domain objects.
    - ``fault_values_for``, ``success_value_for``: Fault code lookups.
"""

from cobol_penetrator.heuristics.corpus import Corpus, CorpusEntry
from cobol_penetrator.heuristics.heuristic_walker import HeuristicWalker
from cobol_penetrator.heuristics.stub_fault_table import (
    fault_values_for,
    success_value_for,
)
from cobol_penetrator.heuristics.value_generator import (
    VariableDomainLike,
    format_value_for_mock,
    generate_value,
)

__all__ = [
    "Corpus",
    "CorpusEntry",
    "HeuristicWalker",
    "VariableDomainLike",
    "fault_values_for",
    "format_value_for_mock",
    "generate_value",
    "success_value_for",
]
