from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from runtime_config import RuntimeConfig
from session_context import SessionContext
from tool_policy import ToolPolicy


@dataclass(frozen=True)
class ToolExecutionContext:
    session_context: SessionContext
    runtime_config: RuntimeConfig
    tool_policy: ToolPolicy


class ToolProtocol(Protocol):
    name: str
    description: str
    source: str

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        ...

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        ...


class AgentToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolProtocol] = {}

    def register(self, tool: ToolProtocol) -> None:
        self._tools[tool.name] = tool

    def get(self, tool_name: str) -> Optional[ToolProtocol]:
        return self._tools.get(tool_name)

    def has(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def describe(self) -> str:
        lines = []
        for name in sorted(self._tools):
            tool = self._tools[name]
            lines.append(f"- {name}: {tool.description}")
        return "\n".join(lines)

    def list_tools(self) -> List[Dict[str, str]]:
        tools = []
        for name in sorted(self._tools):
            tool = self._tools[name]
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "source": getattr(tool, "source", "core"),
                }
            )
        return tools

    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: ToolExecutionContext,
    ) -> Dict[str, Any]:
        tool = self.get(tool_name)
        if tool is None:
            return {"success": False, "error": f"unknown tool: {tool_name}"}
        return await tool.execute(params, context)
