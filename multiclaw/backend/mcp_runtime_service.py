from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from runtime_config import get_runtime_config
from tool_manager_models import MCPToolCallResult, ToolConfigEntry
from tool_manager_service import ToolManagerService


class MCPRuntimeService:
    def __init__(self) -> None:
        self.tool_manager = ToolManagerService()
        self.default_timeout_seconds = 15
        self.node_executable = shutil.which("node") or "node"
        config = get_runtime_config()
        self.bridge_dir = config.backend_root / "mcp_bridge"
        self.bridge_script = self.bridge_dir / "mcp_bridge.mjs"

    def available_servers(self) -> list[ToolConfigEntry]:
        return [
            entry
            for entry in self.tool_manager.list_entries()
            if (entry.transport == "stdio" and entry.command) or (entry.transport == "http" and entry.url)
        ]

    def has_server(self, name: str) -> bool:
        return self.tool_manager.get_entry(name) is not None

    def find_server_by_capability(self, capability: str, usage_scope: str | None = None) -> ToolConfigEntry | None:
        matches = self.tool_manager.get_entries_by_capability(capability, usage_scope)
        return matches[0] if matches else None

    def list_tools(self, server_name: str) -> list[dict[str, Any]]:
        payload = self._run_bridge(
            server_name,
            {
                "action": "list_tools",
                "timeout_ms": self.default_timeout_seconds * 1000,
            },
        )
        tools = payload.get("tools", [])
        return [tool for tool in tools if isinstance(tool, dict)]

    def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> MCPToolCallResult:
        try:
            payload = self._run_bridge(
                server_name,
                {
                    "action": "call_tool",
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "timeout_ms": self.default_timeout_seconds * 1000,
                },
            )
            result = payload.get("result", {})
            if not isinstance(result, dict):
                result = {}
            content = self._extract_content(result)
            return MCPToolCallResult(
                server_name=server_name,
                tool_name=tool_name,
                success=True,
                content=content,
                raw_payload=result,
                message="MCP tool call completed.",
            )
        except Exception as exc:
            return MCPToolCallResult(
                server_name=server_name,
                tool_name=tool_name,
                success=False,
                message=str(exc),
            )

    def call_tool_by_match(
        self,
        server_name: str,
        name_hints: list[str],
        arguments: dict[str, Any],
    ) -> MCPToolCallResult:
        tools = self.list_tools(server_name)
        for tool in tools:
            name = str(tool.get("name", ""))
            lowered = name.lower()
            if any(hint.lower() in lowered for hint in name_hints):
                return self.call_tool(server_name, name, arguments)
        return MCPToolCallResult(
            server_name=server_name,
            tool_name="",
            success=False,
            message=f"No matching MCP tool found for hints: {', '.join(name_hints)}",
        )

    def call_capability_tool(
        self,
        capability: str,
        usage_scope: str | None,
        name_hints: list[str],
        arguments: dict[str, Any],
    ) -> MCPToolCallResult:
        entry = self.find_server_by_capability(capability, usage_scope)
        if not entry:
            return MCPToolCallResult(
                server_name="",
                tool_name="",
                success=False,
                message=f"No MCP server registered for capability '{capability}'.",
            )
        return self.call_tool_by_match(entry.name, name_hints, arguments)

    def _run_bridge(self, server_name: str, request: dict[str, Any]) -> dict[str, Any]:
        entry = self.tool_manager.get_entry(server_name)
        if not entry:
            raise RuntimeError(f"MCP server '{server_name}' is not registered.")
        self._ensure_bridge_ready()

        payload = {
            **request,
            "server": self._entry_to_bridge_server(entry),
        }
        serialized = json.dumps(payload, ensure_ascii=False)
        timeout_seconds = max(self.default_timeout_seconds + 5, int(payload.get("timeout_ms", 0) / 1000) + 5)
        completed = subprocess.run(
            [self.node_executable, str(self.bridge_script)],
            input=serialized,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(self.bridge_dir),
            timeout=timeout_seconds,
        )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if not stdout:
            detail = stderr or "No output returned from MCP bridge."
            raise RuntimeError(detail)

        try:
            response = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid response from MCP bridge: {stdout[:300]}") from exc

        if completed.returncode != 0 or not response.get("success", False):
            detail = response.get("message") or stderr or "MCP bridge request failed."
            extra = response.get("details")
            if isinstance(extra, dict):
                stderr_detail = str(extra.get("stderr", "")).strip()
                if stderr_detail:
                    detail = f"{detail} | stderr: {stderr_detail}"
            raise RuntimeError(detail)
        return response

    def _entry_to_bridge_server(self, entry: ToolConfigEntry) -> dict[str, Any]:
        if entry.transport == "http":
            return {
                "transport": "http",
                "url": entry.url,
            }
        return {
            "transport": "stdio",
            "command": entry.command,
            "args": entry.args,
            "env": entry.env,
        }

    def _ensure_bridge_ready(self) -> None:
        if not self.bridge_script.exists():
            raise RuntimeError(f"MCP bridge script is missing: {self.bridge_script}")

        node_modules = self.bridge_dir / "node_modules" / "@modelcontextprotocol" / "sdk"
        if node_modules.exists():
            return

        npm_executable = shutil.which("npm") or "npm"
        completed = subprocess.run(
            [npm_executable, "install"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(self.bridge_dir),
            timeout=120,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "npm install failed").strip()
            raise RuntimeError(f"Failed to prepare MCP bridge dependencies: {detail}")

    def _extract_content(self, payload: dict[str, Any]) -> str:
        content = payload.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        parts.append(str(item.get("text", "")))
                    else:
                        parts.append(json.dumps(item, ensure_ascii=False))
                else:
                    parts.append(str(item))
            return "\n".join(part for part in parts if part.strip())
        if isinstance(payload, dict):
            return json.dumps(payload, ensure_ascii=False, indent=2)
        return str(payload)
