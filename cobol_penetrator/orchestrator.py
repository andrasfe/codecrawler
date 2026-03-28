"""Main agent loop orchestrator for the COBOL penetration system.

Enhanced with:
- Multi-turn agent execution (multiple LLM calls per ticket)
- Static call graph cascading (not just SPECTER-CALL traces)
- Paragraphs-hit cascading (auto-create tickets for newly seen paragraphs)
- Agent memory (execution history passed to agents on retries)
- Aggressive coverage-driven exploration
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
from cobol_penetrator.knowledge import LearnedKnowledge
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
    """Select the appropriate agent for a ticket type."""
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
    """Check if the execution result reached the ticket's target."""
    if isinstance(ticket, ParagraphTicket):
        return ticket.paragraph in result.paragraphs_hit
    elif isinstance(ticket, BranchTicket):
        return (
            ticket.branch_id in result.branches_hit
            and result.branches_hit[ticket.branch_id] == ticket.direction
        )
    return False


def _cascade_from_trace(
    engine: TicketEngine,
    store: TicketStore,
    structure: ProgramStructure,
    result: ExecutionResult,
    source_ticket: ParagraphTicket,
) -> int:
    """Create tickets for ALL paragraphs seen in trace output + static call graph.

    This is the key enhancement: instead of only cascading from SPECTER-CALL
    traces, we cascade from every paragraph that appeared in the execution
    AND their static callees from the call graph.

    Returns the number of new tickets created.
    """
    created = 0
    done_paras = store.done_paragraphs()
    existing_ids = {t.id for t in store.all_tickets()}

    # 1. Every paragraph hit in the trace gets a ticket (if not already done)
    for para in result.paragraphs_hit:
        if para in structure.paragraphs and para not in done_paras:
            ticket_id = f"PARA-{para}"
            if ticket_id not in existing_ids:
                try:
                    engine.create_paragraph_ticket(
                        paragraph=para,
                        call_path=list(source_ticket.call_path) + [para],
                    )
                    created += 1
                    existing_ids.add(ticket_id)
                except Exception:
                    pass

    # 2. For every hit paragraph, also cascade to its static callees
    for para in result.paragraphs_hit:
        callees = structure.call_graph.get(para, [])
        for callee in callees:
            if callee in structure.paragraphs and callee not in done_paras:
                ticket_id = f"PARA-{callee}"
                if ticket_id not in existing_ids:
                    try:
                        engine.create_paragraph_ticket(
                            paragraph=callee,
                            call_path=list(source_ticket.call_path) + [para, callee],
                        )
                        created += 1
                        existing_ids.add(ticket_id)
                    except Exception:
                        pass

    # 3. Original SPECTER-CALL cascading (if available)
    for _caller, callee in result.call_chain:
        if callee in structure.paragraphs and callee not in done_paras:
            ticket_id = f"PARA-{callee}"
            if ticket_id not in existing_ids:
                try:
                    engine.create_paragraph_ticket(
                        paragraph=callee,
                        call_path=list(source_ticket.call_path) + [callee],
                    )
                    created += 1
                    existing_ids.add(ticket_id)
                except Exception:
                    pass

    return created


def _cascade_branch_tickets(
    engine: TicketEngine,
    structure: ProgramStructure,
    ticket: ParagraphTicket,
) -> None:
    """Create branch tickets for all branches in the completed paragraph."""
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
                pass


