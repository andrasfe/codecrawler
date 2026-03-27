"""Six-strategy domain-aware value generator for COBOL variables.

Generates values for COBOL variables based on their PIC clause domain
information and one of six strategies: condition_literal, 88_value,
boundary, semantic, adversarial, or random_valid.

The VariableDomainLike protocol allows this module to work with any
domain object that provides the required attributes, decoupling it
from the analysis package being built in parallel.
"""

from __future__ import annotations

from random import Random
from typing import Protocol

from cobol_penetrator.heuristics.stub_fault_table import fault_values_for


class VariableDomainLike(Protocol):
    """Minimal interface for variable domain info.

    Any object providing these attributes can be used as a domain
    input for value generation. This decouples the heuristics package
    from the analysis package.
    """

    name: str
    data_type: str  # "alpha", "numeric", "packed", "unknown"
    max_length: int
    precision: int  # decimal places (0 for integers)
    signed: bool
    min_value: int | float | None
    max_value: int | float | None
    condition_literals: list
    valid_88_values: dict[str, str]
    classification: str  # "status", "flag", "data", etc.
    semantic_type: str  # "date", "amount", "status_file", etc.


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_value(
    domain: VariableDomainLike,
    strategy: str,
    rng: Random | None = None,
) -> str | int | float:
    """Generate a value for a COBOL variable using the given strategy.

    Args:
        domain: Variable domain information describing PIC constraints,
            condition literals, semantic type, etc.
        strategy: One of ``"condition_literal"``, ``"88_value"``,
            ``"boundary"``, ``"semantic"``, ``"adversarial"``,
            ``"random_valid"``.
        rng: Random number generator for deterministic output.

    Returns:
        A value appropriate for the variable's type and constraints.
        Falls back to ``random_valid`` if the requested strategy
        cannot produce a value (e.g. no condition literals available).
    """
    if rng is None:
        rng = Random()

    if strategy == "condition_literal" and domain.condition_literals:
        return rng.choice(domain.condition_literals)

    if strategy == "88_value" and domain.valid_88_values:
        return rng.choice(list(domain.valid_88_values.values()))

    if strategy == "boundary":
        return _generate_boundary(domain, rng)

    if strategy == "semantic":
        return _generate_semantic(domain, rng)

    if strategy == "adversarial":
        return _generate_adversarial(domain, rng)

    # "random_valid" or fallback for strategies that had no data
    return _generate_random_valid(domain, rng)


def format_value_for_mock(
    domain: VariableDomainLike, value: str | int | float
) -> str:
    """Format a generated value to fit within 80-byte mock record limits.

    Alpha values are capped at 20 characters (the ALPHA_STATUS_WIDTH
    of the mock record format). Numeric values are capped at 9 digits
    (the NUM_STATUS_WIDTH).

    Args:
        domain: Variable domain information.
        value: The generated value to format.

    Returns:
        A string representation that fits within mock record constraints.
    """
    max_alpha = 20
    max_numeric_digits = 9

    str_val = str(value)

    if domain.data_type in ("alpha", "unknown"):
        return str_val[:max_alpha]

    # Numeric: ensure it fits within 9 digits
    if isinstance(value, float):
        # Format with precision, then truncate
        formatted = f"{value:.{domain.precision}f}" if domain.precision > 0 else str(int(value))
        return formatted[:max_numeric_digits]

    if isinstance(value, int):
        formatted = str(value)
        # If too long, clamp to max representable
        if len(formatted.lstrip("-")) > max_numeric_digits:
            if value < 0:
                return str(-(10**max_numeric_digits - 1))
            return str(10**max_numeric_digits - 1)
        return formatted

    # String fallback
    return str_val[:max_alpha]


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------

_ALPHA_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "


