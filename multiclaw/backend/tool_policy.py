from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from runtime_config import RuntimeConfig


@dataclass(frozen=True)
class ToolPolicyDecision:
    allowed: bool
    reason: str
    normalized_params: Dict[str, Any]


class ToolPolicy:
    def __init__(self, runtime_config: RuntimeConfig):
        self.runtime_config = runtime_config

    def assess(self, tool_name: str, params: Optional[Dict[str, Any]]) -> ToolPolicyDecision:
        normalized_params = dict(params or {})
        if tool_name in {"read_file", "write_file", "list_files"}:
            path_value = normalized_params.get("path", "")
            if not path_value:
                return ToolPolicyDecision(False, "path is required", normalized_params)
            resolved = self._resolve_local_path(path_value)
            normalized_params["path"] = str(resolved)
            return ToolPolicyDecision(True, "local path allowed", normalized_params)

        if tool_name == "run_command":
            command = str(normalized_params.get("command", "")).strip()
            if not command:
                return ToolPolicyDecision(False, "command is required", normalized_params)
            blocked = self._blocked_command_reason(command)
            if blocked:
                return ToolPolicyDecision(False, blocked, normalized_params)
            if normalized_params.get("cwd"):
                normalized_params["cwd"] = str(
                    self._resolve_local_path(str(normalized_params["cwd"]))
                )
            return ToolPolicyDecision(True, "command allowed", normalized_params)

        return ToolPolicyDecision(True, "tool allowed", normalized_params)

    def _resolve_local_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = (self.runtime_config.workspace_root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return candidate

    def _blocked_command_reason(self, command: str) -> Optional[str]:
        lowered = command.lower().strip()
        for blocked in self.runtime_config.blocked_commands:
            if blocked.lower() in lowered:
                return f"blocked command pattern detected: {blocked}"
        return None
