"""
MCP Tool Wrapper for MultiClaw

Bridges registered MCP servers into the AgentToolRegistry so that
the existing plan → validate → vote → execute pipeline picks them up
exactly like built-in tools.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from tool_registry import AgentToolRegistry, ToolExecutionContext

logger = logging.getLogger(__name__)

_MCP_SOURCE_PREFIX = "mcp:"


class MCPDynamicTool:
    """Wraps a single MCP server tool as a ToolProtocol-compatible object."""

    def __init__(
        self,
        server_name: str,
        tool_name: str,
        description: str,
        input_schema: Dict[str, Any],
        mcp_runtime: Any,
    ) -> None:
        self.server_name = server_name
        self.mcp_tool_name = tool_name
        self.name = f"{server_name}__{tool_name}"
        self.description = f"[MCP:{server_name}] {description}"
        self.source = f"{_MCP_SOURCE_PREFIX}{server_name}"
        self._input_schema = input_schema
        self._mcp_runtime = mcp_runtime

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        required = (
            self._input_schema.get("required", [])
            if isinstance(self._input_schema, dict)
            else []
        )
        errors = []
        for field in required:
            if field not in params:
                errors.append(f"required param '{field}' is missing")
        return errors

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        result = await asyncio.to_thread(
            self._mcp_runtime.call_tool,
            self.server_name,
            self.mcp_tool_name,
            params,
        )
        if result.success:
            return {
                "success": True,
                "content": result.content,
                "server": result.server_name,
                "tool": result.tool_name,
            }
        return {
            "success": False,
            "error": result.message,
            "server": result.server_name,
            "tool": result.tool_name,
        }


def refresh_mcp_tools(registry: AgentToolRegistry, mcp_runtime: Any) -> int:
    """Remove stale MCP tool entries and re-register all tools from available servers.

    Returns the number of tools successfully registered.
    Called at startup and after each Tool Manager register/delete operation.
    """
    # Remove all previously registered MCP tools
    stale = [
        k
        for k, v in list(registry._tools.items())
        if str(getattr(v, "source", "")).startswith(_MCP_SOURCE_PREFIX)
    ]
    for key in stale:
        del registry._tools[key]

    registered = 0
    for server in mcp_runtime.available_servers():
        try:
            tools = mcp_runtime.list_tools(server.name)
            for tool_def in tools:
                tool_name = str(tool_def.get("name", "")).strip()
                if not tool_name:
                    continue
                desc = str(tool_def.get("description", tool_name))
                schema = tool_def.get("inputSchema", {})
                if not isinstance(schema, dict):
                    schema = {}
                wrapper = MCPDynamicTool(
                    server_name=server.name,
                    tool_name=tool_name,
                    description=desc,
                    input_schema=schema,
                    mcp_runtime=mcp_runtime,
                )
                registry.register(wrapper)
                registered += 1
                logger.info("Registered MCP tool: %s", wrapper.name)
        except Exception as exc:
            logger.warning("Failed to load tools from MCP server '%s': %s", server.name, exc)

    if registered:
        logger.info("MCP tools loaded: %d tool(s) across %d server(s)", registered, len(mcp_runtime.available_servers()))
    return registered
