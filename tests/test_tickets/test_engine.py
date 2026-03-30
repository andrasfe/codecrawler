"""Tests for cobol_penetrator.tickets.engine."""

from __future__ import annotations

import pytest

from cobol_penetrator.tickets.engine import (
    DEFAULT_MAX_ATTEMPTS,
    InvalidTransitionError,
    TicketEngine,
)
from cobol_penetrator.tickets.models import (
    BLOCKED,
    CLAIMED,
    CREATED,
    DONE,
    IN_PROGRESS,
    BranchTicket,
    ParagraphTicket,
)
from cobol_penetrator.tickets.store import TicketStore


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def engine() -> TicketEngine:
    return TicketEngine()


# ------------------------------------------------------------------
# Ticket creation
# ------------------------------------------------------------------


class TestCreateEntryTicket:
    def test_creates_paragraph_ticket(self, engine: TicketEngine) -> None:
        t = engine.create_entry_ticket("1000-MAIN")
        assert isinstance(t, ParagraphTicket)
        assert t.id == "PARA-1000-MAIN"
        assert t.paragraph == "1000-MAIN"
        assert t.call_path == ["1000-MAIN"]
        assert t.required_stubs == []
        assert t.status == CREATED

    def test_ticket_in_store(self, engine: TicketEngine) -> None:
        t = engine.create_entry_ticket("1000-MAIN")
        assert engine.store.get(t.id) is t


class TestCreateParagraphTicket:
    def test_creates_with_path_and_stubs(self, engine: TicketEngine) -> None:
        t = engine.create_paragraph_ticket(
            paragraph="2000-VALIDATE",
            call_path=["1000-MAIN", "2000-VALIDATE"],
            required_stubs=["READ-ACCOUNT"],
        )
        assert t.id == "PARA-2000-VALIDATE"
        assert t.call_path == ["1000-MAIN", "2000-VALIDATE"]
        assert t.required_stubs == ["READ-ACCOUNT"]

    def test_defaults_stubs_to_empty(self, engine: TicketEngine) -> None:
        t = engine.create_paragraph_ticket(
            paragraph="2000-VALIDATE",
            call_path=["1000-MAIN", "2000-VALIDATE"],
        )
        assert t.required_stubs == []


class TestCreateBranchTicket:
    def test_creates_branch_ticket(self, engine: TicketEngine) -> None:
        t = engine.create_branch_ticket(
            branch_id="5",
            direction="T",
            paragraph="2000-VALIDATE",
            condition_text="WS-STATUS = '00'",
            condition_vars=["WS-STATUS"],
        )
        assert isinstance(t, BranchTicket)
        assert t.id == "BRANCH-5-T"
        assert t.branch_id == "5"
        assert t.direction == "T"
        assert t.paragraph == "2000-VALIDATE"
        assert t.condition_text == "WS-STATUS = '00'"
        assert t.condition_vars == ["WS-STATUS"]

    def test_defaults_condition_fields(self, engine: TicketEngine) -> None:
        t = engine.create_branch_ticket(
            branch_id="7",
            direction="F",
            paragraph="3000-REPORT",
        )
        assert t.condition_text == ""
        assert t.condition_vars == []


# ------------------------------------------------------------------
# State transitions
# ------------------------------------------------------------------


class TestStateTransitions:
    """Walk through the happy-path lifecycle: CREATED -> CLAIMED -> IN_PROGRESS -> DONE."""

    def test_full_lifecycle(self, engine: TicketEngine) -> None:
        engine.create_entry_ticket("1000-MAIN")
        t = engine.claim_next()
        assert t is not None
        assert t.status == CLAIMED

        engine.start_work(t)
        assert t.status == IN_PROGRESS

        engine.complete(t, params={"WS-IN": "HELLO"})
        assert t.status == DONE
        assert t.successful_params == {"WS-IN": "HELLO"}

    def test_complete_stores_branches_on_paragraph(
        self, engine: TicketEngine
    ) -> None:
        engine.create_entry_ticket("1000-MAIN")
        t = engine.claim_next()
        engine.start_work(t)
        engine.complete(
            t,
            params={"WS-IN": "X"},
            result={"branches_discovered": ["5", "6"]},
        )
        assert isinstance(t, ParagraphTicket)
        assert t.branches_discovered == ["5", "6"]

    def test_complete_stores_snapshot_on_branch(
        self, engine: TicketEngine
    ) -> None:
        engine.create_branch_ticket("5", "T", "2000-VALIDATE")
        t = engine.claim_next()
        engine.start_work(t)
        engine.complete(
            t,
            params={"WS-STATUS": "00"},
            result={"variable_snapshot": {"WS-STATUS": "00"}},
        )
        assert isinstance(t, BranchTicket)
        assert t.variable_snapshot == {"WS-STATUS": "00"}


