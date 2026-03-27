"""Tests for cobol_penetrator.trace_parser."""

from __future__ import annotations

from pathlib import Path

from cobol_penetrator.trace_parser import ExecutionResult, parse_traces


class TestParseSpecterTrace:
    """SPECTER-TRACE:<PARAGRAPH> lines."""

    def test_single_paragraph(self) -> None:
        result = parse_traces("SPECTER-TRACE:1000-MAIN\n")
        assert result.paragraphs_hit == ["1000-MAIN"]

    def test_multiple_paragraphs(self) -> None:
        stdout = (
            "SPECTER-TRACE:1000-MAIN\n"
            "SPECTER-TRACE:2000-VALIDATE\n"
            "SPECTER-TRACE:9000-EXIT\n"
        )
        result = parse_traces(stdout)
        assert result.paragraphs_hit == ["1000-MAIN", "2000-VALIDATE", "9000-EXIT"]

    def test_empty_paragraph_ignored(self) -> None:
        result = parse_traces("SPECTER-TRACE:\n")
        assert result.paragraphs_hit == []


class TestParseBranchProbe:
    """@@B:<id>:<direction> lines."""

    def test_true_branch(self) -> None:
        result = parse_traces("@@B:1:T\n")
        assert result.branches_hit == {"1": "T"}

    def test_false_branch(self) -> None:
        result = parse_traces("@@B:2:F\n")
        assert result.branches_hit == {"2": "F"}

    def test_when1_branch(self) -> None:
        result = parse_traces("@@B:10:W1\n")
        assert result.branches_hit == {"10": "W1"}

    def test_when_other_branch(self) -> None:
        result = parse_traces("@@B:99:WO\n")
        assert result.branches_hit == {"99": "WO"}

    def test_multiple_branches(self) -> None:
        stdout = "@@B:1:T\n@@B:2:F\n@@B:3:W1\n"
        result = parse_traces(stdout)
        assert result.branches_hit == {"1": "T", "2": "F", "3": "W1"}

    def test_later_branch_overwrites_earlier(self) -> None:
        """If the same branch id appears twice, last direction wins."""
        stdout = "@@B:1:T\n@@B:1:F\n"
        result = parse_traces(stdout)
        assert result.branches_hit == {"1": "F"}


class TestParseSpecterCall:
    """SPECTER-CALL:FROM=<caller>:TO=<callee> lines."""

    def test_single_call(self) -> None:
        result = parse_traces("SPECTER-CALL:FROM=1000-MAIN:TO=2000-VALIDATE\n")
        assert result.call_chain == [("1000-MAIN", "2000-VALIDATE")]

    def test_multiple_calls(self) -> None:
        stdout = (
            "SPECTER-CALL:FROM=1000-MAIN:TO=2000-VALIDATE\n"
            "SPECTER-CALL:FROM=2000-VALIDATE:TO=3000-PROCESS\n"
        )
        result = parse_traces(stdout)
        assert result.call_chain == [
            ("1000-MAIN", "2000-VALIDATE"),
            ("2000-VALIDATE", "3000-PROCESS"),
        ]

    def test_malformed_call_ignored(self) -> None:
        result = parse_traces("SPECTER-CALL:GARBAGE\n")
        assert result.call_chain == []


class TestParseVariableSnapshot:
    """@@V:<bid>:<var1>=<val1>:<var2>=<val2> lines."""

    def test_single_variable(self) -> None:
        result = parse_traces("@@V:1:WS-STATUS=00\n")
        assert result.variable_snapshots == {"1": {"WS-STATUS": "00"}}

    def test_multiple_variables(self) -> None:
        result = parse_traces("@@V:5:WS-STATUS=00:WS-FLAG=Y\n")
        assert result.variable_snapshots == {
            "5": {"WS-STATUS": "00", "WS-FLAG": "Y"}
        }

    def test_different_branch_ids(self) -> None:
        stdout = "@@V:1:X=1\n@@V:2:Y=2\n"
        result = parse_traces(stdout)
        assert result.variable_snapshots == {
            "1": {"X": "1"},
            "2": {"Y": "2"},
        }

    def test_malformed_snapshot_no_vars(self) -> None:
        """A @@V line with only a branch id and no vars is consumed but empty."""
        result = parse_traces("@@V:1\n")
        assert result.variable_snapshots == {}


