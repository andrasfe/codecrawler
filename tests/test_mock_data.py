"""Tests for cobol_penetrator.mock_data."""

from __future__ import annotations

from pathlib import Path

from cobol_penetrator.mock_data import (
    RECORD_WIDTH,
    MockRecord,
    format_record,
    generate_mock_file,
)


class TestMockRecord:
    """MockRecord dataclass basics."""

    def test_default_fields(self) -> None:
        rec = MockRecord(op_key="TEST")
        assert rec.op_key == "TEST"
        assert rec.alpha_status == ""
        assert rec.num_status == ""


class TestFormatRecord:
    """80-byte record formatting."""

    def test_record_is_80_bytes(self) -> None:
        rec = MockRecord(op_key="OP", alpha_status="STAT", num_status="123")
        line = format_record(rec)
        assert len(line) == RECORD_WIDTH

    def test_fields_left_justified(self) -> None:
        rec = MockRecord(op_key="OP", alpha_status="STAT", num_status="9")
        line = format_record(rec)
        # op_key occupies bytes 0..29
        assert line[0:2] == "OP"
        assert line[2:30] == " " * 28
        # alpha_status occupies bytes 30..49
        assert line[30:34] == "STAT"
        assert line[34:50] == " " * 16
        # num_status occupies bytes 50..58
        assert line[50:51] == "9"
        assert line[51:59] == " " * 8
        # filler is bytes 59..79
        assert line[59:80] == " " * 21

    def test_empty_fields_produce_spaces(self) -> None:
        rec = MockRecord(op_key="", alpha_status="", num_status="")
        line = format_record(rec)
        assert line == " " * RECORD_WIDTH

    def test_truncation_at_field_width(self) -> None:
        """Values longer than the field width are truncated."""
        rec = MockRecord(
            op_key="A" * 50,
            alpha_status="B" * 30,
            num_status="C" * 20,
        )
        line = format_record(rec)
        assert len(line) == RECORD_WIDTH
        assert line[0:30] == "A" * 30
        assert line[30:50] == "B" * 20
        assert line[50:59] == "C" * 9

    def test_init_record_format(self) -> None:
        """INIT:<varname> fits in the 30-char op_key field."""
        rec = MockRecord(op_key="INIT:WS-STATUS", alpha_status="00")
        line = format_record(rec)
        assert len(line) == RECORD_WIDTH
        assert line[0:14] == "INIT:WS-STATUS"
        assert line[30:32] == "00"


class TestGenerateMockFile:
    """File generation with INIT and stub records."""

    def test_init_records_from_input_state(self, tmp_path: Path) -> None:
        output = tmp_path / "test.dat"
        input_state = {"WS-STATUS": "00", "WS-FLAG": "Y"}
        generate_mock_file(input_state, {}, output)

        lines = output.read_text().splitlines()
        assert len(lines) == 2
        for line in lines:
            assert len(line) == RECORD_WIDTH

        # First INIT record op_key
        assert lines[0].startswith("INIT:WS-STATUS")
        # alpha_status starts at byte 30
        assert lines[0][30:32] == "00"

    def test_stub_records(self, tmp_path: Path) -> None:
        output = tmp_path / "test.dat"
        stubs = {
            "READ-ACCOUNT": {"alpha_status": "OK", "num_status": "0"},
        }
        generate_mock_file({}, stubs, output)

        lines = output.read_text().splitlines()
        assert len(lines) == 1
        assert lines[0][:12] == "READ-ACCOUNT"
        assert lines[0][30:32] == "OK"
        assert lines[0][50:51] == "0"

    def test_mixed_init_and_stubs(self, tmp_path: Path) -> None:
        output = tmp_path / "test.dat"
        input_state = {"VAR1": "HELLO"}
        stubs = {"OP1": {"alpha_status": "DONE"}}
        generate_mock_file(input_state, stubs, output)

        lines = output.read_text().splitlines()
        # INIT records come first, then stubs.
        assert len(lines) == 2
        assert lines[0].startswith("INIT:VAR1")
        assert lines[1].startswith("OP1")

    def test_empty_input_produces_empty_file(self, tmp_path: Path) -> None:
        output = tmp_path / "test.dat"
        generate_mock_file({}, {}, output)

        content = output.read_text()
        assert content == ""

    def test_returns_output_path(self, tmp_path: Path) -> None:
        output = tmp_path / "test.dat"
        result = generate_mock_file({}, {}, output)
        assert result == output

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        output = tmp_path / "nested" / "deep" / "test.dat"
        generate_mock_file({"X": "1"}, {}, output)
        assert output.exists()

    def test_stub_with_missing_keys_defaults_empty(self, tmp_path: Path) -> None:
        """Stub dict may omit alpha_status or num_status."""
        output = tmp_path / "test.dat"
        stubs = {"SOME-OP": {}}
        generate_mock_file({}, stubs, output)

        lines = output.read_text().splitlines()
        assert len(lines) == 1
        assert len(lines[0]) == RECORD_WIDTH
        # op_key present, statuses are spaces
        assert lines[0][:7] == "SOME-OP"
        assert lines[0][30:50] == " " * 20
        assert lines[0][50:59] == " " * 9

    def test_all_records_exactly_80_bytes(self, tmp_path: Path) -> None:
        """Every line in the generated file must be exactly 80 characters."""
        output = tmp_path / "test.dat"
        input_state = {"A": "1", "B": "2", "C": "3"}
        stubs = {
            "OP-X": {"alpha_status": "OK", "num_status": "99"},
            "OP-Y": {"alpha_status": "ERR"},
        }
        generate_mock_file(input_state, stubs, output)

        for line in output.read_text().splitlines():
            assert len(line) == RECORD_WIDTH, f"Line not 80 bytes: {line!r}"