def _generate_boundary(
    domain: VariableDomainLike, rng: Random
) -> str | int | float:
    """Generate boundary values for the domain.

    For alpha types: empty string, all-spaces, or all-A's at max length.
    For numeric types: min, max, mid, and +/-1 edge cases.
    """
    if domain.data_type in ("alpha", "unknown"):
        choices = [
            "",
            " " * domain.max_length,
            "A" * domain.max_length,
        ]
        return rng.choice(choices)

    candidates: list[int | float] = []

    if domain.min_value is not None:
        candidates.append(domain.min_value)
        if isinstance(domain.min_value, int):
            candidates.append(domain.min_value + 1)

    if domain.max_value is not None:
        candidates.append(domain.max_value)
        if isinstance(domain.max_value, int):
            candidates.append(domain.max_value - 1)

    candidates.append(0)

    if domain.min_value is not None and domain.max_value is not None:
        mid = (domain.min_value + domain.max_value) / 2
        if domain.precision == 0:
            mid = int(mid)
        candidates.append(mid)

    return rng.choice(candidates) if candidates else 0


def _generate_semantic(
    domain: VariableDomainLike, rng: Random
) -> str | int | float:
    """Generate domain-aware values based on semantic type.

    Produces realistic COBOL-domain values: dates in YYYYMMDD format,
    amounts, counters, identifiers, flags, and status codes from the
    fault tables.
    """
    sem = domain.semantic_type

    if sem == "date":
        year = rng.randint(2020, 2027)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        if domain.max_length >= 8:
            return f"{year:04d}{month:02d}{day:02d}"
        return f"{year % 100:02d}{month:02d}{day:02d}"

    if sem == "time":
        h = rng.randint(0, 23)
        m = rng.randint(0, 59)
        s = rng.randint(0, 59)
        return f"{h:02d}{m:02d}{s:02d}"

    if sem == "amount":
        if domain.precision > 0:
            return round(rng.uniform(0.01, 999999.99), domain.precision)
        return rng.randint(0, 999999)

    if sem == "counter":
        return rng.randint(0, 100)

    if sem == "identifier":
        digits = min(domain.max_length, 10) if domain.max_length > 0 else 10
        return str(rng.randint(10 ** (digits - 1), 10**digits - 1))

    if sem in ("status_file", "status_sql", "status_cics", "status_dli"):
        values = fault_values_for(sem)
        if values:
            return rng.choice(values)

    if sem == "flag_bool":
        if domain.valid_88_values:
            return rng.choice(list(domain.valid_88_values.values()))
        return rng.choice(["Y", "N"])

    # Generic — fall through to random_valid
    return _generate_random_valid(domain, rng)


def _generate_random_valid(
    domain: VariableDomainLike, rng: Random
) -> str | int | float:
    """Generate a random value within PIC constraints.

    Alpha: random uppercase alphanumeric string of max_length.
    Numeric integer: random int within [min_value, max_value].
    Numeric decimal: random float within [min_value, max_value] at precision.
    """
    if domain.data_type in ("alpha", "unknown"):
        length = max(domain.max_length, 1)
        chars = "".join(rng.choice(_ALPHA_CHARS) for _ in range(length))
        return chars

    # Numeric types
    if domain.precision > 0:
        lo = float(domain.min_value) if domain.min_value is not None else 0.0
        hi = float(domain.max_value) if domain.max_value is not None else 99999.99
        return round(rng.uniform(lo, hi), domain.precision)

    lo = int(domain.min_value) if domain.min_value is not None else 0
    hi = int(domain.max_value) if domain.max_value is not None else 99999
    return rng.randint(lo, hi)


def _generate_adversarial(
    domain: VariableDomainLike, rng: Random
) -> str | int | float:
    """Generate edge-case / adversarial values.

    For alpha: empty string, all spaces, all 9s, all As.
    For numeric: zero, min, max, all-nines, and negated all-nines
    if the field is signed.
    """
    if domain.data_type in ("alpha", "unknown"):
        candidates = [
            "",
            " " * domain.max_length,
            "9" * domain.max_length,
            "A" * domain.max_length,
        ]
        return rng.choice(candidates)

    candidates: list[int | float] = [0]

    if domain.max_value is not None:
        candidates.append(domain.max_value)
    if domain.min_value is not None:
        candidates.append(domain.min_value)

    # All nines
    nines = 10**domain.max_length - 1 if domain.max_length > 0 else 99999
    candidates.append(nines)

    if domain.signed:
        candidates.append(-nines)

    return rng.choice(candidates)
