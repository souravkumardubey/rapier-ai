"""rapier-ai — base tool class and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from rapier.llm.types import ToolDefinition


# Global tool registry
TOOL_REGISTRY: dict[str, type[BaseTool]] = {}


def register_tool(cls: type[BaseTool]) -> type[BaseTool]:
    """Decorator to register a tool class."""
    TOOL_REGISTRY[cls.name] = cls
    return cls


def get_all_tools() -> dict[str, BaseTool]:
    """Instantiate and return all registered tools."""
    return {name: cls() for name, cls in TOOL_REGISTRY.items()}


class BaseTool(ABC):
    """Abstract base class for all tools."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def get_schema(self) -> ToolDefinition:
        """Return the JSON schema for this tool's input."""
        ...

    @abstractmethod
    async def execute(self, input: dict[str, Any]) -> str:
        """Execute the tool and return result as string."""
        ...
