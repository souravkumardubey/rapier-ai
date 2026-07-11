# rapier-ai — Development Workflow

## 1. Branch Strategy

```
main ─────────────────────────────────────────────►
  │
  ├── phase-1-core-loop ──────► merge
  │
  ├── phase-2-tools ──────────► merge
  │
  ├── phase-3-permissions ────► merge
  │
  ├── phase-4-context ────────► merge
  │
  ├── phase-5-goals ──────────► merge
  │
  ├── phase-6-multi-agent ────► merge
  │
  ├── phase-7-memory ─────────► merge
  │
  └── phase-8-polish ─────────► merge → v0.1.0
```

**Rule:** Each phase gets its own branch. Merge to main only when phase is complete and tests pass.

## 2. Daily Workflow

### Morning
1. Pull latest `main`
2. Rebase feature branch
3. Review what's pending from yesterday
4. Pick highest priority task

### During Development
1. Write code in small chunks (10-30 lines)
2. Run tests after each chunk
3. Run linter before commit
4. Commit with descriptive message

### Before Commit
```bash
# Always run these in order:
ruff check .          # Lint
ruff format .         # Format
mypy rapier/          # Type check
pytest tests/         # Test
git add -p            # Stage selectively
git commit            # Descriptive message
```

### End of Day
1. Push branch to origin
2. Write brief progress notes
3. Update todo list

## 3. Commit Convention

```
<type>: <description>

Types:
  feat     — New feature
  fix      — Bug fix
  docs     — Documentation only
  refactor — Code restructure (no behavior change)
  test     — Adding tests
  chore    — Build, config, tooling

Examples:
  feat: implement agent loop with tool dispatch
  fix: handle empty tool call response
  docs: add architecture diagram
  refactor: extract LLM client interface
  test: add unit tests for bash analyzer
  chore: add pytest config
```

## 4. Code Review Checklist

Before merging each phase:

- [ ] All tests pass
- [ ] No type errors (mypy)
- [ ] No lint errors (ruff)
- [ ] Code follows existing patterns
- [ ] No hardcoded secrets or API keys
- [ ] Docstrings on public interfaces
- [ ] CLAUDE.md updated if architecture changed
- [ ] README updated if usage changed

## 5. Testing Strategy

### Unit Tests
- Every tool has a test file
- Every LLM provider has a mock test
- Permission gate has exhaustive test cases
- Context compactor has edge case tests

### Integration Tests
- Full agent loop with mocked LLM
- Tool registry auto-discovery
- Goal lifecycle (create → active → complete)
- Memory graph (store → recall → verify)

### Manual Testing
- Run `python -m rapier` and use it yourself
- Test on real codebase tasks
- Verify permissions work correctly

## 6. Project Board Organization

```
│ Phase 1: Core Loop    │ Phase 2: Tools      │ Phase 3: Permissions │
├───────────────────────┼─────────────────────┼──────────────────────┤
│ □ LLM types           │ □ BaseTool ABC      │ □ Permission gate    │
│ □ LLM client          │ □ Read file tool    │ □ Deny rules         │
│ □ Anthropic adapter   │ □ Write file tool   │ □ Bash analyzer      │
│ □ OpenAI adapter      │ □ Edit file tool    │ □ Safety rules       │
│ □ Agent loop          │ □ Bash tool         │ □ UI prompts         │
│ □ REPL                │ □ Grep tool         │                      │
│ □ pyproject.toml      │ □ Glob tool         │                      │
│ □ CLAUDE.md           │ □ Web fetch tool    │                      │
│                       │ □ Tool registry     │                      │
```

## 7. Debugging Workflow

### When tests fail
1. Read the error message carefully
2. Check if it's a type error, logic error, or test error
3. Add print/debug statement if needed
4. Fix the root cause, not the symptom
5. Run tests again

### When the agent loop hangs
1. Check max_iterations isn't too high
2. Check if tool is blocking (add timeout)
3. Check if LLM response is malformed
4. Add logging to loop.py

### When context blows up
1. Check token counting
2. Check compaction triggers
3. Log context size at each turn
4. Add circuit breaker if needed

## 8. Release Workflow

### Pre-release (v0.1.0-rc1)
1. All phases complete
2. All tests passing
3. README complete
4. Install and test on clean venv

### Release (v0.1.0)
1. Tag release: `git tag v0.1.0`
2. Build: `python -m build`
3. Publish: `twine upload dist/*`
4. Create GitHub Release with notes

### Post-release
1. Monitor issues
2. Fix critical bugs
3. Plan v0.2.0 features
