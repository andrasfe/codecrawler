"""COBOL binary executor.

Orchestrates running an instrumented COBOL executable:

1. Generates a temporary .dat file from input parameters.
2. Runs the executable with ``MOCKDATA=<dat_path>`` in the environment.
3. Parses stdout for trace output.
4. Returns an ``ExecutionResult``.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

from cobol_penetrator.mock_data import generate_mock_file
from cobol_penetrator.trace_parser import ExecutionResult, parse_traces

logger = logging.getLogger(__name__)


def execute(
    executable: Path,
    params: dict,
    timeout: int = 30,
) -> ExecutionResult:
    """Run an instrumented COBOL executable and return parsed traces.

    Args:
        executable: Path to the compiled COBOL binary.
        params: Dictionary with ``"input_state"`` and ``"stubs"`` keys.
            ``input_state`` maps variable names to values.
            ``stubs`` maps operation keys to status dicts.
        timeout: Maximum seconds to wait for the process (default 30).

    Returns:
        An ``ExecutionResult`` populated with trace data, exit code,
        stderr, and raw stdout.

    Raises:
        FileNotFoundError: If *executable* does not exist.
        subprocess.TimeoutExpired: If the process exceeds *timeout*.
    """
    executable = Path(executable)
    if not executable.exists():
        raise FileNotFoundError(f"Executable not found: {executable}")

    input_state: dict[str, str] = params.get("input_state", {})
    stubs: dict[str, dict[str, str]] = params.get("stubs", {})

    # Generate mock data file in a temp directory.
    with tempfile.TemporaryDirectory(prefix="cobol_pen_") as tmpdir:
        dat_path = Path(tmpdir) / "mockdata.dat"
        generate_mock_file(input_state, stubs, dat_path)

        env = os.environ.copy()
        env["MOCKDATA"] = str(dat_path)

        logger.debug(
            "Executing %s with MOCKDATA=%s (timeout=%ds)",
            executable,
            dat_path,
            timeout,
        )

        try:
            proc = subprocess.run(
                [str(executable)],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "Executable %s timed out after %d seconds", executable, timeout
            )
            raise

    result = parse_traces(proc.stdout)
    result.exit_code = proc.returncode
    result.stderr = proc.stderr
    return result