async def _multi_turn_execute(
    agent: BaseAgent,
    ticket: ParagraphTicket | BranchTicket,
    structure: ProgramStructure,
    config: PenetratorConfig,
    field_report: Any,
    walker: Any,
    execution_history: list[dict],
    coverage: CoverageTracker | None = None,
    max_turns: int = 3,
    knowledge: LearnedKnowledge | None = None,
) -> tuple[dict | None, ExecutionResult | None]:
    """Execute multiple turns of agent -> execute -> analyze for a single ticket.

    Each turn:
    1. Build context with execution history from prior turns
    2. Generate params (LLM + heuristics)
    3. Execute COBOL binary
    4. If target reached, record success but continue exploring
    5. Otherwise, add result to history and try again

    Returns (params, result) on success, or (None, last_result) on failure.
    """
    best_result = None
    best_params = None
    target_reached_turn: int | None = None

    for turn in range(max_turns):
        try:
            context = await agent.build_context(ticket, structure, config.mock_cbl)
            context.field_report = field_report
            context.execution_history = list(execution_history)
            context.knowledge = knowledge

            # Inject parent params from knowledge if available
            if knowledge is not None and context.parent_params is None:
                if isinstance(ticket, ParagraphTicket) and ticket.call_path:
                    context.parent_params = knowledge.get_parent_params(
                        ticket.call_path
                    )
                elif isinstance(ticket, BranchTicket):
                    context.parent_params = knowledge.successful_params.get(
                        ticket.paragraph
                    )

            params = await agent.generate_params(context)

            # On retries, use heuristics more aggressively
            if turn > 0 and field_report is not None:
                if isinstance(ticket, BranchTicket):
                    h_params = walker.suggest_params_for_branch(
                        ticket.branch_id, ticket.direction,
                        ticket.condition_vars, ticket.condition_text,
                    )
                elif walker.corpus.entries:
                    h_params = walker.mutate_params(params)
                else:
                    h_params = walker.generate_exploratory_params()

                # On later turns, heuristics OVERRIDE LLM (not just fill gaps)
                if turn >= 2:
                    for k, v in h_params.get("input_state", {}).items():
                        params.setdefault("input_state", {})[k] = v
                    for k, v in h_params.get("stubs", {}).items():
                        params.setdefault("stubs", {})[k] = v
                else:
                    for k, v in h_params.get("input_state", {}).items():
                        params.setdefault("input_state", {}).setdefault(k, v)
                    for k, v in h_params.get("stubs", {}).items():
                        params.setdefault("stubs", {}).setdefault(k, v)

        except Exception:
            logger.exception("Agent failed on turn %d for ticket %s", turn + 1, ticket.id)
            continue

        try:
            result = execute(config.executable, params, timeout=30)
        except Exception:
            logger.exception("Execution failed on turn %d for ticket %s", turn + 1, ticket.id)
            continue

        walker.record_result(params, result)
        best_result = result
        best_params = params

        # Update global coverage on EVERY execution (not just ticket success)
        if coverage is not None:
            coverage.update(result)

        # Record every execution into the shared knowledge store
        if knowledge is not None:
            knowledge.record_execution(params, result, ticket)

        # Record this turn in history for the next turn
        execution_history.append({
            "turn": turn + 1,
            "params": params,
            "paragraphs_hit": list(set(result.paragraphs_hit)),
            "branches_hit": dict(result.branches_hit),
            "target_reached": ticket_target_reached(ticket, result),
        })

        if ticket_target_reached(ticket, result):
            if target_reached_turn is None:
                target_reached_turn = turn
                logger.info(
                    "Ticket %s target reached on turn %d",
                    ticket.id, turn + 1,
                )
            # On the last turn or if we've explored enough, return
            if turn >= max_turns - 1:
                return params, result
            # Otherwise continue exploring for additional branch coverage
            logger.debug(
                "Ticket %s: target reached, continuing exploration "
                "(turn %d/%d)",
                ticket.id, turn + 1, max_turns,
            )
            continue

        logger.debug(
            "Ticket %s turn %d: target not reached, hit %d paragraphs",
            ticket.id, turn + 1, len(set(result.paragraphs_hit)),
        )

    # If we ever reached the target, return the best success result
    if target_reached_turn is not None:
        return best_params, best_result

    return best_params, best_result


