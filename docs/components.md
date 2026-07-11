# rapier-ai — Component Deep-Dive

## 1. Agent Loop (`loop.py`)

The heart of rapier-ai. A simple `while(true)` loop that drives everything.

### Pseudocode
```python
async def agent_loop(
    prompt: str,
    tools: dict[str, BaseTool],
    llm: LLMClient,
    system_prompt: str,
    max_iterations: int = 50,
    on_tool_call: Callable | None = None,
    on_tool_result: Callable | None = None,
) -> AgentResult:
    messages = [Message(role="user", content=prompt)]
    
    for i in range(max_iterations):
        # Call LLM
        response = await llm.chat(
            messages=messages,
            tools=[t.get_schema() for t in tools.values()],
            system=system_prompt,
        )
        
        # No tool calls = done
        if not response.tool_calls:
            return AgentResult(
                content=response.content,
                iterations=i + 1,
                usage=response.usage,
            )
        
        # Append assistant message
        messages.append(Message(
            role="assistant",
            content=response.content,
            tool_calls=response.tool_calls,
        ))
        
        # Execute each tool call
        for tool_call in response.tool_calls:
            tool = tools.get(tool_call.name)
            if not tool:
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    content=f"Unknown tool: {tool_call.name}",
                    is_error=True,
                )
            else:
                # Fire callback
                if on_tool_call:
                    await on_tool_call(tool_call)
                
                # Execute
                output = await tool.execute(tool_call.input)
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    content=output,
                )
                
                # Fire callback
                if on_tool_result:
                    await on_tool_result(result)
            
            # Append result
            messages.append(Message(
                role="tool",
                content=result.content,
                tool_call_id=result.tool_call_id,
            ))
    
    return AgentResult(
        content="Hit iteration limit",
        iterations=max_iterations,
        usage=total_usage,
    )
```

### Design Decisions
- **Generator pattern** could be used for streaming, but async/await is simpler for v1
- **Callbacks** allow UI to display tool calls/results without coupling
- **Max iterations** prevents runaway loops
- **AgentResult** captures all metadata for logging/budget tracking

---

## 2. LLM Client (`llm/`)

Provider-agnostic interface with adapters for each LLM provider.

### Interface
```python
class LLMClient(Protocol):
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        system: str | None = None,
        model: str | None = None,
    ) -> LLMResponse: ...
```

### Anthropic Adapter
```python
class AnthropicClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
    
    async def chat(self, messages, tools, system=None, model=None):
        # Convert messages to Anthropic format
        # Convert tools to Anthropic format
        # Call API
        # Parse response
        # Return LLMResponse
```

### OpenAI Adapter
```python
class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def chat(self, messages, tools, system=None, model=None):
        # Convert messages to OpenAI format
        # Convert tools to OpenAI format
        # Call API
        # Parse response
        # Return LLMResponse
```

### Why Separate Adapters?
- Each provider has different message formats
- Different tool calling schemas
- Different error handling
- Easy to add new providers without changing core code

---

## 3. Tool System (`tools/`)

Registry pattern with auto-discovery via decorator.

### Registry
```python
TOOL_REGISTRY: dict[str, type[BaseTool]] = {}

def register_tool(cls: type[BaseTool]) -> type[BaseTool]:
    """Decorator to register a tool class."""
    TOOL_REGISTRY[cls.name] = cls
    return cls

def get_all_tools() -> dict[str, BaseTool]:
    """Instantiate and return all registered tools."""
    return {name: cls() for name, cls in TOOL_REGISTRY.items()}
```

### Tool Interface
```python
class BaseTool(ABC):
    name: str
    description: str
    
    @abstractmethod
    def get_schema(self) -> ToolDefinition:
        """Return the JSON schema for this tool's input."""
        ...
    
    @abstractmethod
    async def execute(self, input: dict[str, Any]) -> str:
        """Execute the tool and return result as string."""
        ...
```

### Example: Read File Tool
```python
@register_tool
class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a file at the given path"
    
    def get_schema(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file"
                    }
                },
                "required": ["path"]
            }
        )
    
    async def execute(self, input: dict[str, Any]) -> str:
        path = Path(input["path"])
        if not path.exists():
            return f"Error: File not found: {path}"
        if not path.is_file():
            return f"Error: Not a file: {path}"
        
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")
        
        if len(lines) > 2000:
            truncated = "\n".join(lines[:2000])
            remaining = len(lines) - 2000
            return f"{truncated}\n\n... ({remaining} more lines)"
        
        return content
```

