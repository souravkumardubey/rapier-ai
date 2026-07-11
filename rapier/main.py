"""rapier-ai — main entry point and REPL."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from rapier import __version__

console = Console()

SYSTEM_PROMPT = """You are rapier-ai, a loop-engineered coding agent.

You have access to tools that let you read, write, edit files, and run commands.
Always read files before writing or editing them.
Run tests after making changes.
If a task is complex, break it into smaller steps."""


@click.command()
@click.version_option(version=__version__, prog_name="rapier")
@click.option("--provider", default="anthropic", help="LLM provider (anthropic/openai)")
@click.option("--model", default=None, help="Model name override")
@click.option("--goal", default=None, help="Autonomous goal to iterate on")
@click.option("--budget", default="standard", help="Budget profile (quick/standard/deep)")
@click.option("--max-turns", default=50, help="Maximum iterations")
def cli(
    provider: str,
    model: str | None,
    goal: str | None,
    budget: str,
    max_turns: int,
) -> None:
    """rapier — a loop-engineered coding agent."""
    console.print(
        Panel(
            f"[bold]rapier-ai[/bold] v{__version__}\n"
            f"Provider: {provider}\n"
            f"Type [cyan]/help[/cyan] for commands, [cyan]/quit[/cyan] to exit",
            title="🗡️  rapier-ai",
            border_style="cyan",
        )
    )

    if goal:
        asyncio.run(_run_goal(goal, provider, model, budget, max_turns))
    else:
        asyncio.run(_run_repl(provider, model, max_turns))


async def _run_repl(provider: str, model: str | None, max_turns: int) -> None:
    """Run interactive REPL."""
    from rapier.llm import get_client

    llm = get_client(provider, model)
    messages: list[dict] = []

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]you[/bold green]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if user_input.strip() in ("/quit", "/exit", "/q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if user_input.strip() == "/help":
            _show_help()
            continue

        if user_input.strip() == "/clear":
            messages.clear()
            console.print("[dim]Conversation cleared.[/dim]")
            continue

        messages.append({"role": "user", "content": user_input})

        console.print("[bold cyan]rapier[/bold cyan]", end="")

        try:
            response = await llm.chat(
                messages=messages,
                tools=[],
                system=SYSTEM_PROMPT,
            )
            content = response.content or ""
            console.print(f" {content}")
            messages.append({"role": "assistant", "content": content})
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


async def _run_goal(
    goal: str,
    provider: str,
    model: str | None,
    budget: str,
    max_turns: int,
) -> None:
    """Run autonomous goal loop."""
    console.print(f"\n[bold]Goal:[/bold] {goal}")
    console.print(f"[dim]Budget: {budget} | Max turns: {max_turns}[/dim]")
    console.print("[dim]Starting loop...[/dim]\n")

    # Phase 5 will implement the full goal engine
    # For now, just run a basic loop
    from rapier.llm import get_client

    llm = get_client(provider, model)
    messages: list[dict] = [
        {"role": "user", "content": f"Complete this goal: {goal}"}
    ]

    for turn in range(max_turns):
        console.print(f"[dim]Turn {turn + 1}/{max_turns}[/dim]")

        try:
            response = await llm.chat(
                messages=messages,
                tools=[],
                system=SYSTEM_PROMPT,
            )
            content = response.content or ""
            console.print(f"[bold cyan]rapier:[/bold cyan] {content}\n")
            messages.append({"role": "assistant", "content": content})

            # TODO: Phase 5 — Check if goal is complete
            # TODO: Phase 5 — Check budget
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            break

    console.print("[dim]Goal loop finished.[/dim]")


def _show_help() -> None:
    """Show help message."""
    help_text = """
## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help |
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
"""
    console.print(Markdown(help_text))


if __name__ == "__main__":
    cli()
