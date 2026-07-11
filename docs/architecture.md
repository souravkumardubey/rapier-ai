# rapier-ai — System Architecture

## 1. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│                    (REPL / CLI / Future TUI)                  │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                      PERMISSION GATE                         │
│              deny → safety → allow → ask user                │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Main Loop)                   │
│                                                              │
│  while (!goal_complete && !budget_exhausted) {               │
│    1. RECALL  — fetch relevant memory + context              │
│    2. PLAN    — decide next action                           │
│    3. ACT     — dispatch to specialist agent                 │
│    4. VERIFY  — checker agent reviews work                   │
│    5. LEARN   — extract durable facts to memory              │
│  }                                                           │
└──────────┬──────────────────────┬────────────────────────────┘
           │                      │
           ▼                      ▼
┌─────────────────────┐  ┌─────────────────────┐
│   AGENT POOL        │  │   CONTEXT ENGINE     │
│                     │  │                     │
│  ┌──────────────┐   │  │  ┌───────────────┐  │
│  │ Coder        │   │  │  │ History       │  │
│  │ (Sonnet)     │   │  │  │ Compactor     │  │
│  ├──────────────┤   │  │  │ Token Counter │  │
│  │ Researcher   │   │  │  └───────────────┘  │
│  │ (Haiku)      │   │  │                     │
│  ├──────────────┤   │  └─────────────────────┘
│  │ Verifier     │   │
│  │ (Opus)       │   │
│  └──────────────┘   │
└─────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                       TOOL SYSTEM                            │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Read     │ │ Write    │ │ Edit     │ │ Bash     │        │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤        │
│  │ Grep     │ │ Glob     │ │ WebFetch │ │ Task     │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
└──────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                       MEMORY SYSTEM                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Knowledge Graph: Topic → Concept → Fact              │    │
│  │ SQLite persistence + Vector recall                   │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## 2. Data Flow

### Single Turn Flow

```
User Input
    │
    ▼
Permission Gate ──BLOCK──► Deny Message
    │
    │ ALLOW
    ▼
Context Engine
    │
    │ Assembles: system_prompt + memory_recall + history + user_input
    ▼
LLM Client
    │
    │ Sends to Anthropic/OpenAI
    ▼
LLM Response
    │
    ├─ No tool calls ──► Return text to user ──► Done
    │
    └─ Has tool calls
        │
        ▼
    For each tool_call:
        │
        ▼
    Permission Gate ──BLOCK──► Skip tool, return error
        │
        │ ALLOW
        ▼
    Tool.execute()
        │
        ▼
    Tool Result
        │
        ▼
    Append to messages
        │
        ▼
    Continue loop (next LLM call)
```

### Goal Loop Flow

```
rapier --goal "add dark mode to settings"
    │
    ▼
Goal Engine: Create goal(status=active, budget=standard)
    │
    ▼
┌─► Orchestrator Loop ◄─────────────────────────────┐
│       │                                            │
│       ▼                                            │
│   Research Phase                                    │
│       │                                            │
│       ▼                                            │
│   Coder: Implement feature                         │
│       │                                            │
│       ▼                                            │
│   Verifier: Run tests + review code                │
│       │                                            │
│       ├─ Pass ──► Goal Complete ──► Done           │
│       │                                            │
│       └─ Fail ──► Coder: Fix issues                │
│                       │                            │
│                       └────────────────────────────┘
│
│   Budget check: tokens_used >= budget?
│       ├─ Yes ──► Goal Failed (budget exhausted)
│       └─ No ──► Continue loop
└──────────────────────────────────────────────────────
```

## 3. Component Responsibilities

### Agent Loop (`loop.py`)
- **Single responsibility:** Orchestrate the perceive→reason→act→observe cycle
- **State:** Holds message history, tracks iterations
- **No business logic:** Delegates to tools, agents, and context engine

### LLM Client (`llm/`)
- **Single responsibility:** Communicate with LLM providers
- **Abstraction:** Same interface for Anthropic, OpenAI, future providers
- **Streaming:** Token-by-token response handling

### Tool System (`tools/`)
- **Single responsibility:** Execute actions in the real world
- **Registry pattern:** Auto-discovery via decorator
- **Each tool:** One file, one class, one clear purpose

### Context Engine (`context/`)
- **Single responsibility:** Manage what the LLM sees each turn
- **Compaction:** 5-tier strategy to stay within token limits
- **Token counting:** Accurate counting via tiktoken

### Permission System (`permissions/`)
- **Single responsibility:** Safety — prevent harmful actions
- **Deny-first:** Unknown commands are blocked by default
- **Bash analyzer:** AST parsing, not regex matching

### Goal Engine (`goals/`)
- **Single responsibility:** Track objectives and budgets
- **Lifecycle:** created → active → complete/blocked/failed/paused
- **Verification:** Uses different model to check completion

### Multi-Agent System (`agents/`)
- **Single responsibility:** Orchestrate specialist agents
- **Hub-and-spoke:** Coordinator holds full context, workers get minimal
- **Maker/Checker:** Different model writes code vs. verifies it

### Memory System (`memory/`)
- **Single responsibility:** Persistent knowledge across sessions
- **Knowledge graph:** Topic → Concept → Fact hierarchy
- **Vector recall:** Find relevant memories by semantic similarity

## 4. Key Interfaces

```python
# LLM Client
class LLMClient(Protocol):
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        system: str | None = None,
    ) -> LLMResponse: ...

# Base Tool
class BaseTool(ABC):
    name: str
    description: str
    
    @abstractmethod
    def get_schema(self) -> ToolDefinition: ...
    
    @abstractmethod
    async def execute(self, input: dict[str, Any]) -> str: ...

# Goal
@dataclass
class Goal:
    id: str
    objective: str
    status: Literal["active", "complete", "blocked", "failed", "paused"]
    budget: Budget
    tokens_used: int
    turns_used: int

# Memory
class MemoryStore(ABC):
    async def store(self, fact: Fact) -> None: ...
    async def recall(self, query: str, limit: int = 10) -> list[Fact]: ...
```

## 5. Error Handling Strategy

| Error Type | Handling |
|---|---|
| LLM API error | Retry with backoff, fallback to other provider |
| Tool execution error | Return error message to LLM, let it decide |
| Permission denied | Return "permission denied" to LLM |
| Context overflow | Trigger compaction, retry |
| Budget exhausted | Stop goal, report to user |
| Unknown error | Log, return generic error, continue |

## 6. Security Model

### Permission Decision Cascade
1. **Deny rules** — Hard block (cannot be overridden)
2. **Safety rules** — Dangerous patterns (can be overridden in auto mode)
3. **Allow rules** — Pre-approved operations
4. **Mode check** — Auto/plan/default determines if user is asked
5. **User prompt** — Last resort, ask for confirmation

### Protected Paths
- `.git/` — Never modify
- `.rapier/` — Agent's own state
- `.env` — Environment secrets
- `node_modules/` — Dependencies
- `__pycache__/` — Python cache

### Bash Safety
- Parse AST, not regex
- Block command substitution: `$()`, backticks
- Block destructive commands: `rm -rf`, `dd`, `mkfs`
- Block dangerous builtins: `eval`, `source`, `exec`, `trap`
- Timeout all commands (default 30s)
