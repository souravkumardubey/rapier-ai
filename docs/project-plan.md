# rapier-ai — Project Plan

## 1. Project Identity

| Field | Value |
|---|---|
| **Name** | `rapier-ai` |
| **Tagline** | A loop-engineered coding agent — set a goal, watch it iterate |
| **Language** | Python 3.11+ |
| **License** | MIT |
| **Location** | `/Users/sodubey/personal/projects/rapier-ai/` |
| **PyPI Package** | `rapier-ai` |
| **CLI Command** | `rapier` |

## 2. Vision

rapier-ai is a coding agent designed from the ground up around **loop engineering principles**. Like the weaving rapier — a thin, precise shuttle that carries thread back and forth across a loom — Rapier carries your intent through iterative loops of code → verify → refine until the goal is met.

## 3. What Makes It Unique

### The Loop Engineering Paradigm

Existing coding agents (Claude Code, Cursor, Copilot) operate in one-shot mode: you prompt, they respond, done. rapier-ai operates in **goal loops**: you set an objective, and the agent iterates through planning, coding, verification, and refinement until the goal is provably complete.

### Differentiators

| Feature | Claude Code | Aider | OpenSeek | **rapier-ai** |
|---|---|---|---|---|
| Loop engineering core | No | No | No | **Yes** |
| Maker/Checker split | Subagent | No | No | **Different model per role** |
| Token-efficient context | No | No | Partial | **Yes + knowledge graph** |
| Persistent memory | CLAUDE.md | No | No | **Knowledge graph** |
| Provider support | Anthropic | Any | 28 | **Any OpenAI-compatible** |
| Language | TypeScript | Python | TypeScript | **Python** |

### Core Design Principles

1. **Goal-based iteration** — Set an objective, agent iterates until verified complete
2. **Maker/Checker separation** — A different model verifies the coder's work (never grade your own homework)
3. **Token efficiency** — Rewrite history per turn instead of replaying full transcript
4. **Persistent memory** — Knowledge graph that survives across sessions
5. **Safety by default** — Deny-first permission system with AST-based bash analysis
6. **Provider agnostic** — Works with Anthropic, OpenAI, or any compatible API

## 4. Target Users

- **Solo developers** who want an autonomous coding assistant
- **Open source maintainers** who want help with issue triage and bug fixes
- **Teams** who want a self-hosted, privacy-first coding agent
- **Learners** who want to understand how coding agents work

## 5. Success Criteria

| Criterion | Target |
|---|---|
| Phase 1 working | REPL that talks to LLM + handles tool calls |
| All 8 phases complete | Full loop-engineered coding agent |
| Tests passing | >80% coverage on core components |
| Published to PyPI | `pip install rapier-ai` works |
| GitHub README | Clear install, usage, architecture docs |
| Portfolio quality | Can discuss design tradeoffs for 15+ minutes |

## 6. Constraints

- **Python only** — No TypeScript, no compiled languages
- **No cloud dependencies** — Runs locally, BYOK (bring your own API key)
- **No vendor lock-in** — Any OpenAI-compatible API works
- **Max 2,500 LOC** — Stay focused, avoid bloat
- **3-week timeline** — Ship within 21 days

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Context engine too complex | Medium | High | Start with simple truncation, add tiers incrementally |
| Memory system scope creep | High | Medium | Ship basic graph first, enhance later |
| Permission system blocks valid ops | Medium | Medium | Extensive testing, allow override |
| Token costs too high | Low | Medium | Token-efficient context from day 1 |
| Scope creep | High | High | Strict phase boundaries, no features outside plan |

## 8. Open Source Strategy

- **MIT License** — Maximum adoption
- **PyPI + GitHub** — Standard Python distribution
- **CLAUDE.md** — AI assistants can contribute effectively
- **Contributing guide** — Community can add tools, providers, features
- **Blog post series** — "Building a Coding Agent from Scratch" (8 parts)
