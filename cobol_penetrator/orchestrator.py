"""Main agent loop orchestrator for the COBOL penetration system.

Implements the core loop from the spec (lines 124-172):
1. Parse mock.cbl for program structure.
2. Create initial entry paragraph ticket.
3. Loop: claim ticket, select agent, build context, generate params,
   execute, check result, cascade tickets.
4. Track coverage and save state after each iteration.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from cobol_penetrator.agents.base import AgentContext, BaseAgent
from cobol_penetrator.agents.branch import BranchAgent
from cobol_penetrator.agents.paragraph import ParagraphAgent
from cobol_penetrator.agents.recon import ReconAgent
from cobol_penetrator.config import PenetratorConfig
from cobol_penetrator.executor import execute
from cobol_penetrator.mock_reader import ProgramStructure, parse_mock_structure
from cobol_penetrator.reports.coverage import CoverageTracker
from cobol_penetrator.reports.params import save_successful_params
from cobol_penetrator.tickets import (
    BranchTicket,
    ParagraphTicket,
    TicketEngine,
    TicketStore,
)
from cobol_penetrator.llm_providers import get_provider_from_env
from cobol_penetrator.trace_parser import ExecutionResult

logger = logging.getLogger(__name__)


def select_agent(
    ticket: ParagraphTicket | BranchTicket,
    provider: Any,
    config: PenetratorConfig,
) -> BaseAgent:
    """Select the appropriate agent for a ticket type.

    - Entry-point ParagraphTickets (no call path or single-element path)
      get the ReconAgent.
    - Deeper ParagraphTickets get the ParagraphAgent.
    - BranchTickets get the BranchAgent.

    Args:
        ticket: The ticket to find an agent for.
        provider: The LLM provider instance.
        config: The penetrator configuration.

    Returns:
        An agent instance appropriate for the ticket type.

    Raises:
        ValueError: If the ticket type is not recognised.
    """
    if isinstance(ticket, ParagraphTicket):
        if not ticket.call_path or len(ticket.call_path) <= 1:
            return ReconAgent(provider)
        return ParagraphAgent(provider)
    elif isinstance(ticket, BranchTicket):
        return BranchAgent(provider)
    raise ValueError(f"Unknown ticket type: {type(ticket)}")


def ticket_target_reached(
    ticket: ParagraphTicket | BranchTicket,
    result: ExecutionResult,
) -> bool:
    """Check if the execution result reached the ticket's target.

    For ParagraphTickets, success means the target paragraph appeared
    in ``result.paragraphs_hit``.  For BranchTickets, success means
    the target branch ID was hit with the target direction.

    Args:
        ticket: The ticket whose target we are checking.
        result: The execution result from running the COBOL binary.

    Returns:
        ``True`` if the target was reached, ``False`` otherwise.
    """
    if isinstance(ticket, ParagraphTicket):
        return ticket.paragraph in result.paragraphs_hit
    elif isinstance(ticket, BranchTicket):
        return (
            ticket.branch_id in result.branches_hit
            and result.branches_hit[ticket.branch_id] == ticket.direction
        )
    return False


async def run(config: PenetratorConfig) -> dict:
    """Main orchestration loop.

    Implements the agent loop from the spec:
    1. Parse the mock.cbl file for program structure.
    2. Load or create the ticket store (with crash recovery on resume).
    3. Create the initial entry paragraph ticket if this is a fresh run.
    4. Loop: claim tickets, dispatch agents, execute, cascade.
    5. Save final state and return a summary dict.

    Args:
        config: The penetrator configuration.

    Returns:
        A summary dict with keys:
            - ``executions``: Number of COBOL binary runs.
            - ``coverage_pct``: Final coverage percentage.
            - ``total_tickets``: Total tickets created.
            - ``done_tickets``: Tickets completed successfully.
            - ``blocked_tickets``: Tickets that exhausted their attempts.
    """
    # 1a. Parse mock.cbl
    structure = parse_mock_structure(config.mock_cbl)
    logger.info(
        "Parsed structure: %d paragraphs, %d branches, entry=%s",
        len(structure.paragraphs),
        len(structure.branches),
        structure.entry_paragraph,
    )

    # 1b. Build field report from DATA DIVISION
    from cobol_penetrator.analysis.field_report import build_field_report

    field_report = None
    if config.heuristic_mode != "llm_only":
        try:
            field_report = build_field_report(config.mock_cbl, structure)
            logger.info(
                "Field report: %d variables analyzed",
                len(field_report.fields),
            )
        except Exception:
            logger.warning(
                "Failed to build field report, continuing without",
                exc_info=True,
            )
            field_report = None

    # 1c. Initialize heuristic walker
    from cobol_penetrator.heuristics.heuristic_walker import HeuristicWalker

    walker = HeuristicWalker(field_report)

    # 2. Load or create ticket store
    store = TicketStore()
    store.load_or_create(config.tickets_path)
    engine = TicketEngine(store, max_attempts=config.max_attempts)

    # 3. Create initial ticket if fresh run
    if not config.resume:
        engine.create_entry_ticket(structure.entry_paragraph)

    # 4. Create LLM provider
    provider = get_provider_from_env()

    # 5. Coverage tracking — load existing state if resuming
    if config.resume and config.coverage_path.exists():
        coverage = CoverageTracker.load(config.coverage_path, structure)
    else:
        coverage = CoverageTracker(structure)

    # 6. Budget tracking
    executions = 0
    start_time = time.time()

    # 7. Main loop
    while store.open_tickets_exist() and executions < config.budget:
        elapsed = time.time() - start_time
        if elapsed > config.timeout:
            logger.warning("Timeout reached (%ds)", config.timeout)
            break

        ticket = engine.claim_next()
        if ticket is None:
            logger.info("No more claimable tickets")
            break

        engine.start_work(ticket)

        agent = select_agent(ticket, provider, config)
        logger.debug(
            "Iteration %d: ticket=%s, agent=%s",
            executions + 1,
            ticket.id,
            agent.name,
        )

        try:
            context = await agent.build_context(
                ticket, structure, config.mock_cbl
            )
            # Attach field report and execution history to context
            context.field_report = field_report
            # TODO: populate execution_history from prior attempts on
            # this ticket once a per-ticket history store is added.

            params = await agent.generate_params(context)

            # On retry attempts, merge heuristic suggestions (hybrid mode)
            if (
                config.heuristic_mode != "llm_only"
                and ticket.attempts > 0
                and field_report is not None
            ):
                if isinstance(ticket, BranchTicket):
                    h_params = walker.suggest_params_for_branch(
                        ticket.branch_id,
                        ticket.direction,
                        ticket.condition_vars,
                        ticket.condition_text,
                    )
                else:
                    if walker.corpus.entries:
                        h_params = walker.mutate_params(params)
                    else:
                        h_params = walker.generate_exploratory_params()

                # Merge: heuristic fills gaps, does not overwrite LLM
                for k, v in h_params.get("input_state", {}).items():
                    params.setdefault("input_state", {}).setdefault(k, v)
                for k, v in h_params.get("stubs", {}).items():
                    params.setdefault("stubs", {}).setdefault(k, v)

        except Exception:
            logger.exception(
                "Agent %s failed for ticket %s", agent.name, ticket.id
            )
            engine.record_attempt(ticket)
            if ticket.status != "BLOCKED":
                ticket.status = "CREATED"
                ticket.assigned_agent = None
            store.save(config.tickets_path)
            continue

        try:
            result = execute(
                config.executable, params, timeout=30
            )
        except Exception:
            logger.exception(
                "Execution failed for ticket %s", ticket.id
            )
            engine.record_attempt(ticket)
            if ticket.status != "BLOCKED":
                ticket.status = "CREATED"
                ticket.assigned_agent = None
            store.save(config.tickets_path)
            continue

        # Record result in the heuristic walker for corpus tracking
        walker.record_result(params, result)

        executions += 1

        if ticket_target_reached(ticket, result):
            logger.info(
                "Ticket %s target reached on execution %d",
                ticket.id,
                executions,
            )

            # Build result metadata for engine.complete()
            result_meta: dict[str, Any] = {}
            if isinstance(ticket, ParagraphTicket):
                # Discover branches within this paragraph
                para_branch_ids = set(structure.branches_in(ticket.paragraph))
                result_meta["branches_discovered"] = [
                    bid
                    for bid in result.branches_hit
                    if bid in para_branch_ids
                ]
            if isinstance(ticket, BranchTicket):
                result_meta["variable_snapshot"] = (
                    result.variable_snapshots.get(ticket.branch_id)
                )

            engine.complete(ticket, params, result_meta)

            # Cascade: open tickets for branches and called paragraphs
            if isinstance(ticket, ParagraphTicket):
                _cascade_branch_tickets(engine, structure, ticket)
                _cascade_paragraph_tickets(
                    engine, store, result, ticket
                )

            coverage.update(result)
            save_successful_params(ticket, params, config.params_dir)
        else:
            engine.record_attempt(ticket)
            # If the ticket was not auto-blocked, reset it to CREATED
            # so it can be claimed again on the next loop iteration.
            if ticket.status != "BLOCKED":
                ticket.status = "CREATED"
                ticket.assigned_agent = None

        store.save(config.tickets_path)

    # Save final state
    coverage.save(config.coverage_path)
    store.save(config.tickets_path)

    all_tickets = store.all_tickets()
    summary = {
        "executions": executions,
        "coverage_pct": coverage.coverage_pct,
        "total_tickets": len(all_tickets),
        "done_tickets": len(
            [t for t in all_tickets if t.status == "DONE"]
        ),
        "blocked_tickets": len(
            [t for t in all_tickets if t.status == "BLOCKED"]
        ),
    }

    logger.info("Run complete: %s", summary)
    return summary


def _cascade_branch_tickets(
    engine: TicketEngine,
    structure: ProgramStructure,
    ticket: ParagraphTicket,
) -> None:
    """Create branch tickets for all branches in the completed paragraph.

    Args:
        engine: The ticket engine for creating tickets.
        structure: The program structure.
        ticket: The completed paragraph ticket.
    """
    for branch_id in structure.branches_in(ticket.paragraph):
        branch_info = structure.branches[branch_id]
        for direction in branch_info.directions:
            try:
                engine.create_branch_ticket(
                    branch_id=branch_id,
                    direction=direction,
                    paragraph=ticket.paragraph,
                    condition_text=branch_info.condition_text,
                    condition_vars=branch_info.condition_vars,
                )
            except Exception:
                # Duplicate ticket — already exists from a prior run
                logger.debug(
                    "Branch ticket BRANCH-%s-%s already exists",
                    branch_id,
                    direction,
                )


def _cascade_paragraph_tickets(
    engine: TicketEngine,
    store: TicketStore,
    result: ExecutionResult,
    ticket: ParagraphTicket,
) -> None:
    """Create paragraph tickets for callees discovered in the execution.

    Args:
        engine: The ticket engine for creating tickets.
        store: The ticket store for checking done paragraphs.
        result: The execution result containing the call chain.
        ticket: The completed paragraph ticket.
    """
    done_paras = store.done_paragraphs()
    for _caller, callee in result.call_chain:
        if callee not in done_paras:
            try:
                engine.create_paragraph_ticket(
                    paragraph=callee,
                    call_path=list(ticket.call_path) + [callee],
                )
            except Exception:
                # Duplicate ticket — already exists
                logger.debug(
                    "Paragraph ticket PARA-%s already exists", callee
                )
