# rapier-ai — Build Phases

## Overview

8 phases, 21 days, ~2,330 LOC. Each phase produces a working, testable increment.

---

## Phase 1: Core Loop + LLM Client (Days 1-2)

**Goal:** Working REPL that talks to an LLM and handles tool calls.

**Files to create:**
```
rapier-ai/
├── rapier/
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py
│   ├── loop.py
│   └── llm/
│       ├── __init__.py
│       ├── types.py
│       ├── client.py
│       ├── anthropic.py
│       └── openai_provider.py
├── pyproject.toml
├── .gitignore
├── .env.example
└── CLAUDE.md
```

**Key interfaces:**

```python
# types.py
@dataclass
class Usage:
    input_tokens: int
    output_tokens: int

@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]

@dataclass
class ToolResult:
    tool_call_id: str
    content: str
    is_error: bool = False

@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall]
    usage: Usage

@dataclass
class Message:
    role: Literal["user", "assistant", "system", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None

# client.py
class LLMClient(Protocol):
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        system: str | None = None,
    ) -> LLMResponse: ...

# loop.py
async def agent_loop(
    prompt: str,
    tools: dict[str, BaseTool],
    llm: LLMClient,
    system_prompt: str,
    max_iterations: int = 50,
) -> str: ...

# main.py
@click.command()
@click.option("--provider", default="anthropic", help="LLM provider")
@click.option("--model", default=None, help="Model name")
@click.option("--goal", default=None, help="Autonomous goal")
def cli(provider: str, model: str | None, goal: str | None):
    """rapier — a loop-engineered coding agent"""
    ...
```

**Deliverable:** `python -m rapier` starts REPL, conversation works.

---

## Phase 2: Tool System (Days 3-4)

**Goal:** Agent can read, write, edit files and run commands.

**Files to create:**
```
rapier/tools/
├── __init__.py
├── base.py
├── read_file.py
├── write_file.py
├── edit_file.py
├── bash.py
├── grep.py
├── glob.py
├── web_fetch.py
└── task.py
```

**Key interface:**
```python
# base.py
class BaseTool(ABC):
    name: str
    description: str
    
    @abstractmethod
    def get_schema(self) -> ToolDefinition: ...
    
    @abstractmethod
    async def execute(self, input: dict[str, Any]) -> str: ...

# Tool registry
TOOL_REGISTRY: dict[str, type[BaseTool]] = {}

def register_tool(cls: type[BaseTool]) -> type[BaseTool]:
    TOOL_REGISTRY[cls.name] = cls
    return cls

# Usage
@register_tool
class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a file"
    
    def get_schema(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            }
        )
    
    async def execute(self, input: dict[str, Any]) -> str:
        path = Path(input["path"])
        if not path.exists():
            return f"Error: File not found: {path}"
        content = path.read_text()
        lines = content.split("\n")
        if len(lines) > 2000:
            return "\n".join(lines[:2000]) + f"\n\n... ({len(lines) - 2000} more lines)"
        return content
```

**Tools to implement:**

| Tool | Purpose | Lines |
|---|---|---|
| `read_file` | Read file contents | ~35 |
| `write_file` | Create/overwrite files | ~30 |
| `edit_file` | Diff-based edit | ~45 |
| `bash` | Execute shell commands | ~40 |
| `grep` | Search file contents | ~35 |
| `glob` | Find files by pattern | ~30 |
| `web_fetch` | Fetch URLs | ~40 |
| `task` | Spawn sub-agents | ~60 |

**Deliverable:** Agent can modify your codebase.

---

## Phase 3: Permission System (Days 5-6)

**Goal:** Safety rails — block dangerous commands, prompt for risky edits.

**Files to create:**
```
rapier/permissions/
├── __init__.py
├── gate.py
├── rules.py
└── bash_analyzer.py
```

**Permission decision cascade:**
```
1. Check deny rules → BLOCK (hard deny)
2. Check safety rules → BLOCK (dangerous patterns)
3. Check allow rules → ALLOW (pre-approved)
4. Check mode (auto/plan/default) → ASK or AUTO-ALLOW
5. Prompt user → ALLOW/DENY
```

