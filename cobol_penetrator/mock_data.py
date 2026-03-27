"""Mock data generator for 80-byte LINE SEQUENTIAL records.

Generates temporary .dat files consumed by instrumented COBOL executables
via the MOCKDATA environment variable. Each record is exactly 80 bytes,
left-justified and space-padded:

    <op-key:30><alpha-status:20><num-status:9><filler:21>

Two record types are produced:
- INIT records: op_key = "INIT:<varname>", alpha_status = variable value
- Stub records: op_key = stub operation key, with status values
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Fixed field widths per the spec (total = 80).
OP_KEY_WIDTH = 30
ALPHA_STATUS_WIDTH = 20
NUM_STATUS_WIDTH = 9
FILLER_WIDTH = 21
RECORD_WIDTH = OP_KEY_WIDTH + ALPHA_STATUS_WIDTH + NUM_STATUS_WIDTH + FILLER_WIDTH

assert RECORD_WIDTH == 80, f"Record width must be 80, got {RECORD_WIDTH}"


@dataclass
class MockRecord:
    """A single 80-byte mock data record.

    Attributes:
        op_key: Operation key (max 30 chars).
        alpha_status: Alphanumeric status field (max 20 chars).
        num_status: Numeric status field (max 9 chars).
    """

    op_key: str
    alpha_status: str = ""
    num_status: str = ""


def format_record(record: MockRecord) -> str:
    """Format a MockRecord into an exactly 80-character string.

    Each field is left-justified and truncated to its maximum width,
    then space-padded. The three fields plus a 21-byte filler of
    spaces produce exactly 80 characters.

    Args:
        record: The MockRecord to format.

    Returns:
        An 80-character string representing the record.
    """
    op_key = record.op_key[:OP_KEY_WIDTH].ljust(OP_KEY_WIDTH)
    alpha_status = record.alpha_status[:ALPHA_STATUS_WIDTH].ljust(ALPHA_STATUS_WIDTH)
    num_status = record.num_status[:NUM_STATUS_WIDTH].ljust(NUM_STATUS_WIDTH)
    filler = " " * FILLER_WIDTH

    line = op_key + alpha_status + num_status + filler
    assert len(line) == RECORD_WIDTH, f"Record length {len(line)} != {RECORD_WIDTH}"
    return line


def generate_mock_file(
    input_state: dict[str, str],
    stubs: dict[str, dict[str, str]],
    output_path: Path,
) -> Path:
    """Generate a .dat file with INIT and stub records.

    Args:
        input_state: Mapping of variable name to value. Each entry
            produces an INIT record with op_key ``"INIT:<varname>"``
            and alpha_status set to the value.
        stubs: Mapping of operation key to a dict with optional
            ``"alpha_status"`` and ``"num_status"`` keys.
        output_path: Destination file path for the .dat file.

    Returns:
        The *output_path* after writing.
    """
    records: list[MockRecord] = []

    # INIT records — one per variable in input_state.
    for varname, value in input_state.items():
        records.append(
            MockRecord(
                op_key=f"INIT:{varname}",
                alpha_status=str(value),
            )
        )

    # Stub records — one per operation key.
    # The LLM may return stubs as {"key": "value"} (string shorthand)
    # or {"key": {"alpha_status": "...", "num_status": "..."}} (full form).
    for op_key, status in stubs.items():
        if isinstance(status, str):
            # Shorthand: treat the string as alpha_status
            records.append(
                MockRecord(op_key=op_key, alpha_status=status)
            )
        elif isinstance(status, dict):
            records.append(
                MockRecord(
                    op_key=op_key,
                    alpha_status=status.get("alpha_status", ""),
                    num_status=status.get("num_status", ""),
                )
            )
        else:
            records.append(MockRecord(op_key=op_key, alpha_status=str(status)))

    # Write all records, one per line.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(format_record(record) + "\n")

    return output_path