---

## 4. Context Engine (`context/`)

Manages what the LLM sees each turn. The 5-tier compaction strategy.

### Tier 1: Snip
```python
async def snip_old_results(messages: list[Message], max_age_minutes: int = 60) -> list[Message]:
    """Replace old tool results with placeholder."""
    now = datetime.now()
    for msg in messages:
        if msg.role == "tool" and msg.age > max_age_minutes:
            msg.content = "[Old tool result content cleared]"
    return messages
```

### Tier 2: Microcompact
```python
async def microcompact(messages: list[Message]) -> list[Message]:
    """Remove stale tool results while preserving cache prefix."""
    # Find last tool_use index
    # Keep recent tool results, clear older ones
    # Preserve message order for cache hits
    return messages
```

### Tier 3: Context Collapse
```python
async def collapse_tool_outputs(messages: list[Message]) -> list[Message]:
    """Summarize large tool outputs."""
    for msg in messages:
        if msg.role == "tool" and len(msg.content) > 5000:
            msg.content = await summarize(msg.content)
    return messages
```

### Tier 4: Autocompact
```python
async def autocompact(messages: list[Message], llm: LLMClient) -> list[Message]:
    """Summarize entire conversation history."""
    summary = await llm.chat([
        Message(role="user", content=f"Summarize this conversation:\n{format_messages(messages)}")
    ])
    return [Message(role="assistant", content=summary.content)]
```

### Tier 5: Reactive
```python
async def reactive_compact(messages: list[Message]) -> list[Message]:
    """Emergency truncation when API returns prompt_too_long."""
    # Keep system message
    # Keep last 5 messages
    # Drop everything in between
    return messages[:1] + messages[-5:]
```

### Circuit Breaker
```python
class CompactionCircuitBreaker:
    def __init__(self, max_failures: int = 3):
        self.failures = 0
        self.max_failures = max_failures
        self.open = False
    
    def record_failure(self):
        self.failures += 1
        if self.failures >= self.max_failures:
            self.open = True
    
    def record_success(self):
        self.failures = 0
    
    def is_open(self) -> bool:
        return self.open
```

---

## 5. Permission System (`permissions/`)

Safety rails with deny-first philosophy.

### Decision Flow
```python
class PermissionGate:
    def __init__(self, rules: PermissionRules, mode: str = "default"):
        self.rules = rules
        self.mode = mode  # "default", "auto", "plan"
    
    async def check(self, tool_name: str, input: dict) -> PermissionResult:
        # 1. Check deny rules
        if self.rules.is_denied(tool_name, input):
            return PermissionResult.DENIED
        
        # 2. Check safety rules
        if self.rules.is_dangerous(tool_name, input):
            if self.mode == "auto":
                return PermissionResult.ALLOWED
            return await self.ask_user(tool_name, input)
        
        # 3. Check allow rules
        if self.rules.is_allowed(tool_name, input):
            return PermissionResult.ALLOWED
        
        # 4. Default: ask user
        if self.mode == "auto":
            return PermissionResult.ALLOWED
        return await self.ask_user(tool_name, input)
```

### Bash Analyzer
```python
class BashAnalyzer:
    """AST-based bash command safety analyzer."""
    
    DANGEROUS_BUILTINS = {"eval", "source", "exec", "trap", "kill", "suspend"}
    DANGEROUS_PATTERNS = {
        "command_substitution": r"\$\(|`",
        "process_substitution": r"<\(|>\(",
        "destructive_commands": r"\brm\s+-rf\b|\bdd\b|\bmkfs\b",
    }
    
    def analyze(self, command: str) -> BashAnalysis:
        # Parse AST
        tree = bash_parser.parse(command)
        
        # Check for dangerous patterns
        issues = []
        for node in ast.walk(tree):
            if self.is_dangerous(node):
                issues.append(f"Dangerous: {node.type}")
        
        return BashAnalysis(
            safe=len(issues) == 0,
            issues=issues,
            risk_level=self.calculate_risk(issues),
        )
