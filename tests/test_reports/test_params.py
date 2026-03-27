"""Tests for save_successful_params."""

from __future__ import annotations

import json
from pathlib import Path

from cobol_penetrator.reports.params import save_successful_params
from cobol_penetrator.tickets.models import BranchTicket, ParagraphTicket


class TestSaveSuccessfulParams:
    """Tests for the save_successful_params function."""

    def test_saves_paragraph_ticket_params(self, tmp_path: Path) -> None:
        """Saves params for a ParagraphTicket as JSON."""
        ticket = ParagraphTicket(
            id="PARA-1000-MAIN",
            paragraph="1000-MAIN",
            call_path=["1000-MAIN"],
        )
        params = {
            "input_state": {"WS-STATUS": "00"},
            "stubs": {"READ-ACCOUNT": {"alpha_status": "OK"}},
        }

        result_path = save_successful_params(ticket, params, tmp_path)

        assert result_path.exists()
        assert result_path.name == "PARA-1000-MAIN.json"

        data = json.loads(result_path.read_text())
        assert data["ticket_id"] == "PARA-1000-MAIN"
        assert data["ticket_type"] == "ParagraphTicket"
        assert data["params"] == params

    def test_saves_branch_ticket_params(self, tmp_path: Path) -> None:
        """Saves params for a BranchTicket as JSON."""
        ticket = BranchTicket(
            id="BRANCH-5-T",
            branch_id="5",
            direction="T",
            paragraph="2000-VALIDATE",
        )
        params = {
            "input_state": {"WS-FLAG": "Y"},
            "stubs": {},
        }

        result_path = save_successful_params(ticket, params, tmp_path)

        assert result_path.exists()
        data = json.loads(result_path.read_text())
        assert data["ticket_id"] == "BRANCH-5-T"
        assert data["ticket_type"] == "BranchTicket"

    def test_creates_output_directory(self, tmp_path: Path) -> None:
        """Creates the output directory if it does not exist."""
        ticket = ParagraphTicket(
            id="PARA-TEST",
            paragraph="TEST",
        )
        output_dir = tmp_path / "deep" / "nested"
        result_path = save_successful_params(
            ticket, {"input_state": {}, "stubs": {}}, output_dir
        )
        assert result_path.exists()
        assert result_path.parent == output_dir

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        """The returned path matches the expected file location."""
        ticket = ParagraphTicket(id="PARA-ABC", paragraph="ABC")
        result_path = save_successful_params(
            ticket, {"input_state": {}}, tmp_path
        )
        assert result_path == tmp_path / "PARA-ABC.json"

    def test_empty_params(self, tmp_path: Path) -> None:
        """Handles empty params dict gracefully."""
        ticket = ParagraphTicket(id="PARA-EMPTY", paragraph="EMPTY")
        result_path = save_successful_params(ticket, {}, tmp_path)
        data = json.loads(result_path.read_text())
        assert data["params"] == {}
