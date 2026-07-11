# CLAUDE.md

## Project

rapier-ai — A loop-engineered coding agent. Goal-based iteration, maker/checker separation, token-efficient context, persistent memory.

## Build

- Language: Python 3.11+
- Package manager: pip / uv
- Install: `pip install -e ".[dev]"`
- Run: `python -m rapier` or `rapier`

## Commands

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
mypy rapier/

# Test
pytest tests/

# Test with coverage
pytest tests/ --cov=rapier
```

## Architecture

- `rapier/loop.py` — the agent loop (while true + tool dispatch)
- `rapier/llm/` — provider-agnostic LLM client (Anthropic, OpenAI)
- `rapier/tools/` — tool registry + implementations (read, write, edit, bash, grep, glob, web_fetch, task)
- `rapier/context/` — conversation management + 5-tier compaction
- `rapier/permissions/` — safety rails (deny-first, AST-based bash analysis)
- `rapier/goals/` — goal lifecycle + budget tracking
- `rapier/agents/` — multi-agent orchestration (coordinator, coder, researcher, verifier)
- `rapier/memory/` — knowledge graph + vector recall
- `rapier/ui/` — terminal UI (Rich-based)

## Code Style

- Type hints on all functions
- docstrings on public interfaces
- Use `async/await` for all I/O
- Pydantic for data validation
- Rich for terminal output
- Click for CLI
