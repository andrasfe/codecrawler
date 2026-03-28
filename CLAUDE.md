# CLAUDE.md — Agent Coding Guide

## Project Overview

COBOL Coverage Penetration Agent System. Takes instrumented COBOL binaries (from [specter](https://github.com/andrasfe/specter)) and uses LLM + heuristic agents to discover test parameters that reach every code path.

## Quick Reference

```bash
# Install
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Run tests (751 tests, ~6 seconds)
.venv/bin/pytest tests/ -v --tb=short

# Run against COPAUA0C
.venv/bin/python -m cobol_penetrator \
    --executable .specter_build_COPAUA0C/COPAUA0C \
    --mock-cbl .specter_build_COPAUA0C/COPAUA0C.mock.cbl \
    --budget 200 --timeout 300

# Check coverage
.venv/bin/python -m cobol_penetrator --status
```

## Conventions

- **pip** (not uv) for package management
- Python 3.10+, dataclasses preferred over Pydantic for internal models
- LLM providers use Protocol-based abstraction (no LangChain)
- No LangGraph — orchestrator is a simple async while-loop
- All ticket/coverage state persisted as JSON (`.tickets.json`, `.knowledge.json`, `reports/coverage.json`)
- Tests use `pytest` with `pytest-asyncio` (asyncio_mode = auto)

## Module Map

### Core Loop (`orchestrator.py`)

The main `run()` function executes:
1. Parse `.mock.cbl` → `ProgramStructure`
2. Build `FieldReport` from DATA DIVISION
3. Initialize `HeuristicWalker` and `LearnedKnowledge`
4. Baseline execution (empty params)
5. Position-aware stub sequencing (fault injection at each FIFO position)
6. Ticket loop: claim → agent → multi-turn execute → cascade → record knowledge

### Agents (`agents/`)

Three agent types, all extending `BaseAgent`:

| Agent | Ticket Type | Strategy | When Used |
|-------|------------|----------|-----------|
| `ReconAgent` | Entry paragraph | `EntryPointStrategy` | First ticket, no call path |
| `ParagraphAgent` | Deep paragraph | `CallChainStrategy` | Has call_path from parent |
| `BranchAgent` | Branch direction | `BranchFlipStrategy` | Targets specific `@@B:` direction |

**AgentContext** (passed to all agents):
- `ticket` — the work item
- `structure` — `ProgramStructure` (paragraphs, branches, call graph)
- `paragraph_code` — raw COBOL source of target
- `parent_params` — successful params from parent ticket (via knowledge)
- `field_report` — PIC types, ranges, condition literals
- `knowledge` — shared `LearnedKnowledge` store
- `execution_history` — prior attempts on this ticket

### Analysis (`analysis/`)

Extracts metadata from `.mock.cbl` DATA DIVISION:

- `pic_parser.py` — `parse_pic("S9(5)V99")` → `("numeric", 5, 2, True)`
- `data_division_parser.py` — `parse_working_storage(path)` → `list[FieldDefinition]`
- `variable_domain.py` — `VariableDomain` with semantic type inference (date, amount, status, flag...)
- `condition_harvester.py` — scans IF/EVALUATE for literal comparison values
- `field_report.py` — `build_field_report(path, structure)` → unified `FieldReport`

### Heuristics (`heuristics/`)

Domain-aware parameter generation inspired by AFL fuzzing:

- `value_generator.py` — 6 strategies: condition_literal, 88_value, boundary, semantic, adversarial, random_valid
- `stub_fault_table.py` — File status, SQL, CICS, DLI fault code tables
- `corpus.py` — Coverage-guided corpus with energy-weighted seed selection
- `heuristic_walker.py` — `HeuristicWalker` with `generate_initial_params()`, `mutate_params()`, `suggest_params_for_branch()`, knowledge-seeded generation

### Knowledge (`knowledge.py`)

`LearnedKnowledge` persists across tickets:
- `successful_params[paragraph]` — params that reached each paragraph
- `branch_params["id:dir"]` — params that hit each branch direction
- `variable_observations[var]` — values seen in `@@V:` snapshots
- `stub_outcomes[op]` — which stub outcomes produced coverage
- `failed_attempts[target]` — what was tried and didn't work

### Tickets (`tickets/`)

- `ParagraphTicket` — reach a specific paragraph
- `BranchTicket` — hit a specific branch direction (T/F/W1/WO)
- State machine: `CREATED → CLAIMED → IN_PROGRESS → DONE | BLOCKED`
- `TicketStore` — in-memory dict + JSON persistence, priority-based claim (paragraphs first, shorter call_path wins)
- `TicketEngine` — state machine enforcement, crash recovery (reset in-flight on load)

### Execution (`executor.py`, `trace_parser.py`, `mock_data.py`)

- `execute(executable, params, timeout)` → `ExecutionResult`
- Generates temp `.dat` file with 80-byte records, sets `MOCKDATA` env var
- Parses 5 trace formats from stdout into structured result
- `all_branch_directions: set[str]` captures every branch direction seen (not just last per ID)

### LLM Providers (`llm_providers/`)

Protocol-based abstraction (copied from specter):
- `Message(role, content)`, `CompletionResponse(content, model, tokens_used)`
- `LLMProvider` Protocol with `complete()` method
- `get_provider_from_env()` reads `LLM_PROVIDER`, `OPENROUTER_API_KEY`, etc.

## Key Data Flow

```
.mock.cbl → mock_reader.parse_mock_structure() → ProgramStructure
         → analysis.build_field_report()        → FieldReport

Agent generates: {"input_state": {...}, "stubs": {...}}
  ↓
mock_data.generate_mock_file() → temp .dat file (80-byte records)
  ↓
executor.execute() → subprocess with MOCKDATA=path → ExecutionResult
  ↓
trace_parser.parse_traces(stdout) → paragraphs_hit, branches_hit, all_branch_directions
  ↓
coverage.update(result) → cumulative paragraph + branch coverage
knowledge.record_execution(params, result) → shared wisdom
```

## Mock Data Record Format

```
Cols  1-30: op_key (operation identifier, or empty for positional records)
Cols 31-50: alpha_status (2-char file status, DLI status, etc.)
Cols 51-59: num_status (9-digit numeric, SQLCODE, EIBRESP, etc.)
Cols 60-80: filler (spaces)
```

Records consumed FIFO — the Nth `READ MOCK-FILE` gets the Nth record. The mock operation cycle repeats (e.g., `DLI-SCHD, DLI-GU, DLI-REPL, CICS, CICS, DLI-ISRT` for COPAUA0C).

## Testing

```bash
# All tests
.venv/bin/pytest tests/ -v

# By module
.venv/bin/pytest tests/test_analysis/ -v      # 168 tests
.venv/bin/pytest tests/test_heuristics/ -v     # 152 tests
.venv/bin/pytest tests/test_agents/ -v         # 108 tests
.venv/bin/pytest tests/test_orchestrator.py -v # 20 tests
.venv/bin/pytest tests/test_knowledge.py -v    # 29 tests
```

Test fixtures at `tests/fixtures/sample.mock.cbl` — a hand-crafted 4-paragraph COBOL program.

## Specter Integration

Specter instruments COBOL source → produces `.mock.cbl` + compiled binary:

```bash
# Instrument
specter PROGRAM.cbl --mock-cobol --copybook-dir CPY_DIR -o OUT.mock.cbl

# Compile (requires GnuCOBOL)
cobc -x -o PROGRAM OUT.mock.cbl
```

Branch probes (`@@B:`) are added by specter's Phase 12b2 (post-compilation-fix). Only structured IFs (with END-IF) get probes — period-delimited IFs are skipped.

## Common Tasks

**Add a new agent type:**
1. Create `agents/new_agent.py` extending `BaseAgent`
2. Implement `build_context()` and `generate_params()`
3. Create matching `strategies/new_strategy.py` extending `Strategy`
4. Register in `orchestrator.select_agent()`

**Add a new heuristic strategy:**
1. Add to `heuristics/value_generator.py` `generate_value()` switch
2. Update `heuristic_walker.py` mutation probabilities

**Add a new trace format:**
1. Add parser function in `trace_parser.py`
2. Add to `_PARSERS` list
3. Add field to `ExecutionResult`

## External Dependencies

- **Specter** (`~/specter`) — COBOL instrumentation engine
- **War Rig** (`~/war_rig`) — LLM providers originated from here
- **AWS CardDemo** (`~/aws-mainframe-modernization-carddemo`) — Reference COBOL programs
- **GnuCOBOL** (`cobc`) — Compiles instrumented COBOL to native binary
