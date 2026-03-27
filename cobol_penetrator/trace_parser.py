"""Trace output parser for 5 COBOL trace formats.

Parses instrumented COBOL executable stdout into structured
ExecutionResult data. Handles the following trace prefixes:

- SPECTER-TRACE:<PARAGRAPH>
- @@B:<id>:<T|F|W1|WO>
- SPECTER-CALL:FROM=<caller>:TO=<callee>
- @@V:<bid>:<var1>=<val1>:<var2>=<val2>
- SPECTER-MOCK:<operation>
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExecutionResult:
    """Structured result from running an instrumented COBOL binary.

    Attributes:
        paragraphs_hit: Paragraphs entered (from SPECTER-TRACE lines).
        branches_hit: Branch probes taken, mapping branch id to direction
            (from @@B lines).
        call_chain: Caller/callee pairs (from SPECTER-CALL lines).
        variable_snapshots: Variable values at branch points, mapping
            branch id to {var: value} (from @@V lines).
        mock_ops: Mock operations executed (from SPECTER-MOCK lines).
        exit_code: Process exit code.
        stderr: Captured stderr output.
        raw_stdout: Full unmodified stdout.
    """

    paragraphs_hit: list[str] = field(default_factory=list)
    branches_hit: dict[str, str] = field(default_factory=dict)
    call_chain: list[tuple[str, str]] = field(default_factory=list)
    variable_snapshots: dict[str, dict[str, str]] = field(default_factory=dict)
    mock_ops: list[str] = field(default_factory=list)
    exit_code: int = 0
    stderr: str = ""
    raw_stdout: str = ""


def _parse_specter_trace(line: str, result: ExecutionResult) -> bool:
    """Parse a SPECTER-TRACE:<PARAGRAPH> line.

    Returns True if the line was consumed.
    """
    prefix = "SPECTER-TRACE:"
    if not line.startswith(prefix):
        return False
    paragraph = line[len(prefix):]
    if paragraph:
        result.paragraphs_hit.append(paragraph)
    return True


def _parse_branch_probe(line: str, result: ExecutionResult) -> bool:
    """Parse a @@B:<id>:<direction> line.

    Direction is one of T, F, W1, WO.
    Returns True if the line was consumed.
    """
    prefix = "@@B:"
    if not line.startswith(prefix):
        return False
    rest = line[len(prefix):]
    parts = rest.split(":", 1)
    if len(parts) == 2:
        branch_id, direction = parts
        result.branches_hit[branch_id] = direction
    return True


def _parse_specter_call(line: str, result: ExecutionResult) -> bool:
    """Parse a SPECTER-CALL:FROM=<caller>:TO=<callee> line.

    Returns True if the line was consumed.
    """
    prefix = "SPECTER-CALL:"
    if not line.startswith(prefix):
        return False
    rest = line[len(prefix):]
    # Expected: FROM=<caller>:TO=<callee>
    from_part = None
    to_part = None
    for segment in rest.split(":"):
        if segment.startswith("FROM="):
            from_part = segment[len("FROM="):]
        elif segment.startswith("TO="):
            to_part = segment[len("TO="):]
    if from_part is not None and to_part is not None:
        result.call_chain.append((from_part, to_part))
    return True


def _parse_variable_snapshot(line: str, result: ExecutionResult) -> bool:
    """Parse a @@V:<bid>:<var1>=<val1>:<var2>=<val2> line.

    Returns True if the line was consumed.
    """
    prefix = "@@V:"
    if not line.startswith(prefix):
        return False
    rest = line[len(prefix):]
    parts = rest.split(":")
    if len(parts) < 2:
        return True  # Consumed but malformed — skip silently
    branch_id = parts[0]
    variables: dict[str, str] = {}
    for kv_pair in parts[1:]:
        eq_idx = kv_pair.find("=")
        if eq_idx > 0:
            var_name = kv_pair[:eq_idx]
            var_value = kv_pair[eq_idx + 1:]
            variables[var_name] = var_value
    result.variable_snapshots[branch_id] = variables
    return True


def _parse_specter_mock(line: str, result: ExecutionResult) -> bool:
    """Parse a SPECTER-MOCK:<operation> line.

    Returns True if the line was consumed.
    """
    prefix = "SPECTER-MOCK:"
    if not line.startswith(prefix):
        return False
    operation = line[len(prefix):]
    if operation:
        result.mock_ops.append(operation)
    return True


# Ordered list of parsers — each returns True if it consumed the line.
_PARSERS = [
    _parse_specter_trace,
    _parse_branch_probe,
    _parse_specter_call,
    _parse_variable_snapshot,
    _parse_specter_mock,
]


def parse_traces(stdout: str) -> ExecutionResult:
    """Parse instrumented COBOL stdout into an ExecutionResult.

    Processes each line of *stdout* against the five known trace
    formats. Lines that do not match any prefix are silently ignored
    (the COBOL program may emit arbitrary DISPLAY output).

    Args:
        stdout: Raw stdout captured from the COBOL executable.

    Returns:
        An ExecutionResult populated with parsed trace data.
    """
    result = ExecutionResult(raw_stdout=stdout)

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for parser in _PARSERS:
            if parser(line, result):
                break  # Line consumed — move to next line

    return result