class TestInvalidTransitions:
    def test_start_work_requires_claimed(self, engine: TicketEngine) -> None:
        t = engine.create_entry_ticket("1000-MAIN")
        # t is CREATED, not CLAIMED
        with pytest.raises(InvalidTransitionError):
            engine.start_work(t)

    def test_complete_requires_in_progress(self, engine: TicketEngine) -> None:
        engine.create_entry_ticket("1000-MAIN")
        t = engine.claim_next()
        # t is CLAIMED, not IN_PROGRESS
        with pytest.raises(InvalidTransitionError):
            engine.complete(t, params={})

    def test_block_requires_claimed_or_in_progress(
        self, engine: TicketEngine
    ) -> None:
        t = engine.create_entry_ticket("1000-MAIN")
        with pytest.raises(InvalidTransitionError):
            engine.block(t)

    def test_block_from_claimed(self, engine: TicketEngine) -> None:
        engine.create_entry_ticket("1000-MAIN")
        t = engine.claim_next()
        engine.block(t)
        assert t.status == BLOCKED

    def test_block_from_in_progress(self, engine: TicketEngine) -> None:
        engine.create_entry_ticket("1000-MAIN")
        t = engine.claim_next()
        engine.start_work(t)
        engine.block(t)
        assert t.status == BLOCKED

    def test_cannot_transition_done_ticket(self, engine: TicketEngine) -> None:
        engine.create_entry_ticket("1000-MAIN")
        t = engine.claim_next()
        engine.start_work(t)
        engine.complete(t, params={})
        with pytest.raises(InvalidTransitionError):
            engine.start_work(t)

    def test_cannot_block_done_ticket(self, engine: TicketEngine) -> None:
        engine.create_entry_ticket("1000-MAIN")
        t = engine.claim_next()
        engine.start_work(t)
        engine.complete(t, params={})
        with pytest.raises(InvalidTransitionError):
            engine.block(t)


# ------------------------------------------------------------------
# Attempt tracking
# ------------------------------------------------------------------


class TestAttemptTracking:
    def test_record_attempt_increments(self, engine: TicketEngine) -> None:
        t = engine.create_entry_ticket("1000-MAIN")
        assert t.attempts == 0
        engine.record_attempt(t)
        assert t.attempts == 1
        engine.record_attempt(t)
        assert t.attempts == 2

    def test_auto_block_at_max_attempts(self) -> None:
        engine = TicketEngine(max_attempts=3)
        t = engine.create_entry_ticket("1000-MAIN")
        engine.record_attempt(t)  # 1
        engine.record_attempt(t)  # 2
        assert t.status == CREATED
        engine.record_attempt(t)  # 3 -> blocked
        assert t.status == BLOCKED

    def test_default_max_attempts(self) -> None:
        engine = TicketEngine()
        assert engine.max_attempts == DEFAULT_MAX_ATTEMPTS

    def test_custom_max_attempts(self) -> None:
        engine = TicketEngine(max_attempts=10)
        assert engine.max_attempts == 10


# ------------------------------------------------------------------
# Delegated queries
# ------------------------------------------------------------------


class TestDelegatedQueries:
    def test_open_tickets_exist(self, engine: TicketEngine) -> None:
        assert engine.open_tickets_exist() is False
        engine.create_entry_ticket("1000-MAIN")
        assert engine.open_tickets_exist() is True

    def test_done_paragraphs(self, engine: TicketEngine) -> None:
        engine.create_entry_ticket("1000-MAIN")
        assert engine.done_paragraphs() == set()
        t = engine.claim_next()
        engine.start_work(t)
        engine.complete(t, params={})
        assert engine.done_paragraphs() == {"1000-MAIN"}


# ------------------------------------------------------------------
# claim_next delegation
# ------------------------------------------------------------------


class TestClaimNextDelegation:
    def test_returns_none_when_empty(self, engine: TicketEngine) -> None:
        assert engine.claim_next() is None

    def test_claim_priority(self, engine: TicketEngine) -> None:
        """ParagraphTickets should be claimed before BranchTickets
        when both have no dependencies."""
        engine.create_branch_ticket("5", "T", "2000-VALIDATE")
        engine.create_entry_ticket("1000-MAIN")
        t = engine.claim_next()
        assert isinstance(t, ParagraphTicket)
        assert t.paragraph == "1000-MAIN"


# ------------------------------------------------------------------
# build_dag
# ------------------------------------------------------------------