**Bash analyzer categories:**
- Command substitution: `$()`, backticks
- Process substitution: `<()`, `>()`
- Subshells: `()`
- Redirections: `>`, `>>`, `|`, `|`
- Loops: `for`, `while`, `until`
- Conditionals: `if`, `case`
- Functions: `function`, `fname()`
- Dangerous builtins: `eval`, `source`, `exec`, `trap`, `kill`, `suspend`
- Zsh-specific: `zmodload`, `ztcp`
- Destructive commands: `rm -rf`, `dd`, `mkfs`

**Deliverable:** Agent asks before dangerous operations, blocks harmful ones.

---

## Phase 4: Context Engine (Days 7-9)

**Goal:** Long conversations don't blow up the context window.

**Files to create:**
```
rapier/context/
├── __init__.py
├── engine.py
├── compactor.py
└── history.py
```

**5-Tier Compaction Strategy:**

| Tier | Name | Trigger | Action | Cost |
|---|---|---|---|---|
| 1 | Snip | Tool result >60min old | Replace with `[old result cleared]` | Free |
| 2 | Microcompact | Cache-aware | Remove stale tool results | Low |
| 3 | Context Collapse | Tool outputs large | Summarize tool outputs | Low |
| 4 | Autocompact | Context >80% full | LLM summarizes history | Medium |
| 5 | Reactive | API error | Emergency truncation | Emergency |

**Circuit breaker:** 3 consecutive compaction failures → skip compaction for session.

**Deliverable:** 50+ turn conversations work.

---

## Phase 5: Goal Engine (Days 10-12)

**Goal:** Set objectives, track budgets, verify completion.

**Files to create:**
```
rapier/goals/
├── __init__.py
├── engine.py
├── budget.py
└── verifier.py
```

**Goal states:**
```
created → active → complete
                   → blocked (waiting on external factor)
                   → failed (budget exhausted)
                   → paused (user paused)
```

**Budget profiles:**
```python
BUDGETS = {
    "quick": Budget(tokens=2_000_000, turns=50, hours=2),
    "standard": Budget(tokens=10_000_000, turns=200, hours=8),
    "deep": Budget(tokens=100_000_000, turns=1000, hours=24),
    "unlimited": Budget(tokens=None, turns=None, hours=None),
}
```

**Deliverable:** `rapier --goal "add error handling"` → iterates → verified complete.

---

## Phase 6: Multi-Agent System (Days 13-15)

**Goal:** Coordinator dispatches to specialist agents.

**Files to create:**
```
rapier/agents/
├── __init__.py
├── coordinator.py
├── coder.py
├── researcher.py
└── verifier.py
```

**Agent roles:**
| Agent | Model | Tools | Purpose |
|---|---|---|---|
| Coordinator | Opus | All | Orchestrate, decide |
| Coder | Sonnet | Read/Write/Edit/Bash | Write code |
| Researcher | Haiku | Grep/Glob/WebFetch | Research (cheap) |
| Verifier | Opus | Read/Bash/Glob | Verify (careful) |

**Maker/Checker flow:**
```
Coordinator → Coder writes code → Verifier reviews
  → Pass → Done
  → Fail → Coder fixes (max 3 rounds)
  → Still fails → Escalate to user
```

**Deliverable:** Complex tasks decomposed. Different model per role.

---

## Phase 7: Memory System (Days 16-18)

**Goal:** Persistent knowledge graph across sessions.

**Files to create:**
```
rapier/memory/
├── __init__.py
├── graph.py
├── store.py
├── recall.py
└── extractor.py
```

**Knowledge graph:**
```
Topic → Concept → Fact
  │       │         │
  │       │         └── "bcrypt with 12 rounds" (source: auth.py)
  │       └── "JWT tokens" (3 facts)
  └── "Authentication" (5 concepts)
```

**SQLite schema:**
```sql
CREATE TABLE facts (
    id TEXT PRIMARY KEY,
    topic TEXT,
    concept TEXT,
    fact TEXT,
    source_file TEXT,
    created_at TIMESTAMP,
    embedding BLOB
);
```

**Deliverable:** Agent remembers conventions across sessions.

---

## Phase 8: Polish + Ship (Days 19-21)

**Goal:** Production-ready with docs, tests, CI.

**Tasks:**
- Rich TUI with status bar, cost tracker
- Streaming token display
- Error handling, retry logic
- pytest test suite (unit + integration)
- README with badges, install, usage, architecture
- GitHub Actions CI
- PyPI publish (`pip install rapier-ai`)

**Deliverable:** Published to PyPI, installable via pip.