```

---

## 6. Goal Engine (`goals/`)

Track objectives and budgets with verification.

### Goal Lifecycle
```python
class GoalEngine:
    async def create(self, objective: str, budget: str = "standard") -> Goal:
        goal = Goal(
            id=str(uuid4()),
            objective=objective,
            status="active",
            budget=BUDGETS[budget],
            created_at=datetime.now(),
        )
        await self.store.save(goal)
        return goal
    
    async def check_budget(self, goal: Goal) -> bool:
        """Return True if budget is exhausted."""
        if goal.budget.tokens and goal.tokens_used >= goal.budget.tokens:
            return True
        if goal.budget.turns and goal.turns_used >= goal.budget.turns:
            return True
        if goal.budget.hours:
            elapsed = (datetime.now() - goal.created_at).total_seconds() / 3600
            if elapsed >= goal.budget.hours:
                return True
        return False
```

### Verifier
```python
class GoalVerifier:
    """Uses a different model to verify goal completion."""
    
    async def verify(self, goal: Goal, evidence: str) -> VerificationResult:
        prompt = f"""
        Goal: {goal.objective}
        
        Evidence of completion:
        {evidence}
        
        Is this goal complete? Respond with JSON:
        {{"complete": true/false, "reason": "..."}}
        """
        
        # Use different model than the coder
        response = await self.verifier_llm.chat([
            Message(role="user", content=prompt)
        ])
        
        result = json.loads(response.content)
        return VerificationResult(
            complete=result["complete"],
            reason=result["reason"],
        )
```

---

## 7. Multi-Agent System (`agents/`)

Hub-and-spoke orchestration with specialist agents.

### Coordinator
```python
class Coordinator:
    def __init__(self, agents: dict[str, Agent]):
        self.agents = agents
    
    async def execute(self, task: str, goal: Goal) -> str:
        # 1. Research phase
        research = await self.agents["researcher"].run(
            f"Research how to: {task}"
        )
        
        # 2. Implementation phase
        code = await self.agents["coder"].run(
            f"Implement: {task}\n\nResearch:\n{research}"
        )
        
        # 3. Verification phase
        for attempt in range(3):
            verification = await self.agents["verifier"].run(
                f"Verify this code:\n{code}\n\nTask: {task}"
            )
            
            if verification.passed:
                return code
            
            # Fix issues
            code = await self.agents["coder"].run(
                f"Fix these issues:\n{verification.issues}\n\nCode:\n{code}"
            )
        
        return code  # Max attempts reached
```

### Agent Interface
```python
class Agent:
    def __init__(self, name: str, llm: LLMClient, tools: list[BaseTool]):
        self.name = name
        self.llm = llm
        self.tools = {t.name: t for t in tools}
    
    async def run(self, task: str) -> AgentResult:
        return await agent_loop(
            prompt=task,
            tools=self.tools,
            llm=self.llm,
            system_prompt=self.get_system_prompt(),
        )
```

---

## 8. Memory System (`memory/`)

Persistent knowledge graph with vector recall.

### Knowledge Graph
```python
class KnowledgeGraph:
    def __init__(self, store: MemoryStore):
        self.store = store
    
    async def store_fact(self, topic: str, concept: str, fact: str, source: str):
        embedding = await self.embed(fact)
        await self.store.save(Fact(
            topic=topic,
            concept=concept,
            fact=fact,
            source=source,
            embedding=embedding,
        ))
    
    async def recall(self, query: str, limit: int = 10) -> list[Fact]:
        query_embedding = await self.embed(query)
        return await self.store.search(query_embedding, limit=limit)
```

### Auto-Extractor
```python
class FactExtractor:
    """Extracts durable facts from tool results."""
    
    async def extract(self, tool_name: str, result: str) -> list[Fact]:
        prompt = f"""
        Extract durable facts from this tool result:
        
        Tool: {tool_name}
        Result: {result}
        
        Return JSON array of facts:
        [{{"topic": "...", "concept": "...", "fact": "..."}}]
        """
        
        response = await self.llm.chat([Message(role="user", content=prompt)])
        return json.loads(response.content)
```

### Vector Recall
```python
class VectorRecall:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed(self, text: str) -> np.ndarray:
        return self.model.encode(text)
    
    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
```