class TestParseSpecterMock:
    """SPECTER-MOCK:<operation> lines."""

    def test_single_mock(self) -> None:
        result = parse_traces("SPECTER-MOCK:READ-ACCOUNT\n")
        assert result.mock_ops == ["READ-ACCOUNT"]

    def test_multiple_mocks(self) -> None:
        stdout = "SPECTER-MOCK:READ-ACCOUNT\nSPECTER-MOCK:WRITE-LOG\n"
        result = parse_traces(stdout)
        assert result.mock_ops == ["READ-ACCOUNT", "WRITE-LOG"]

    def test_empty_operation_ignored(self) -> None:
        result = parse_traces("SPECTER-MOCK:\n")
        assert result.mock_ops == []


class TestMixedOutput:
    """Parsing output that contains all trace types plus noise."""

    def test_mixed_trace_fixture(self, fixtures_dir: Path) -> None:
        fixture_path = fixtures_dir / "trace_mixed.txt"
        stdout = fixture_path.read_text()
        result = parse_traces(stdout)

        assert result.paragraphs_hit == [
            "1000-MAIN",
            "2000-VALIDATE",
            "3000-PROCESS",
            "9000-EXIT",
        ]
        assert result.branches_hit == {
            "1": "T",
            "2": "F",
            "3": "W1",
            "4": "WO",
        }
        assert result.call_chain == [
            ("1000-MAIN", "2000-VALIDATE"),
            ("2000-VALIDATE", "3000-PROCESS"),
        ]
        assert result.variable_snapshots == {
            "1": {"WS-STATUS": "00", "WS-FLAG": "Y"},
            "3": {"WS-AMOUNT": "10000", "WS-LIMIT": "50000", "WS-CODE": "A1"},
        }
        assert result.mock_ops == ["READ-ACCOUNT", "WRITE-LOG"]

    def test_raw_stdout_preserved(self) -> None:
        stdout = "SPECTER-TRACE:1000-MAIN\nsome noise\n"
        result = parse_traces(stdout)
        assert result.raw_stdout == stdout


class TestEmptyAndEdgeCases:
    """Empty input, blank lines, and whitespace handling."""

    def test_empty_string(self) -> None:
        result = parse_traces("")
        assert result.paragraphs_hit == []
        assert result.branches_hit == {}
        assert result.call_chain == []
        assert result.variable_snapshots == {}
        assert result.mock_ops == []
        assert result.raw_stdout == ""

    def test_only_blank_lines(self) -> None:
        result = parse_traces("\n\n\n")
        assert result.paragraphs_hit == []

    def test_non_matching_lines_ignored(self) -> None:
        stdout = "DISPLAY Hello World\nREADY.\nSome COBOL output\n"
        result = parse_traces(stdout)
        assert result.paragraphs_hit == []
        assert result.branches_hit == {}
        assert result.call_chain == []
        assert result.variable_snapshots == {}
        assert result.mock_ops == []

    def test_lines_with_leading_trailing_whitespace(self) -> None:
        stdout = "  SPECTER-TRACE:1000-MAIN  \n  @@B:1:T  \n"
        result = parse_traces(stdout)
        assert result.paragraphs_hit == ["1000-MAIN"]
        assert result.branches_hit == {"1": "T"}


class TestExecutionResultDefaults:
    """Default values for ExecutionResult."""

    def test_defaults(self) -> None:
        result = ExecutionResult()
        assert result.paragraphs_hit == []
        assert result.branches_hit == {}
        assert result.call_chain == []
        assert result.variable_snapshots == {}
        assert result.mock_ops == []
        assert result.exit_code == 0
        assert result.stderr == ""
        assert result.raw_stdout == ""