async def run(config: PenetratorConfig) -> dict:
    """Main orchestration loop with multi-turn agents and aggressive cascading."""

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
            logger.info("Field report: %d variables analyzed", len(field_report.fields))
        except Exception:
            logger.warning("Failed to build field report", exc_info=True)

    # 1c. Initialize heuristic walker
    from cobol_penetrator.heuristics.heuristic_walker import HeuristicWalker
    walker = HeuristicWalker(field_report)

    # 2. Load or create ticket store
    store = TicketStore()
    store.load_or_create(config.tickets_path)
    engine = TicketEngine(store, max_attempts=config.max_attempts)

    # 2b. Load or create shared knowledge store
    knowledge = (
        LearnedKnowledge.load(config.knowledge_path)
        if config.resume
        else LearnedKnowledge()
    )

    # 3. Create initial ticket if fresh run
    if not config.resume:
        engine.create_entry_ticket(structure.entry_paragraph)

    # 4. Create LLM provider
    provider = get_provider_from_env()

    # 5. Coverage tracking
    if config.resume and config.coverage_path.exists():
        coverage = CoverageTracker.load(config.coverage_path, structure)
    else:
        coverage = CoverageTracker(structure)

    # 6. Budget tracking
    executions = 0
    start_time = time.time()

    # 6a. Baseline execution with EMPTY params to establish success-path coverage
    if not config.resume:
        try:
            baseline_params = {"input_state": {}, "stubs": {}}
            baseline_result = execute(config.executable, baseline_params, timeout=30)
            coverage.update(baseline_result)
            walker.record_result(baseline_params, baseline_result)
            knowledge.record_execution(baseline_params, baseline_result)
            executions += 1
            logger.info(
                "Baseline: %d paragraphs, %d branches hit",
                len(set(baseline_result.paragraphs_hit)),
                len(baseline_result.branches_hit),
            )
        except Exception:
            logger.debug("Baseline execution failed")

    # 6b. FAST fault exploration phase (SKIPPED — position sequencing is more effective)
    if False and field_report and not config.resume:
        from cobol_penetrator.heuristics.stub_fault_table import fault_values_for
        logger.info("Pre-scan: running stub fault sweeps to discover error paths")
        all_fault_values = (
            fault_values_for("status_file")
            + fault_values_for("status_sql")
            + ["GE", "GB", "AI", "II"]  # DLI-specific
        )
        # Deduplicate
        seen_fv: set[str] = set()
        unique_faults = []
        for fv in all_fault_values:
            s = str(fv)
            if s not in seen_fv:
                seen_fv.add(s)
                unique_faults.append(s)

        pre_scan_new = 0
        for stub_op in field_report.stub_operations:
            for fv in unique_faults:
                if executions >= min(config.budget, 50):  # cap pre-scan at 50
                    break
                params = {"input_state": {}, "stubs": {stub_op: fv}}
                try:
                    result = execute(config.executable, params, timeout=10)
                    executions += 1
                    coverage.update(result)
                    walker.record_result(params, result)
                    knowledge.record_execution(params, result)
                    new_paras = set(result.paragraphs_hit) - set(coverage.state.hit_paragraphs[:-len(result.paragraphs_hit)] if len(coverage.state.hit_paragraphs) > len(result.paragraphs_hit) else [])
                except Exception:
                    pass
            if executions >= min(config.budget, 50):
                break

        # Also try pairwise stub faults
        import itertools
        for op1, op2 in itertools.combinations(field_report.stub_operations[:4], 2):
            if executions >= min(config.budget, 80):
                break
            for fv in ["GE", "23", "10"]:
                if executions >= min(config.budget, 80):
                    break
                params = {"input_state": {}, "stubs": {op1: fv, op2: fv}}
                try:
                    result = execute(config.executable, params, timeout=10)
                    executions += 1
                    coverage.update(result)
                    walker.record_result(params, result)
                    knowledge.record_execution(params, result)
                except Exception:
                    pass

        logger.info(
            "Pre-scan complete: %d executions, coverage %.1f%% (%d/%d paragraphs)",
            executions, coverage.coverage_pct,
            len(coverage.state.hit_paragraphs), coverage.state.total_paragraphs,
        )

    # 6c. Position-aware stub sequencing
    # The COBOL mock reads records in FIFO order. Each iteration of the
    # main loop consumes N records (one per SPECTER-MOCK operation).
    # By injecting fault values at specific POSITIONS in the sequence,
    # we can flip branches that depend on specific stub outcomes.
    if not config.resume and executions < config.budget:
        # Discover the mock operation sequence from baseline
        try:
            baseline_out = execute(
                config.executable, {"input_state": {}, "stubs": {}}, timeout=30
            )
            mock_ops = baseline_out.mock_ops
            # Find the repeating pattern (one iteration of the main loop)
            if mock_ops:
                # Detect cycle: find shortest prefix that repeats
                cycle_len = 0
                for cl in range(1, min(len(mock_ops) // 2 + 1, 20)):
                    pattern = mock_ops[:cl]
                    if mock_ops[cl:2*cl] == pattern:
                        cycle_len = cl
                        break
                if cycle_len == 0:
                    cycle_len = min(len(mock_ops), 10)

                logger.info(
                    "Position-aware sequencing: %d mock ops, cycle=%d (%s)",
                    len(mock_ops), cycle_len, mock_ops[:cycle_len],
                )

                # For each position in the cycle, try fault values
                fault_values = [
                    "GE", "GB", "II", "10", "23", "35", "AI",
                    "00", "N", "Y", "A", "D", "04", "08", "12", "16",
                ]
                pre_cov = len(coverage.state.hit_branches)
                for pos in range(cycle_len):
                    if executions >= min(config.budget, 200):
                        break
                    for fv in fault_values:
                        if executions >= min(config.budget, 200):
                            break
                        # Build records: success everywhere except position `pos`
                        from cobol_penetrator.mock_data import MockRecord, format_record
                        records = []
                        num_iters = 100
                        for _ in range(num_iters):
                            for p in range(cycle_len):
                                if p == pos:
                                    records.append(format_record(
                                        MockRecord(op_key="", alpha_status=fv, num_status="0")
                                    ))
                                else:
                                    records.append(format_record(
                                        MockRecord(op_key="", alpha_status="  ", num_status="0")
                                    ))

                        import tempfile
                        with tempfile.NamedTemporaryFile(
                            mode="w", suffix=".dat", delete=False, prefix="stub_seq_"
                        ) as tf:
                            for r in records:
                                tf.write(r + "\n")
                            dat_path = tf.name

                        import os, subprocess
                        try:
                            env = os.environ.copy()
                            env["MOCKDATA"] = dat_path
                            proc = subprocess.run(
                                [str(config.executable)],
                                capture_output=True, text=True,
                                timeout=30, env=env,
                            )
                            from cobol_penetrator.trace_parser import parse_traces
                            result = parse_traces(proc.stdout)
                            result.exit_code = proc.returncode
                            result.stderr = proc.stderr
                            executions += 1
                            coverage.update(result)
                            walker.record_result(
                                {"input_state": {}, "stubs": {f"pos{pos}": fv}}, result
                            )
                            knowledge.record_execution(
                                {"input_state": {}, "stubs": {f"pos{pos}": fv}}, result
                            )
                        except Exception:
                            pass
                        finally:
                            try:
                                os.unlink(dat_path)
                            except OSError:
                                pass

                post_cov = len(coverage.state.hit_branches)
                logger.info(
                    "Position sequencing: %d new branch directions found (%d -> %d)",
                    post_cov - pre_cov, pre_cov, post_cov,
                )
        except Exception:
            logger.debug("Position-aware sequencing failed", exc_info=True)
        coverage.save(config.coverage_path)

    # 7. Per-ticket execution history (memory)
    ticket_histories: dict[str, list[dict]] = {}

    # 8. Main loop
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

        # Get or create history for this ticket
        history = ticket_histories.setdefault(ticket.id, [])

        # Multi-turn execution
        turns_per_ticket = min(
            config.max_turns_per_ticket,
            config.max_attempts - ticket.attempts,
        )
        params, result = await _multi_turn_execute(
            agent, ticket, structure, config, field_report, walker,
            history, coverage=coverage,
            max_turns=max(1, turns_per_ticket),
            knowledge=knowledge,
        )

        if result is None:
            engine.record_attempt(ticket)
            if ticket.status != "BLOCKED":
                ticket.status = "CREATED"
                ticket.assigned_agent = None
            store.save(config.tickets_path)
            continue

        executions += 1

        if ticket_target_reached(ticket, result):
            # Build result metadata
            result_meta: dict[str, Any] = {}
            if isinstance(ticket, ParagraphTicket):
                para_branch_ids = set()
                try:
                    para_branch_ids = set(structure.branches_in(ticket.paragraph))
                except KeyError:
                    pass
                result_meta["branches_discovered"] = [
                    bid for bid in result.branches_hit if bid in para_branch_ids
                ]
            if isinstance(ticket, BranchTicket):
                result_meta["variable_snapshot"] = result.variable_snapshots.get(ticket.branch_id)

            engine.complete(ticket, params, result_meta)

            # Cascade using BOTH trace output AND static call graph
            if isinstance(ticket, ParagraphTicket):
                _cascade_branch_tickets(engine, structure, ticket)
                new_tickets = _cascade_from_trace(
                    engine, store, structure, result, ticket
                )
                if new_tickets:
                    logger.info(
                        "Cascaded %d new paragraph tickets from %s",
                        new_tickets, ticket.id,
                    )

            # Coverage already updated in _multi_turn_execute for every execution
            save_successful_params(ticket, params, config.params_dir)

            logger.info(
                "Coverage: %.1f%% (%d/%d paragraphs, %d/%d branches)",
                coverage.coverage_pct,
                len(coverage.state.hit_paragraphs),
                coverage.state.total_paragraphs,
                len(coverage.state.hit_branches),
                coverage.state.total_branches,
            )
        else:
            # Even on failure, cascade tickets for any NEW paragraphs seen
            if isinstance(ticket, ParagraphTicket):
                _cascade_from_trace(engine, store, structure, result, ticket)

            engine.record_attempt(ticket)
            if ticket.status != "BLOCKED":
                ticket.status = "CREATED"
                ticket.assigned_agent = None

        store.save(config.tickets_path)
        coverage.save(config.coverage_path)
        knowledge.save(config.knowledge_path)

    # 9. Fault exploration phase — try stub error codes to reach error handlers
    if executions < config.budget and coverage.coverage_pct < 100.0:
        all_known_paras = set(coverage.state.hit_paragraphs)
        missing_paras = set(structure.paragraphs.keys()) - all_known_paras
        if missing_paras:
            logger.info(
                "Fault exploration: %d paragraphs still missing, trying stub fault sweeps",
                len(missing_paras),
            )
            from cobol_penetrator.heuristics.stub_fault_table import fault_values_for

            # Get stub operations from field report or from mock ops seen
            stub_ops = []
            if field_report:
                stub_ops = list(field_report.stub_operations)

            for stub_op in stub_ops:
                if executions >= config.budget:
                    break
                if time.time() - start_time > config.timeout:
                    break

                # Try each fault value for this stub
                fault_values = fault_values_for("status_file") + fault_values_for("status_sql")
                for fv in fault_values:
                    if executions >= config.budget:
                        break

                    params = {
                        "input_state": {},
                        "stubs": {stub_op: str(fv)},
                    }
                    try:
                        result = execute(config.executable, params, timeout=30)
                        executions += 1
                        coverage.update(result)
                        walker.record_result(params, result)
                        knowledge.record_execution(params, result)

                        new_paras = set(result.paragraphs_hit) - all_known_paras
                        if new_paras:
                            logger.info(
                                "Fault sweep %s=%s found %d new paragraphs: %s",
                                stub_op, fv, len(new_paras), sorted(new_paras),
                            )
                            all_known_paras.update(new_paras)
                            # Create tickets for newly found paragraphs
                            for para in new_paras:
                                if para in structure.paragraphs:
                                    try:
                                        engine.create_paragraph_ticket(
                                            paragraph=para, call_path=[para],
                                        )
                                    except Exception:
                                        pass
                    except Exception:
                        logger.debug("Fault sweep execution failed for %s=%s", stub_op, fv)

            # Also try combinations of fault values
            if len(stub_ops) >= 2 and executions < config.budget:
                import itertools
                for op1, op2 in itertools.combinations(stub_ops[:5], 2):
                    if executions >= config.budget:
                        break
                    for fv in ["GE", "23", "10", "100", "-803"]:
                        if executions >= config.budget:
                            break
                        params = {
                            "input_state": {},
                            "stubs": {op1: str(fv), op2: str(fv)},
                        }
                        try:
                            result = execute(config.executable, params, timeout=30)
                            executions += 1
                            coverage.update(result)
                            walker.record_result(params, result)
                            knowledge.record_execution(params, result)
                            new_paras = set(result.paragraphs_hit) - all_known_paras
                            if new_paras:
                                logger.info(
                                    "Combo fault %s=%s,%s=%s found %d new paras: %s",
                                    op1, fv, op2, fv, len(new_paras), sorted(new_paras),
                                )
                                all_known_paras.update(new_paras)
                        except Exception:
                            pass

            logger.info(
                "Fault exploration complete: coverage now %.1f%% (%d/%d paragraphs)",
                coverage.coverage_pct,
                len(coverage.state.hit_paragraphs),
                coverage.state.total_paragraphs,
            )

    # Save final state
    coverage.save(config.coverage_path)
    store.save(config.tickets_path)
    knowledge.save(config.knowledge_path)

    all_tickets = store.all_tickets()
    summary = {
        "executions": executions,
        "coverage_pct": coverage.coverage_pct,
        "total_tickets": len(all_tickets),
        "done_tickets": len([t for t in all_tickets if t.status == "DONE"]),
        "blocked_tickets": len([t for t in all_tickets if t.status == "BLOCKED"]),
    }

    logger.info("Run complete: %s", summary)
    return summary
