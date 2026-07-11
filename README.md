# rapier-ai

A loop-engineered coding agent — set a goal, watch it iterate.

## What is rapier-ai?

rapier-ai is a Python coding agent designed around **loop engineering principles**. Like the weaving rapier — a thin, precise shuttle that carries thread back and forth across a loom — Rapier carries your intent through iterative loops of code → verify → refine until the goal is met.

## Features

- **Goal-based loops** — Set an objective, agent iterates until verified complete
- **Maker/Checker separation** — A different model verifies the coder's work
- **Token-efficient context** — Rewrites history instead of replaying full transcript
- **Persistent memory** — Knowledge graph that survives across sessions
- **Safety by default** — Deny-first permission system with AST-based bash analysis
- **Multi-provider** — Works with Anthropic, OpenAI, or any compatible API

## Quick Start

```bash
# Install
pip install rapier-ai

# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Start the REPL
rapier

# Or set a goal
rapier --goal "add error handling to the API routes"
```

## Architecture

```
┌──────────────────────────────────────┐
│       ORCHESTRATOR (Main Loop)       │
│  while (!goal_complete) {            │
│    1. RECALL  — memory + context     │
│    2. PLAN    — next action          │
│    3. ACT     — dispatch to agent    │
│    4. VERIFY  — checker reviews      │
│    5. LEARN   — extract facts        │
│  }                                   │
└──────────┬───────────────────────────┘
           │
    ┌──────┼──────┐
    ▼      ▼      ▼
┌──────┐┌──────┐┌──────┐
│Coder ││Resrch││Verifr│
└──────┘└──────┘└──────┘
```

## Development

```bash
# Clone
git clone https://github.com/souravdubey/rapier-ai.git
cd rapier-ai

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Lint
ruff check .

# Format
ruff format .
```

## Documentation

- [Project Plan](docs/project-plan.md)
- [Architecture](docs/architecture.md)
- [Build Phases](docs/phases.md)
- [Components](docs/components.md)
- [Development Workflow](docs/workflow.md)
- [Roadmap](docs/roadmap.md)

## License

MIT
