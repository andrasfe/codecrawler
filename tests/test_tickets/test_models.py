"""Tests for cobol_penetrator.tickets.models."""

from __future__ import annotations

from cobol_penetrator.tickets.models import (
    BLOCKED,
    CLAIMED,
    CREATED,
    DONE,
    IN_PROGRESS,
    BranchTicket,
    ParagraphTicket,
)


# ------------------------------------------------------------------
# ParagraphTicket
# ------------------------------------------------------------------


class TestParagraphTicketCreation:
    """Verify ParagraphTicket defaults and field access."""

    def test_minimal_creation(self) -> None:
        t = ParagraphTicket(id="PARA-1000-MAIN", paragraph="1000-MAIN")
        assert t.id == "PARA-1000-MAIN"
        assert t.paragraph == "1000-MAIN"
        assert t.status == CREATED
        assert t.assigned_agent is None
        assert t.call_path == []
        assert t.required_stubs == []
        assert t.successful_params is None
        assert t.branches_discovered == []
        assert t.attempts == 0
        assert t.created_at  # non-empty string
        assert t.updated_at

    def test_full_creation(self) -> None:
        t = ParagraphTicket(
            id="PARA-2000-VALIDATE",
            paragraph="2000-VALIDATE",
            status=IN_PROGRESS,
            assigned_agent="ParagraphAgent",
            call_path=["1000-MAIN", "2000-VALIDATE"],
            required_stubs=["READ-ACCOUNT"],
            successful_params={"WS-STATUS": "00"},
            branches_discovered=["5", "6"],
            attempts=3,
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:01:00+00:00",
        )
        assert t.status == IN_PROGRESS
        assert t.assigned_agent == "ParagraphAgent"
        assert t.call_path == ["1000-MAIN", "2000-VALIDATE"]
        assert t.required_stubs == ["READ-ACCOUNT"]
        assert t.successful_params == {"WS-STATUS": "00"}
        assert t.branches_discovered == ["5", "6"]
        assert t.attempts == 3

    def test_id_pattern_convention(self) -> None:
        """IDs should follow the PARA-<paragraph> convention."""
        t = ParagraphTicket(id="PARA-3000-REPORT", paragraph="3000-REPORT")
        assert t.id.startswith("PARA-")
        assert t.paragraph in t.id

    def test_default_lists_are_independent(self) -> None:
        """Each instance should get its own mutable default lists."""
        t1 = ParagraphTicket(id="PARA-A", paragraph="A")
        t2 = ParagraphTicket(id="PARA-B", paragraph="B")
        t1.call_path.append("A")
        assert t2.call_path == []


# ------------------------------------------------------------------
# BranchTicket
# ------------------------------------------------------------------


class TestBranchTicketCreation:
    """Verify BranchTicket defaults and field access."""

    def test_minimal_creation(self) -> None:
        t = BranchTicket(
            id="BRANCH-5-T",
            branch_id="5",
            direction="T",
            paragraph="2000-VALIDATE",
        )
        assert t.id == "BRANCH-5-T"
        assert t.branch_id == "5"
        assert t.direction == "T"
        assert t.paragraph == "2000-VALIDATE"
        assert t.condition_text == ""
        assert t.condition_vars == []
        assert t.status == CREATED
        assert t.assigned_agent is None
        assert t.successful_params is None
        assert t.variable_snapshot is None
        assert t.attempts == 0
        assert t.created_at
        assert t.updated_at

    def test_full_creation(self) -> None:
        t = BranchTicket(
            id="BRANCH-5-F",
            branch_id="5",
            direction="F",
            paragraph="2000-VALIDATE",
            condition_text="WS-STATUS = '00'",
            condition_vars=["WS-STATUS"],
            status=DONE,
            assigned_agent="BranchAgent",
            successful_params={"WS-STATUS": "99"},
            variable_snapshot={"WS-STATUS": "99", "WS-FLAG": "N"},
            attempts=2,
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:02:00+00:00",
        )
        assert t.direction == "F"
        assert t.condition_vars == ["WS-STATUS"]
        assert t.variable_snapshot == {"WS-STATUS": "99", "WS-FLAG": "N"}

    def test_id_pattern_convention(self) -> None:
        """IDs should follow the BRANCH-<id>-<direction> convention."""
        t = BranchTicket(
            id="BRANCH-12-W1",
            branch_id="12",
            direction="W1",
            paragraph="3000-REPORT",
        )
        assert t.id.startswith("BRANCH-")
        assert t.branch_id in t.id
        assert t.direction in t.id

    def test_default_lists_are_independent(self) -> None:
        t1 = BranchTicket(id="B-1-T", branch_id="1", direction="T", paragraph="X")
        t2 = BranchTicket(id="B-2-T", branch_id="2", direction="T", paragraph="Y")
        t1.condition_vars.append("WS-FOO")
        assert t2.condition_vars == []


# ------------------------------------------------------------------
# Status constants
# ------------------------------------------------------------------


class TestStatusConstants:
    """Status constants are plain strings."""

    def test_values(self) -> None:
        assert CREATED == "CREATED"
        assert CLAIMED == "CLAIMED"
        assert IN_PROGRESS == "IN_PROGRESS"
        assert DONE == "DONE"
        assert BLOCKED == "BLOCKED"

    def test_default_status_is_created(self) -> None:
        p = ParagraphTicket(id="P", paragraph="P")
        b = BranchTicket(id="B", branch_id="1", direction="T", paragraph="P")
        assert p.status == CREATED
        assert b.status == CREATED
