# rapier-ai — Roadmap

## Visual Timeline

```
Week 1: Foundation
═══════════════════════════════════════════════════════════════
Day 1  │ ████████████████████ │ Phase 1: Core Loop + LLM Client
Day 2  │ ████████████████████ │ Phase 1: Core Loop + LLM Client
Day 3  │ ████████████████████ │ Phase 2: Tool System
Day 4  │ ████████████████████ │ Phase 2: Tool System
Day 5  │ ████████████████████ │ Phase 3: Permission System
Day 6  │ ████████████████████ │ Phase 3: Permission System
Day 7  │ ░░░░░░░░░░░░░░░░░░░░ │ (buffer / catch-up)

Week 2: Intelligence
═══════════════════════════════════════════════════════════════
Day 8  │ ████████████████████ │ Phase 4: Context Engine
Day 9  │ ████████████████████ │ Phase 4: Context Engine
Day 10 │ ████████████████████ │ Phase 5: Goal Engine
Day 11 │ ████████████████████ │ Phase 5: Goal Engine
Day 12 │ ████████████████████ │ Phase 5: Goal Engine
Day 13 │ ████████████████████ │ Phase 6: Multi-Agent System
Day 14 │ ░░░░░░░░░░░░░░░░░░░░ │ (buffer / catch-up)

Week 3: Memory + Ship
═══════════════════════════════════════════════════════════════
Day 15 │ ████████████████████ │ Phase 6: Multi-Agent System
Day 16 │ ████████████████████ │ Phase 7: Memory System
Day 17 │ ████████████████████ │ Phase 7: Memory System
Day 18 │ ████████████████████ │ Phase 7: Memory System
Day 19 │ ████████████████████ │ Phase 8: Polish + Ship
Day 20 │ ████████████████████ │ Phase 8: Polish + Ship
Day 21 │ ████████████████████ │ Ship to PyPI + GitHub
```

## LOC Progression

```
Phase 1:  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  400 LOC
Phase 2:  █████████████████░░░░░░░░░░░░░░░░░░░░░░░  650 LOC (+250)
Phase 3:  ██████████████████████░░░░░░░░░░░░░░░░░░  950 LOC (+300)
Phase 4:  ██████████████████████████░░░░░░░░░░░░░░  1250 LOC (+300)
Phase 5:  █████████████████████████████░░░░░░░░░░░  1520 LOC (+270)
Phase 6:  █████████████████████████████████░░░░░░░  1850 LOC (+330)
Phase 7:  ████████████████████████████████████░░░░  2130 LOC (+280)
Phase 8:  ████████████████████████████████████████  2330 LOC (+200)
```

## File Count Progression

```
Phase 1:  10 files
Phase 2:  19 files (+9)
Phase 3:  22 files (+3)
Phase 4:  25 files (+3)
Phase 5:  28 files (+3)
Phase 6:  32 files (+4)
Phase 7:  36 files (+4)
Phase 8:  55 files (+19) — tests, docs, config
```

## Phase Dependencies

```
Phase 1: Core Loop ──────────────────────────┐
                                              │
Phase 2: Tools ──────────────────────────────┤
                                              │
Phase 3: Permissions ────────────────────────┤
                                              │
Phase 4: Context ────────────────────────────┤
                                              ├──► Phase 6: Multi-Agent
Phase 5: Goals ──────────────────────────────┤
                                              │
Phase 7: Memory ─────────────────────────────┘
                                              │
                                              ▼
                                      Phase 8: Polish
```

## Milestone Checklist

### Milestone 1: Foundation (Day 2)
- [ ] `python -m rapier` starts REPL
- [ ] Can talk to Anthropic Claude
- [ ] Can talk to OpenAI GPT
- [ ] Basic tool calling works
- [ ] pyproject.toml configured

### Milestone 2: Tools (Day 4)
- [ ] Read file tool works
- [ ] Write file tool works
- [ ] Edit file tool works (diff-based)
- [ ] Bash tool works with timeout
- [ ] Grep tool works
- [ ] Glob tool works
- [ ] Tool registry auto-discovers tools

### Milestone 3: Safety (Day 6)
- [ ] Permission gate blocks dangerous bash
- [ ] AST analyzer catches command substitution
- [ ] User can approve/deny operations
- [ ] Protected paths (.git/) blocked
- [ ] Safety rules enforced

### Milestone 4: Context (Day 9)
- [ ] Token counting works
- [ ] Tier 1 (snip) clears old results
- [ ] Tier 4 (autocompact) summarizes history
- [ ] Circuit breaker prevents infinite compaction
- [ ] 50+ turn conversations work

### Milestone 5: Goals (Day 12)
- [ ] `rapier --goal "..."` works
- [ ] Budget tracking (tokens, turns, time)
- [ ] Goal lifecycle (create → active → complete)
- [ ] Verifier uses different model
- [ ] Budget exhaustion stops goal

### Milestone 6: Multi-Agent (Day 15)
- [ ] Coordinator dispatches to specialists
- [ ] Coder writes code (Sonnet)
- [ ] Researcher searches (Haiku)
- [ ] Verifier reviews (Opus)
- [ ] Maker/Checker loop works
- [ ] Max 3 rounds before escalation

### Milestone 7: Memory (Day 18)
- [ ] Knowledge graph stores facts
- [ ] Vector recall finds relevant facts
- [ ] Auto-extraction from tool results
- [ ] SQLite persistence works
- [ ] Cross-session memory works

### Milestone 8: Ship (Day 21)
- [ ] All tests passing
- [ ] README complete
- [ ] Architecture docs complete
- [ ] Published to PyPI
- [ ] GitHub repo public

## Risk Timeline

| Week | Risk | Mitigation |
|---|---|---|
| Week 1 | LLM API changes | Pin versions, test early |
| Week 1 | Tool system too complex | Start with 3 tools, add later |
| Week 2 | Context engine hard | Start with simple truncation |
| Week 2 | Goal engine scope creep | Strict phase boundaries |
| Week 3 | Memory system complex | Ship basic graph, enhance later |
| Week 3 | Testing incomplete | Write tests alongside code |

## Future Roadmap (Post v0.1.0)

### v0.2.0 — Enhanced Loop Engineering
- Goal templates (common patterns)
- Goal dependencies (A blocks B)
- Goal history and analytics
- Cost optimization suggestions

### v0.3.0 — Advanced Memory
- Session summaries auto-generated
- Cross-project memory sharing
- Memory decay (old facts lose relevance)
- Memory importance scoring

### v0.4.0 — Plugin System
- Custom tools via Python packages
- Custom LLM providers
- Custom permission rules
- Custom compaction strategies

### v0.5.0 — Web UI
- Browser-based dashboard
- Real-time agent monitoring
- Goal visualization
- Memory graph explorer
