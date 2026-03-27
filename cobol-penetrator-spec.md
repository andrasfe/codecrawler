# COBOL Coverage Penetration Agent System — Spec

## Overview

A standalone repo (`cobol-penetrator`) that takes pre-built instrumented COBOL artifacts from specter and uses a multi-agent ticket system to progressively "penetrate" the executable — discovering parameters that reach deeper code paths, documenting successes, and spawning new tickets for each discovered branch.

**No build/runtime dependencies on specter or war_rig.** Copies over `llm_providers/` and `.env` config. Tickets are in-memory with JSON persistence (like war_rig's default mode), no beads CLI dependency.

## Input Artifacts (from `.specter_build_<STEM>/`)

| File | Purpose |
|------|---------|
| `<STEM>` | Compiled COBOL executable |
| `<STEM>.mock.cbl` | Instrumented source (agents read this to understand structure) |

## Copied Packages (standalone)

| Source | Destination | Purpose |
|--------|-------------|---------|
| `specter/llm_providers/` | `cobol_penetrator/llm_providers/` | LLM abstraction (Protocol, Message, providers) |
| `.env` pattern | `.env` | LLM config (provider, key, model) |

## COBOL Trace Formats

The instrumented COBOL executable emits to stdout:

| Prefix | Format | Purpose |
|--------|--------|---------|
| `SPECTER-TRACE:` | `SPECTER-TRACE:<PARAGRAPH>` | Paragraph was entered |
| `@@B:` | `@@B:<id>:<T\|F\|W1\|WO>` | Branch probe taken |
| `SPECTER-CALL:` | `SPECTER-CALL:FROM=<caller>:TO=<callee>` | **NEW** — call chain tracking |
| `@@V:` | `@@V:<bid>:<var1>=<val1>:<var2>=<val2>` | **NEW** — variable snapshots at branch points |
| `SPECTER-MOCK:` | `SPECTER-MOCK:<operation>` | Mock operation executed |

## Architecture

```
cobol_penetrator/
├── __main__.py              # CLI entry point
├── config.py                # Load .env, CLI args, YAML config
├── executor.py              # Run COBOL binary, parse traces
├── mock_reader.py           # Parse .mock.cbl for paragraph/branch structure
├── tickets/
│   ├── models.py            # Ticket types (ParagraphTicket, BranchTicket)
│   ├── store.py             # In-memory store with JSON persistence (.tickets.json)
│   └── engine.py            # Ticket state machine (CREATED->CLAIMED->DONE)
├── agents/
│   ├── base.py              # BaseAgent with LLM + ticket interface
│   ├── recon.py             # ReconAgent: initial parameter discovery
│   ├── paragraph.py         # ParagraphAgent: penetrate specific paragraph
│   └── branch.py            # BranchAgent: target specific branch direction
├── strategies/
│   ├── base.py              # Strategy ABC
│   ├── entry_point.py       # Find the entry paragraph, discover initial params
│   ├── call_chain.py        # Follow PERFORM chain to reach target paragraph
│   └── branch_flip.py       # Flip a specific branch by varying condition vars
├── llm_providers/            # Copied from specter (standalone)
│   ├── __init__.py
│   ├── protocol.py
│   ├── config.py
│   ├── factory.py
│   └── providers/
│       ├── openrouter.py
│       ├── anthropic.py
│       └── openai.py
├── reports/
│   ├── coverage.json         # Running coverage state
│   └── successful_params/    # Documented successful parameters per paragraph
└── .tickets.json             # In-memory ticket state persisted to disk
```

## Ticket Types

### ParagraphTicket

```python
@dataclass
class ParagraphTicket:
    id: str                          # "PARA-2000-VALIDATE"
    paragraph: str                   # "2000-VALIDATE"
    status: str                      # CREATED | CLAIMED | IN_PROGRESS | DONE | BLOCKED
    assigned_agent: str | None       # Agent class name
    call_path: list[str]             # ["1000-MAIN", "2000-VALIDATE"]
    required_stubs: list[str]        # Stub ops needed to reach this para
    successful_params: dict | None   # Input state that reached it
    branches_discovered: list[str]   # Branch IDs found inside this paragraph
    attempts: int
    created_at: str
    updated_at: str
```

### BranchTicket

```python
@dataclass
class BranchTicket:
    id: str                          # "BRANCH-5-T"
    branch_id: str                   # "5"
    direction: str                   # "T" or "F" or "W1"
    paragraph: str                   # Paragraph containing this branch
    condition_text: str              # "WS-STATUS = '00'"
    condition_vars: list[str]        # ["WS-STATUS"]
    status: str
    assigned_agent: str | None
    successful_params: dict | None   # Params that hit this branch+direction
    variable_snapshot: dict | None   # @@V: data when branch was taken
    attempts: int
    created_at: str
    updated_at: str
```

### Ticket State Machine

```
CREATED --> CLAIMED --> IN_PROGRESS --> DONE
                  \              \
                   \--> BLOCKED   \--> BLOCKED
```

On crash/restart: CLAIMED and IN_PROGRESS tickets reset to CREATED (rehydrated from `.tickets.json`).

## Agent Loop (Main Orchestrator)

```python
def run(executable, mock_cbl, config):
    # 1. Parse mock.cbl -> paragraph list, branch list, call graph
    structure = parse_mock_structure(mock_cbl)

    # 2. Create initial ticket: reach the entry paragraph
    tickets.create(ParagraphTicket(paragraph=structure.entry_paragraph))

    # 3. Agent pool loop
    while open_tickets_exist() and budget_remaining():
        ticket = tickets.claim_next()  # Priority: paragraphs before branches

        agent = select_agent(ticket)

        # Agent reads relevant section of mock.cbl
        context = agent.build_context(ticket, structure, mock_cbl)

        # Agent generates test parameters (may use LLM)
        params = agent.generate_params(context, ticket)

        # Execute COBOL binary
        result = execute(executable, params)

        # Check success
        if ticket_target_reached(ticket, result):
            ticket.status = "DONE"
            ticket.successful_params = params

            # Open NEW tickets for each branch discovered
            for branch_id in result.branches_hit:
                if branch_id in structure.branches_in(ticket.paragraph):
                    tickets.create(BranchTicket(
                        branch_id=branch_id,
                        paragraph=ticket.paragraph,
                        condition_text=structure.branch_condition(branch_id),
                    ))

            # Open tickets for CALLED paragraphs discovered
            for caller, callee in result.call_chain:
                if callee not in tickets.done_paragraphs():
                    tickets.create(ParagraphTicket(
                        paragraph=callee,
                        call_path=ticket.call_path + [callee],
                    ))
        else:
            ticket.attempts += 1
            if ticket.attempts >= max_attempts:
                ticket.status = "BLOCKED"
```

## LLM Integration

Agents use the LLM (via `llm_providers/`, configured from `.env`) to:

1. **Read mock.cbl chunks** — understand what a paragraph does, what stubs it calls
2. **Generate parameter hypotheses** — "to reach paragraph X, I need WS-STATUS='00'"
3. **Analyze variable snapshots** — "branch 5:F was taken because WS-FLAG was 'N'"
4. **Multi-turn investigation** — agent can request more chunks of mock.cbl

```python
class ParagraphAgent(BaseAgent):
    def generate_params(self, context, ticket):
        para_code = context.get_paragraph_code(ticket.paragraph)

        prompt = f"""
        I need to reach paragraph {ticket.paragraph} in a COBOL program.
        Call path: {ticket.call_path}

        Code:
        ```cobol
        {para_code}
        ```

        Known stubs: {ticket.required_stubs}
        Parent's successful params: {parent_params}

        What input variables and stub outcomes should I set?
        Return as JSON: {{"input_state": {{}}, "stubs": {{}}}}
        """

        response = self.llm.complete(prompt)
        return parse_params(response)
```

## Mock Data Format (reimplemented standalone)

80-byte LINE SEQUENTIAL records:
```
<op-key:30><alpha-status:20><num-status:9><filler:21>
```

The executor generates:
1. INIT records: `INIT:<varname>` + value
2. Stub records: `<op-key>` + status values
3. Writes temp `.dat` file, runs executable with `MOCKDATA=<path>` env var
4. Parses stdout for all trace prefixes

## CLI

```bash
# Run penetration
python -m cobol_penetrator \
    --executable .specter_build_RCO100B/RCO100B \
    --mock-cbl .specter_build_RCO100B/RCO100B.mock.cbl \
    --budget 10000 \
    --timeout 3600

# Resume from prior run (reads beads/ directory)
python -m cobol_penetrator \
    --executable .specter_build_RCO100B/RCO100B \
    --mock-cbl .specter_build_RCO100B/RCO100B.mock.cbl \
    --resume

# Status report
python -m cobol_penetrator --status --beads-dir ./beads
```

## Validation Examples

The AWS CardDemo COBOL programs (from [aws-mainframe-modernization-carddemo](https://github.com/aws-samples/aws-mainframe-modernization-carddemo)) are the reference test suite for validating mock build and instrumentation. These are located in specter's `examples/` directory:

| Program | AST File | Description |
|---------|----------|-------------|
| COPAUA0C | `examples/COPAUA0C.cbl.ast` | Authorization processing (IMS/DB2/MQ) — primary validation target |
| COACTUPC | `examples/COACTUPC.cbl.ast` | Account update |
| COTRN00C | `examples/COTRN00C.cbl.ast` | Transaction listing |
| COSGN00C | `examples/COSGN00C.cbl.ast` | Sign-on |
| COBIL00C | `examples/COBIL00C.cbl.ast` | Bill pay |
| COMEN01C | `examples/COMEN01C.cbl.ast` | Menu navigation |
| COUSR00C-03C | `examples/COUSR0*.cbl.ast` | User management (4 programs) |
| CORPT00C | `examples/CORPT00C.cbl.ast` | Reporting |

**Validation workflow** (from `examples/README.md`):
```bash
# 1. Clone CardDemo repo alongside specter
git clone https://github.com/aws-samples/aws-mainframe-modernization-carddemo

# 2. Instrument + compile
specter ../aws-mainframe-modernization-carddemo/app/.../cbl/COPAUA0C.cbl \
    --copybook-dir ../aws-mainframe-modernization-carddemo/app/.../cpy \
    -o examples/COPAUA0C.mock.cbl
cobc -x -o examples/COPAUA0C.mock examples/COPAUA0C.mock.cbl

# 3. Run coverage synthesis (validates COBOL binary against Python)
specter examples/COPAUA0C.cbl.ast --cobol-coverage \
    --cobol-source ../aws-mainframe-modernization-carddemo/app/.../cbl/COPAUA0C.cbl \
    --copybook-dir ../aws-mainframe-modernization-carddemo/app/.../cpy
```

The large enterprise program (`RCO100B.cbl`, 40K+ lines, 1033 paragraphs) from `war_rig/examples/MNS/` is the stress test for the compilation pipeline and the primary target for cobol-penetrator.

## Success Criteria

1. First run creates entry paragraph ticket, reaches it, documents params
2. Tickets cascade: reaching paragraph X opens tickets for branches in X and paragraphs called by X
3. Agents use LLM to analyze mock.cbl and generate intelligent params
4. `.tickets.json` shows ticket lifecycle with successful_params
5. Resume works: picks up where it left off
6. Coverage % increases monotonically across agent iterations
7. Validated against AWS CardDemo programs (COPAUA0C as primary) and RCO100B (stress test)
