"""Tests for cobol_penetrator.tickets.store."""

from __future__ import annotations

from pathlib import Path

import pytest

from cobol_penetrator.tickets.models import (
    BLOCKED,
    CLAIMED,
    CREATED,
    DONE,
    IN_PROGRESS,
    BranchTicket,
    ParagraphTicket,
)
from cobol_penetrator.tickets.store import (
    DuplicateTicketError,
    TicketNotFoundError,
    TicketStore,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def store() -> TicketStore:
    return TicketStore()


def _para(
    paragraph: str,
    call_path: list[str] | None = None,
    status: str = CREATED,
) -> ParagraphTicket:
    """Quick ParagraphTicket factory."""
    return ParagraphTicket(
        id=f"PARA-{paragraph}",
        paragraph=paragraph,
        call_path=call_path or [paragraph],
        status=status,
    )


def _branch(
    branch_id: str,
    direction: str = "T",
    paragraph: str = "2000-VALIDATE",
    status: str = CREATED,
) -> BranchTicket:
    """Quick BranchTicket factory."""
    return BranchTicket(
        id=f"BRANCH-{branch_id}-{direction}",
        branch_id=branch_id,
        direction=direction,
        paragraph=paragraph,
        status=status,
    )


# ------------------------------------------------------------------
# add / get
# ------------------------------------------------------------------


class TestAddAndGet:
    def test_add_and_retrieve(self, store: TicketStore) -> None:
        t = _para("1000-MAIN")
        store.add(t)
        assert store.get("PARA-1000-MAIN") is t

    def test_add_duplicate_raises(self, store: TicketStore) -> None:
        store.add(_para("1000-MAIN"))
        with pytest.raises(DuplicateTicketError):
            store.add(_para("1000-MAIN"))

    def test_get_missing_raises(self, store: TicketStore) -> None:
        with pytest.raises(TicketNotFoundError):
            store.get("NONEXISTENT")


# ------------------------------------------------------------------
# claim_next — priority
# ------------------------------------------------------------------


class TestClaimNext:
    def test_returns_none_when_empty(self, store: TicketStore) -> None:
        assert store.claim_next() is None

    def test_paragraphs_before_branches(self, store: TicketStore) -> None:
        b = _branch("5")
        p = _para("2000-VALIDATE", call_path=["1000-MAIN", "2000-VALIDATE"])
        store.add(b)
        store.add(p)
        claimed = store.claim_next()
        assert claimed is p
        assert claimed.status == CLAIMED

    def test_shorter_call_path_wins(self, store: TicketStore) -> None:
        long_path = _para(
            "3000-DEEP",
            call_path=["1000-MAIN", "2000-VALIDATE", "3000-DEEP"],
        )
        short_path = _para("1000-MAIN", call_path=["1000-MAIN"])
        store.add(long_path)
        store.add(short_path)
        assert store.claim_next() is short_path

    def test_branch_claimed_when_no_paragraphs(self, store: TicketStore) -> None:
        b1 = _branch("10", direction="F")
        b2 = _branch("5", direction="T")
        store.add(b1)
        store.add(b2)
        # Sorted by id: "BRANCH-10-F" < "BRANCH-5-T" (lexicographic)
        claimed = store.claim_next()
        assert claimed is b1

    def test_skips_non_created(self, store: TicketStore) -> None:
        done = _para("1000-MAIN", status=DONE)
        blocked = _para("2000-VALIDATE", status=BLOCKED)
        ready = _para("3000-REPORT", call_path=["1000-MAIN", "3000-REPORT"])
        store.add(done)
        store.add(blocked)
        store.add(ready)
        assert store.claim_next() is ready

    def test_returns_none_when_all_done(self, store: TicketStore) -> None:
        store.add(_para("1000-MAIN", status=DONE))
        store.add(_branch("5", status=BLOCKED))
        assert store.claim_next() is None

    def test_claim_sets_status_to_claimed(self, store: TicketStore) -> None:
        t = _para("1000-MAIN")
        store.add(t)
        claimed = store.claim_next()
        assert claimed.status == CLAIMED

    def test_second_claim_skips_already_claimed(self, store: TicketStore) -> None:
        t1 = _para("1000-MAIN", call_path=["1000-MAIN"])
        t2 = _para("2000-VALIDATE", call_path=["1000-MAIN", "2000-VALIDATE"])
        store.add(t1)
        store.add(t2)
        first = store.claim_next()
        assert first is t1
        second = store.claim_next()
        assert second is t2


# ------------------------------------------------------------------
# open_tickets_exist / done_paragraphs
# ------------------------------------------------------------------


class TestQueryMethods:
    def test_open_tickets_empty_store(self, store: TicketStore) -> None:
        assert store.open_tickets_exist() is False

    def test_open_tickets_with_created(self, store: TicketStore) -> None:
        store.add(_para("1000-MAIN"))
        assert store.open_tickets_exist() is True

    def test_open_tickets_all_done(self, store: TicketStore) -> None:
        store.add(_para("1000-MAIN", status=DONE))
        assert store.open_tickets_exist() is False

    def test_open_tickets_all_blocked(self, store: TicketStore) -> None:
        store.add(_para("1000-MAIN", status=BLOCKED))
        assert store.open_tickets_exist() is False

    def test_open_tickets_mixed(self, store: TicketStore) -> None:
        store.add(_para("1000-MAIN", status=DONE))
        store.add(_para("2000-VALIDATE"))  # CREATED
        assert store.open_tickets_exist() is True

    def test_done_paragraphs_empty(self, store: TicketStore) -> None:
        assert store.done_paragraphs() == set()

    def test_done_paragraphs(self, store: TicketStore) -> None:
        store.add(_para("1000-MAIN", status=DONE))
        store.add(_para("2000-VALIDATE", status=IN_PROGRESS))
        store.add(_branch("5", status=DONE))  # BranchTicket — not counted
        assert store.done_paragraphs() == {"1000-MAIN"}


class TestAllTickets:
    def test_all_tickets_empty(self, store: TicketStore) -> None:
        assert store.all_tickets() == []

    def test_all_tickets_order(self, store: TicketStore) -> None:
        t1 = _para("A")
        t2 = _branch("1")
        t3 = _para("B")
        store.add(t1)
        store.add(t2)
        store.add(t3)
        assert store.all_tickets() == [t1, t2, t3]


# ------------------------------------------------------------------
# JSON round-trip
# ------------------------------------------------------------------


class TestJsonPersistence:
    def test_save_and_load_round_trip(
        self, store: TicketStore, tmp_path: Path
    ) -> None:
        p = _para("1000-MAIN", call_path=["1000-MAIN"])
        p.status = DONE
        p.successful_params = {"WS-IN": "HELLO"}
        p.branches_discovered = ["5", "6"]
        b = _branch("5", direction="T", paragraph="1000-MAIN")
        b.condition_text = "WS-STATUS = '00'"
        b.condition_vars = ["WS-STATUS"]
        store.add(p)
        store.add(b)

        path = tmp_path / "tickets.json"
        store.save(path)

        new_store = TicketStore()
        new_store.load(path)

        loaded_p = new_store.get("PARA-1000-MAIN")
        assert isinstance(loaded_p, ParagraphTicket)
        assert loaded_p.paragraph == "1000-MAIN"
        assert loaded_p.status == DONE
        assert loaded_p.successful_params == {"WS-IN": "HELLO"}
        assert loaded_p.branches_discovered == ["5", "6"]

        loaded_b = new_store.get("BRANCH-5-T")
        assert isinstance(loaded_b, BranchTicket)
        assert loaded_b.condition_text == "WS-STATUS = '00'"
        assert loaded_b.condition_vars == ["WS-STATUS"]

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        store = TicketStore()
        with pytest.raises(FileNotFoundError):
            store.load(tmp_path / "nope.json")


# ------------------------------------------------------------------
# Crash recovery
# ------------------------------------------------------------------


class TestCrashRecovery:
    def test_claimed_reset_to_created(
        self, store: TicketStore, tmp_path: Path
    ) -> None:
        t = _para("1000-MAIN")
        t.status = CLAIMED
        t.assigned_agent = "ReconAgent"
        store.add(t)

        path = tmp_path / "tickets.json"
        store.save(path)

        new_store = TicketStore()
        new_store.load(path)
        recovered = new_store.get("PARA-1000-MAIN")
        assert recovered.status == CREATED
        assert recovered.assigned_agent is None

    def test_in_progress_reset_to_created(
        self, store: TicketStore, tmp_path: Path
    ) -> None:
        t = _branch("5")
        t.status = IN_PROGRESS
        t.assigned_agent = "BranchAgent"
        store.add(t)

        path = tmp_path / "tickets.json"
        store.save(path)

        new_store = TicketStore()
        new_store.load(path)
        recovered = new_store.get("BRANCH-5-T")
        assert recovered.status == CREATED
        assert recovered.assigned_agent is None

    def test_done_and_blocked_preserved(
        self, store: TicketStore, tmp_path: Path
    ) -> None:
        done = _para("1000-MAIN", status=DONE)
        blocked = _para("2000-VALIDATE", status=BLOCKED)
        store.add(done)
        store.add(blocked)

        path = tmp_path / "tickets.json"
        store.save(path)

        new_store = TicketStore()
        new_store.load(path)
        assert new_store.get("PARA-1000-MAIN").status == DONE
        assert new_store.get("PARA-2000-VALIDATE").status == BLOCKED


# ------------------------------------------------------------------
# load_or_create
# ------------------------------------------------------------------


class TestLoadOrCreate:
    def test_loads_existing_file(
        self, store: TicketStore, tmp_path: Path
    ) -> None:
        store.add(_para("1000-MAIN"))
        path = tmp_path / "tickets.json"
        store.save(path)

        new_store = TicketStore()
        new_store.load_or_create(path)
        assert new_store.get("PARA-1000-MAIN").paragraph == "1000-MAIN"

    def test_creates_empty_when_missing(self, tmp_path: Path) -> None:
        store = TicketStore()
        store.load_or_create(tmp_path / "nonexistent.json")
        assert store.all_tickets() == []
