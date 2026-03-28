# COBOL Coverage Penetration Agent System

A multi-agent system that uses LLM-driven analysis and heuristic-based random walks to progressively penetrate instrumented COBOL executables, discovering parameters that reach deeper code paths and documenting successful test inputs.

## How It Works

```
.mock.cbl ──► Mock Reader ──► Program Structure
                                    │
Executable ◄── Executor ◄── Mock Data ◄── Agent (LLM + Heuristics)
    │                                         ▲
    ▼                                         │
Trace Parser ──► Coverage Tracker ──► Ticket Engine ──► Next Agent
```

1. **Specter** instruments a COBOL source file, producing a `.mock.cbl` (instrumented source) and a compiled executable that emits trace data (`SPECTER-TRACE:`, `@@B:`, `@@V:`)
2. **Mock Reader** parses the `.mock.cbl` to extract paragraph structure, branch probes, and call graph
3. **Analysis** extracts PIC clauses, data types, value ranges, and condition literals from the DATA DIVISION
4. **Ticket Engine** creates work items for each paragraph and branch direction to reach
5. **Agents** (ReconAgent, ParagraphAgent, BranchAgent) use LLM + heuristics to generate test parameters
6. **Executor** runs the COBOL binary with generated mock data, captures trace output
7. **Coverage Tracker** accumulates paragraph and branch coverage across all executions
8. **Knowledge Store** persists successful parameters, variable observations, and failure patterns across tickets

## Quick Start

```bash
# Install
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# Configure LLM provider
cp .env.example .env
# Edit .env with your API key

# Instrument a COBOL program (requires specter)
specter path/to/PROGRAM.cbl --mock-cobol --copybook-dir path/to/cpy -o .specter_build_PROG/PROG.mock.cbl
cobc -x -o .specter_build_PROG/PROG .specter_build_PROG/PROG.mock.cbl

# Run penetration
python -m cobol_penetrator \
    --executable .specter_build_PROG/PROG \
    --mock-cbl .specter_build_PROG/PROG.mock.cbl \
    --budget 200 --timeout 600 --max-attempts 10

# Check status
python -m cobol_penetrator --status
```

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--executable` | required | Path to compiled COBOL mock binary |
| `--mock-cbl` | required | Path to instrumented `.mock.cbl` source |
| `--budget` | 10000 | Maximum execution attempts |
| `--timeout` | 3600 | Total wall-clock timeout (seconds) |
| `--max-attempts` | 5 | Max attempts per ticket before blocking |
| `--resume` | false | Resume from prior `.tickets.json` |
| `--status` | false | Show current coverage status and exit |
| `--tickets-path` | `.tickets.json` | Ticket store file path |
| `--coverage-path` | `reports/coverage.json` | Coverage state file path |

## Architecture

```
cobol_penetrator/
├── __main__.py              # CLI entry point
├── config.py                # PenetratorConfig (env + CLI args)
├── orchestrator.py          # Main agent loop with multi-turn execution
├── executor.py              # Run COBOL binary, capture traces
├── trace_parser.py          # Parse 5 trace formats from stdout
├── mock_reader.py           # Extract paragraphs, branches, call graph from .mock.cbl
├── mock_data.py             # Generate 80-byte LINE SEQUENTIAL .dat files
├── knowledge.py             # Shared knowledge store across tickets
├── agents/
│   ├── base.py              # BaseAgent ABC, AgentContext
│   ├── recon.py             # ReconAgent (entry point discovery)
│   ├── paragraph.py         # ParagraphAgent (reach specific paragraph)
│   └── branch.py            # BranchAgent (flip branch direction)
├── strategies/
│   ├── base.py              # Strategy ABC
│   ├── entry_point.py       # EntryPointStrategy (initial params)
│   ├── call_chain.py        # CallChainStrategy (follow PERFORM chain)
│   ├── branch_flip.py       # BranchFlipStrategy (target branch direction)
│   └── prompt_enrichment.py # Format metadata for LLM prompts
├── analysis/
│   ├── pic_parser.py        # COBOL PIC clause parsing
│   ├── data_division_parser.py  # Extract WORKING-STORAGE fields
│   ├── variable_domain.py   # VariableDomain (types, ranges, semantics)
│   ├── condition_harvester.py   # Harvest IF/EVALUATE literals
│   └── field_report.py      # Unified FieldReport builder
├── heuristics/
│   ├── value_generator.py   # 6-strategy domain-aware value generation
│   ├── stub_fault_table.py  # File/SQL/CICS/DLI fault code tables
│   ├── corpus.py            # Coverage-guided corpus management
│   └── heuristic_walker.py  # AFL-inspired random walk engine
├── tickets/
│   ├── models.py            # ParagraphTicket, BranchTicket
│   ├── store.py             # In-memory store with JSON persistence
│   └── engine.py            # Ticket state machine
├── reports/
│   ├── coverage.py          # CoverageTracker (paragraphs + branches)
│   └── params.py            # Save successful params per ticket
└── llm_providers/           # Provider-agnostic LLM abstraction
    ├── protocol.py          # LLMProvider Protocol, Message, CompletionResponse
    ├── config.py             # Provider configs (Pydantic)
    ├── factory.py            # create_provider, get_provider_from_env
    └── providers/
        ├── openrouter.py    # OpenRouter (multi-provider gateway)
        ├── anthropic.py     # Direct Anthropic API
        └── openai.py        # Direct OpenAI API
