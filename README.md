<div align="center">

# ⚔️ rapier-ai

**A loop-engineered coding agent — set a goal, watch it iterate.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

Like the weaving rapier — a thin, precise shuttle that carries thread back and forth across a loom — **rapier-ai** carries your intent through iterative loops of **code → verify → refine** until the goal is met.

</div>

---

## Why rapier-ai?

Existing coding agents operate in one-shot mode: you prompt, they respond, done. rapier-ai operates in **goal loops** — you set an objective, and the agent iterates through planning, coding, verification, and refinement until the goal is provably complete.

| Feature | Claude Code | Aider | Cursor | **rapier-ai** |
|---|:---:|:---:|:---:|:---:|
| Loop engineering core | ✗ | ✗ | ✗ | **✓** |
| Maker/Checker split | subagent | ✗ | ✗ | **different model** |
| Token-efficient context | ✗ | ✗ | partial | **✓ + knowledge graph** |
| Persistent memory | CLAUDE.md | ✗ | ✗ | **knowledge graph** |
| Provider lock-in | Anthropic | any | OpenAI | **any OpenAI-compatible** |
| Language | TypeScript | Python | TypeScript | **Python** |

---

## How It Works

### The ReACT Loop

Every interaction follows the **Reason → Act → Observe** cycle:

```mermaid
flowchart LR
    A[User Input] --> B{LLM Reasons}
    B -->|Text response| C[Return to User]
    B -->|Tool calls| D[Execute Tools]
    D --> E[Observe Results]
    E --> B
```

### Goal-Based Iteration

Set a goal, and rapier-ai iterates until verified complete:

```mermaid
flowchart TD
    G[Set Goal] --> R[Research Phase]
    R --> C[Coder Implements]
    C --> V{Verifier Reviews}
    V -->|Pass| D[Done ✓]
    V -->|Fail| F[Coder Fixes]
    F --> V
    V -->|Budget exhausted| X[Stop — Report to User]
```

### Multi-Agent Architecture

Hub-and-spoke model — coordinator holds full context, workers get minimal:

```mermaid
flowchart TD
    U[User] --> CO[Coordinator<br/><i>Opus</i>]
    CO -->|research task| RE[Researcher<br/><i>Haiku</i>]
    CO -->|code task| CD[Coder<br/><i>Sonnet</i>]
    CD -->|verify| VE[Verifier<br/><i>Opus</i>]
    VE -->|pass| CO
    VE -->|fail| CD
    RE --> CO
```

---

## Quick Start

```bash
# Install
pip install rapier-ai

# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Start the REPL
rapier

# Or set a goal and watch it iterate
rapier --goal "add error handling to the API routes"

# Use OpenAI instead
rapier --provider openai --model gpt-4o
```

---

## Architecture

```mermaid
flowchart TD
    UI[REPL / CLI] --> PG[Permission Gate]
    PG --> OL[Orchestrator Loop]
    OL --> ME[Memory Recall]
    OL --> CT[Context Engine]
    CT --> LLM[LLM Client]
    LLM --> |Anthropic| A[Claude]
    LLM --> |OpenAI| O[GPT]
    LLM --> |response| OL
    OL --> |tool calls| TS[Tool System]
    TS --> RF[read_file]
    TS --> WF[write_file]
    TS --> EF[edit_file]
    TS --> BA[bash]
    TS --> GR[grep]
    TS --> GL[glob]
    TS --> WF2[web_fetch]
    TS --> TK[task]
    OL --> |verify| VE[Verifier Agent]
    VE --> |extract facts| MEM[Knowledge Graph]
    MEM --> SQ[(SQLite)]
```

---

## Development

```bash
# Clone
git clone https://github.com/souravkumardubey/rapier-ai.git
cd rapier-ai

# Create venv and install
uv venv --python 3.14
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest tests/

# Lint + format
ruff check .
ruff format .

# Type check
mypy rapier/
```

---

## Built With

- [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) — Claude API
- [OpenAI SDK](https://github.com/openai/openai-python) — GPT API
- [Rich](https://github.com/Textualize/rich) — Terminal formatting
- [Click](https://github.com/pallets/click) — CLI framework
- [tiktoken](https://github.com/openai/tiktoken) — Token counting
- [sentence-transformers](https://github.com/UKPLab/sentence-transformers) — Local embeddings

---

## License

[MIT](LICENSE) — do whatever you want.

---

<div align="center">

**Built with precision. Iterated with purpose.**

</div>
