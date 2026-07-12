# Copyright (c) 2026 Sourav Kumar Dubey. All rights reserved.
# SPDX-License-Identifier: MIT
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""rapier-ai — main entry point and REPL."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from rapier import __version__
from rapier.loop import agent_loop, AgentResult
from rapier.tools.base import get_all_tools
from rapier.llm.types import ToolCall, ToolResult

console = Console()

SYSTEM_PROMPT = """You are rapier-ai, a loop-engineered coding agent.

You have access to tools that let you read, write, edit files, and run commands.
Always read files before writing or editing them.
Run tests after making changes.
If a task is complex, break it into smaller steps.

Current working directory: {cwd}"""


@click.command()
@click.version_option(version=__version__, prog_name="rapier")
@click.option("--provider", default="anthropic", help="LLM provider (anthropic/openai)")
@click.option("--model", default=None, help="Model name override")
@click.option("--goal", default=None, help="Autonomous goal to iterate on")
@click.option("--budget", default="standard", help="Budget profile (quick/standard/deep)")
@click.option("--max-turns", default=50, help="Maximum iterations")
@click.option("--no-tools", is_flag=True, help="Disable tool execution (chat only)")
def cli(
    provider: str,
    model: str | None,
    goal: str | None,
    budget: str,
    max_turns: int,
    no_tools: bool,
) -> None:
    """rapier — a loop-engineered coding agent."""
    console.print(
        Panel(
            f"[bold]rapier-ai[/bold] v{__version__}\n"
            f"Provider: {provider} | Tools: {'off' if no_tools else 'on'}\n"
            f"Type [cyan]/help[/cyan] for commands, [cyan]/quit[/cyan] to exit",
            title="🗡️  rapier-ai",
            border_style="cyan",
        )
    )

    if goal:
        asyncio.run(_run_goal(goal, provider, model, budget, max_turns, no_tools))
    else:
        asyncio.run(_run_repl(provider, model, max_turns, no_tools))


async def _run_repl(provider: str, model: str | None, max_turns: int, no_tools: bool) -> None:
    """Run interactive REPL with full agent loop."""
    from rapier.llm import get_client

    llm = get_client(provider, model)
    tools = {} if no_tools else get_all_tools()
    system_prompt = SYSTEM_PROMPT.format(cwd=Path.cwd())

    # Track conversation history across turns
    conversation_history: list[dict] = []

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]you[/bold green]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        cmd = user_input.strip()

        if cmd in ("/quit", "/exit", "/q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if cmd == "/help":
            _show_help()
            continue

        if cmd == "/clear":
            conversation_history.clear()
            console.print("[dim]Conversation cleared.[/dim]")
            continue

        if cmd == "/tools":
            if tools:
                console.print("[bold]Available tools:[/bold]")
                for name, tool in tools.items():
                    console.print(f"  [cyan]{name}[/cyan] — {tool.description}")
            else:
                console.print("[dim]Tools disabled (--no-tools)[/dim]")
            continue

        if not cmd:
            continue

        # Callbacks for live display
        async def on_tool_call(tc: ToolCall) -> None:
            console.print(f"  [dim]→ calling {tc.name}({tc.input})[/dim]")

        async def on_tool_result(tr: ToolResult) -> None:
            status = "[red]error[/red]" if tr.is_error else "[green]ok[/green]"
            preview = tr.content[:200] + "..." if len(tr.content) > 200 else tr.content
            console.print(f"  [dim]← {status}: {preview}[/dim]")

        # Run through the full agent loop
        console.print("[bold cyan]rapier[/bold cyan]", end="")

        try:
            result: AgentResult = await agent_loop(
                prompt=user_input,
                tools=tools,
                llm=llm,
                system_prompt=system_prompt,
                max_iterations=max_turns,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            )

            if result.content:
                console.print(f" {result.content}")

            # Show usage stats
            console.print(
                f"  [dim]({result.usage.input_tokens} in / {result.usage.output_tokens} out / "
                f"{result.iterations} turns)[/dim]"
            )

        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


async def _run_goal(
    goal: str,
    provider: str,
    model: str | None,
    budget: str,
    max_turns: int,
    no_tools: bool,
) -> None:
    """Run autonomous goal loop with budget tracking."""
    from rapier.llm import get_client
    from rapier.goals.engine import GoalEngine

    llm = get_client(provider, model)
    tools = {} if no_tools else get_all_tools()
    system_prompt = SYSTEM_PROMPT.format(cwd=Path.cwd())

    # Create and track the goal
    goal_engine = GoalEngine()
    g = goal_engine.create(objective=goal, budget=budget)

    console.print(f"\n[bold]Goal:[/bold] {g.objective}")
    console.print(f"[dim]Budget: {g.budget} | Max turns: {max_turns} | Tools: {'off' if no_tools else 'on'}[/dim]")
    console.print("[dim]Starting loop...[/dim]\n")

    # Callbacks for live display + budget tracking
    async def on_tool_call(tc: ToolCall) -> None:
        console.print(f"  [dim]→ calling {tc.name}({tc.input})[/dim]")

    async def on_tool_result(tr: ToolResult) -> None:
        status = "[red]error[/red]" if tr.is_error else "[green]ok[/green]"
        preview = tr.content[:200] + "..." if len(tr.content) > 200 else tr.content
        console.print(f"  [dim]← {status}: {preview}[/dim]")

    try:
        result: AgentResult = await agent_loop(
            prompt=f"Complete this goal: {goal}",
            tools=tools,
            llm=llm,
            system_prompt=system_prompt,
            max_iterations=max_turns,
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
        )

        # Record final usage
        goal_engine.record_usage(g.id, result.usage.input_tokens, result.usage.output_tokens)
        for _ in range(result.iterations):
            goal_engine.record_turn(g.id)

        # Mark goal complete
        goal_engine.complete(g.id, result=result.content)

        console.print("\n[bold green]═══ Goal Complete ═══[/bold green]")
        if result.content:
            console.print(result.content)
        console.print(f"[dim]{goal_engine.format_status(g.id)}[/dim]")

    except Exception as e:
        goal_engine.fail(g.id, reason=str(e))
        console.print(f"\n[red]Error: {e}[/red]")
        console.print(f"[dim]{goal_engine.format_status(g.id)}[/dim]")


def _show_help() -> None:
    """Show help message."""
    help_text = """
## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help |
| `/tools` | List available tools |
| `/clear` | Clear conversation |
| `/quit` | Exit rapier |

## Usage

Just type naturally to chat with rapier. The agent can:
- Read and write files
- Run shell commands
- Search codebases
- Implement features
- Fix bugs

## Goal Mode

```bash
rapier --goal "add dark mode to settings"
```

Set a goal and rapier will iterate until it's done.

## Options

| Flag | Description |
|------|-------------|
| `--provider` | LLM provider: anthropic (default) or openai |
| `--model` | Model name override |
| `--max-turns` | Max iterations (default: 50) |
| `--no-tools` | Disable tools, chat only |
| `--budget` | Budget profile: quick/standard/deep |
"""
    console.print(Markdown(help_text))


if __name__ == "__main__":
    cli()
