from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from contextlib import suppress
from typing import Any

from runtime_config import get_runtime_config
from tool_manager_models import MCPToolCallResult, ToolConfigEntry
from tool_manager_service import ToolManagerService

PARALLEL_SEARCH_URL = "https://search.parallel.ai/mcp"


class MCPRuntimeService:
    def __init__(self) -> None:
        self.tool_manager = ToolManagerService()
        self.default_timeout_seconds = 15
        self.node_executable = shutil.which("node") or "node"
        config = get_runtime_config()
        self.parallel_search_enabled = config.parallel_search_enabled
        self.bridge_dir = config.backend_root / "mcp_bridge"
        self.bridge_script = self.bridge_dir / "mcp_bridge.mjs"

    def available_servers(self) -> list[ToolConfigEntry]:
        entries = self.tool_manager.list_entries()
        # A saved entry wins even when incomplete: never replace an explicit choice.
        if self.parallel_search_enabled and not any(entry.name.lower() == "parallel" for entry in entries):
            entries.append(ToolConfigEntry(
                name="parallel",
                description="Parallel Search MCP: free web search and page fetching without a Parallel API key.",
                transport="http",
                url=PARALLEL_SEARCH_URL,
                capabilities=["reference"],
                usage_scopes=["prompt"],
            ))
        return [
            entry
            for entry in entries
            if (entry.transport == "stdio" and entry.command) or (entry.transport == "http" and entry.url)
        ]

    def has_server(self, name: str) -> bool:
        return self._get_server(name) is not None

    def _get_server(self, name: str) -> ToolConfigEntry | None:
        saved = self.tool_manager.get_entry(name)
        if saved is not None:
            return saved
        return next((entry for entry in self.available_servers() if entry.name.lower() == name.lower()), None)

    def find_server_by_capability(self, capability: str, usage_scope: str | None = None) -> ToolConfigEntry | None:
        matches = [entry for entry in self.available_servers()
                   if capability in entry.capabilities
                   and (not usage_scope or not entry.usage_scopes or usage_scope in entry.usage_scopes)]
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
            return self._tool_result(server_name, tool_name, payload)
        except Exception as exc:
            return MCPToolCallResult(
                server_name=server_name,
                tool_name=tool_name,
                success=False,
                message=str(exc),
            )

    def _tool_result(self, server_name: str, tool_name: str, payload: dict[str, Any]) -> MCPToolCallResult:
        result = payload.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("MCP bridge returned an invalid tool result.")
        content = self._extract_content(result)
        failed = bool(result.get("isError", False))
        return MCPToolCallResult(
            server_name=server_name,
            tool_name=tool_name,
            success=not failed,
            content=content,
            raw_payload=result,
            message=(content or "MCP tool returned an error.") if failed else "MCP tool call completed.",
        )

    async def call_tool_async(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> MCPToolCallResult:
        """Call HTTP tools without leaving a bridge running after cancellation."""
        try:
            entry = self._get_server(server_name)
            if entry is not None and entry.transport == "stdio":
                # Preserve the existing stdio lifecycle, which may include child processes.
                return await asyncio.to_thread(self.call_tool, server_name, tool_name, arguments)
            payload = await self._run_bridge_async(server_name, {
                "action": "call_tool", "tool_name": tool_name, "arguments": arguments,
                "timeout_ms": self.default_timeout_seconds * 1000,
            })
            return self._tool_result(server_name, tool_name, payload)
        except Exception as exc:
            return MCPToolCallResult(server_name=server_name, tool_name=tool_name, success=False, message=str(exc))

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
        entry = self._get_server(server_name)
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

        return self._decode_bridge_response(completed.returncode, completed.stdout, completed.stderr)

    async def _run_bridge_async(self, server_name: str, request: dict[str, Any]) -> dict[str, Any]:
        entry = self._get_server(server_name)
        if entry is None:
            raise RuntimeError(f"MCP server '{server_name}' is not registered.")
        # Discovery prepares the SDK before registering tools. Do not run npm on the event loop.
        if not self.bridge_script.is_file() or not (self.bridge_dir / "node_modules" / "@modelcontextprotocol" / "sdk").is_dir():
            raise RuntimeError("MCP bridge is not ready. Refresh MCP tools before calling them.")
        payload = {**request, "server": self._entry_to_bridge_server(entry)}
        process = await asyncio.create_subprocess_exec(
            self.node_executable, str(self.bridge_script),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(self.bridge_dir),
        )
        timeout_seconds = max(self.default_timeout_seconds + 5, float(payload.get("timeout_ms", 0)) / 1000 + 5)
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(json.dumps(payload, ensure_ascii=False).encode("utf-8")), timeout_seconds,
            )
        except (asyncio.CancelledError, asyncio.TimeoutError) as exc:
            if process.returncode is None:
                with suppress(ProcessLookupError):
                    process.kill()
            await process.communicate()
            if isinstance(exc, asyncio.TimeoutError):
                raise RuntimeError("MCP bridge call timed out.") from exc
            raise
        return self._decode_bridge_response(process.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace"))

    def _decode_bridge_response(self, returncode: int, stdout: str, stderr: str) -> dict[str, Any]:
        stdout = stdout.strip()
        stderr = stderr.strip()
        if not stdout:
            detail = stderr or "No output returned from MCP bridge."
            raise RuntimeError(detail)

        try:
            response = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid response from MCP bridge: {stdout[:300]}") from exc

        if not isinstance(response, dict):
            raise RuntimeError("MCP bridge response must be an object.")
        if returncode != 0 or not response.get("success", False):
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