```

## Orchestration Pipeline

The orchestrator runs these phases in order:

1. **Parse** `.mock.cbl` for program structure (paragraphs, branches, call graph)
2. **Analyze** DATA DIVISION (PIC clauses, field types, value ranges, condition literals)
3. **Baseline execution** with empty params to establish success-path coverage
4. **Position-aware stub sequencing** — detect mock operation cycle, inject fault values at each position to flip branches
5. **Agent loop** — for each ticket:
   - Multi-turn execution (up to `max_turns_per_ticket`, default 10)
   - LLM generates params enriched with field metadata, knowledge, execution history
   - Heuristic walker provides fallback/mutation on retries
   - Coverage updated after every execution
   - Knowledge store records successes, failures, variable observations
   - Tickets cascade for newly discovered paragraphs and branches

## Coverage Results (COPAUA0C)

AWS CardDemo authorization program — 43 paragraphs, 25 branch directions:

| Metric | Raw | Of Reachable |
|--------|-----|-------------|
| Paragraphs | 30/43 (69.8%) | 30/33 traceable (90.9%) |
| Branches | 18/25 (72.0%) | 18/18 reachable (100%) |
| **Combined** | **48/68 (70.6%)** | **48/51 (94.1%)** |

## COBOL Trace Formats

| Prefix | Format | Purpose |
|--------|--------|---------|
| `SPECTER-TRACE:` | `SPECTER-TRACE:<PARAGRAPH>` | Paragraph was entered |
| `@@B:` | `@@B:<id>:<T\|F\|W1\|WO>` | Branch probe taken |
| `SPECTER-CALL:` | `SPECTER-CALL:FROM=<X>:TO=<Y>` | Call chain tracking |
| `@@V:` | `@@V:<bid>:<var>=<val>` | Variable snapshot at branch |
| `SPECTER-MOCK:` | `SPECTER-MOCK:<operation>` | Mock operation executed |

## Mock Data Format

80-byte LINE SEQUENTIAL records consumed via `MOCKDATA` env var:

```
<op-key:30><alpha-status:20><num-status:9><filler:21>
```

Records are consumed in FIFO order — each `READ MOCK-FILE` gets the next record.

## Development

```bash
# Run tests (751 tests)
.venv/bin/pytest tests/ -v

# Run a specific test module
.venv/bin/pytest tests/test_orchestrator.py -v

# Type check
.venv/bin/python -c "import cobol_penetrator; print('OK')"
```

## Dependencies

- Python >= 3.10
- pydantic >= 2.0
- httpx, openai, anthropic (LLM providers)
- python-dotenv, pyyaml, rich, typer (CLI)
- GnuCOBOL (`cobc`) for compiling instrumented COBOL
- [Specter](https://github.com/andrasfe/specter) for COBOL instrumentation

## License

Proprietary