def _make_structure(
    entry: str,
    paragraphs: dict[str, list[str]],
    call_graph: dict[str, list[str]],
    branches: dict[str, tuple[str, list[str]]] | None = None,
):
    """Build a minimal ProgramStructure for testing.

    Args:
        entry: Entry paragraph name.
        paragraphs: {name: [branch_ids]} mapping.
        call_graph: {caller: [callees]} mapping.
        branches: {branch_id: (paragraph, [directions])} mapping.
    """
    from cobol_penetrator.mock_reader import (
        BranchInfo,
        ParagraphInfo,
        ProgramStructure,
    )

    para_objs = {}
    for name, branch_ids in paragraphs.items():
        para_objs[name] = ParagraphInfo(
            name=name,
            line_start=1,
            line_end=10,
            source_code="MOCK CODE",
            branches=list(branch_ids),
            performs=call_graph.get(name, []),
        )

    branch_objs = {}
    if branches:
        for bid, (para, dirs) in branches.items():
            branch_objs[bid] = BranchInfo(
                id=bid,
                paragraph=para,
                condition_text=f"COND-{bid}",
                condition_vars=[f"VAR-{bid}"],
                directions=list(dirs),
            )

    return ProgramStructure(
        entry_paragraph=entry,
        paragraphs=para_objs,
        branches=branch_objs,
        call_graph=call_graph,
    )


class TestBuildDag:
    """Verify build_dag creates correct ticket DAG from call graph."""

    def test_linear_chain(self, engine: TicketEngine) -> None:
        """A -> B -> C creates 3 paragraph tickets with correct deps."""
        structure = _make_structure(
            entry="A",
            paragraphs={"A": [], "B": [], "C": []},
            call_graph={"A": ["B"], "B": ["C"]},
        )
        count = engine.build_dag(structure)
        assert count == 3

        a = engine.store.get("PARA-A")
        b = engine.store.get("PARA-B")
        c = engine.store.get("PARA-C")
        assert a.depends_on == []
        assert b.depends_on == ["PARA-A"]
        assert c.depends_on == ["PARA-B"]
        assert b.call_path == ["A", "B"]
        assert c.call_path == ["A", "B", "C"]

    def test_with_branches(self, engine: TicketEngine) -> None:
        """Branches depend on their containing paragraph."""
        structure = _make_structure(
            entry="MAIN",
            paragraphs={"MAIN": ["1"], "SUB": ["2"]},
            call_graph={"MAIN": ["SUB"]},
            branches={
                "1": ("MAIN", ["T", "F"]),
                "2": ("SUB", ["T", "F"]),
            },
        )
        count = engine.build_dag(structure)
        # 2 paragraphs + 4 branches = 6
        assert count == 6

        b1t = engine.store.get("BRANCH-1-T")
        b1f = engine.store.get("BRANCH-1-F")
        b2t = engine.store.get("BRANCH-2-T")
        assert b1t.depends_on == ["PARA-MAIN"]
        assert b1f.depends_on == ["PARA-MAIN"]
        assert b2t.depends_on == ["PARA-SUB"]

    def test_cycle_handled(self, engine: TicketEngine) -> None:
        """A -> B -> A should not loop; each paragraph gets one ticket."""
        structure = _make_structure(
            entry="A",
            paragraphs={"A": [], "B": []},
            call_graph={"A": ["B"], "B": ["A"]},
        )
        count = engine.build_dag(structure)
        assert count == 2  # one ticket per paragraph

    def test_diamond(self, engine: TicketEngine) -> None:
        """A -> B, A -> C, B -> D, C -> D — D created once with shortest path."""
        structure = _make_structure(
            entry="A",
            paragraphs={"A": [], "B": [], "C": [], "D": []},
            call_graph={"A": ["B", "C"], "B": ["D"], "C": ["D"]},
        )
        count = engine.build_dag(structure)
        assert count == 4  # A, B, C, D

        d = engine.store.get("PARA-D")
        # D depends on whichever parent was dequeued first (B, since A->[B,C])
        assert d.depends_on == ["PARA-B"]
        assert d.call_path == ["A", "B", "D"]

    def test_unreachable_paragraph_skipped(self, engine: TicketEngine) -> None:
        """Paragraphs not reachable from entry are not in DAG."""
        structure = _make_structure(
            entry="A",
            paragraphs={"A": [], "B": [], "ORPHAN": []},
            call_graph={"A": ["B"]},
        )
        count = engine.build_dag(structure)
        assert count == 2  # A and B only
        with pytest.raises(Exception):
            engine.store.get("PARA-ORPHAN")
