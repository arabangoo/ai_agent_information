from __future__ import annotations

import json
import shutil
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from runtime_config import get_runtime_config
from tool_manager_models import (
    ToolCheckRequest,
    ToolCheckResponse,
    ToolConfigEntry,
    ToolDeleteResponse,
    ToolManagerConfigResponse,
    ToolRegistrationRequest,
)


class ToolManagerService:
    def __init__(self) -> None:
        config = get_runtime_config()
        self.config_path = config.workspace_root / "tool_manager_config.json"

    def get_config(self) -> ToolManagerConfigResponse:
        config = self._load_config()
        return ToolManagerConfigResponse(
            config_path=str(self.config_path),
            entries=self._entries_from_config(config),
            raw_json=json.dumps(config, indent=2, ensure_ascii=False),
        )

    def list_entries(self) -> list[ToolConfigEntry]:
        return self.get_config().entries

    def get_entry(self, name: str) -> ToolConfigEntry | None:
        lowered = name.strip().lower()
        for entry in self.list_entries():
            if entry.name.lower() == lowered:
                return entry
        return None

    def get_entries_by_capability(
        self,
        capability: str,
        usage_scope: str | None = None,
    ) -> list[ToolConfigEntry]:
        matched: list[ToolConfigEntry] = []
        for entry in self.list_entries():
            if capability not in entry.capabilities:
                continue
            if usage_scope and entry.usage_scopes and usage_scope not in entry.usage_scopes:
                continue
            matched.append(entry)
        return matched

    def register(self, request: ToolRegistrationRequest) -> ToolManagerConfigResponse:
        normalized = self._normalize_request(request)
        config = self._load_config()
        servers = config.setdefault("mcpServers", {})
        servers[normalized.name] = self._entry_to_server_config(normalized)
        self._write_config(config)
        return self.get_config()

    def delete(self, name: str) -> ToolDeleteResponse:
        config = self._load_config()
        servers = config.setdefault("mcpServers", {})
        if name not in servers:
            return ToolDeleteResponse(deleted=False, name=name, message="Tool entry was not found.")
        del servers[name]
        self._write_config(config)
        return ToolDeleteResponse(deleted=True, name=name, message="Tool entry deleted.")

    def check(self, request: ToolCheckRequest) -> ToolCheckResponse:
        try:
            normalized = self._normalize_request(request)
        except ValueError as exc:
            return ToolCheckResponse(valid=False, summary=str(exc), checks=[])

        checks: list[str] = []
        valid = True

        if normalized.github_url:
            reachable = self._check_url(normalized.github_url)
            checks.append("GitHub URL reachable." if reachable else "GitHub URL could not be reached.")
            valid = valid and reachable

        if normalized.transport == "stdio":
            if not normalized.command:
                checks.append("Command is required for stdio tools.")
                valid = False
            else:
                command_available = self._command_available(normalized.command)
                checks.append("Command available on this machine." if command_available else "Command was not found on PATH.")
                valid = valid and command_available
        else:
            if not normalized.url:
                checks.append("URL is required for http tools.")
                valid = False
            else:
                url_reachable = self._check_url(normalized.url)
                checks.append("HTTP endpoint reachable." if url_reachable else "HTTP endpoint could not be reached.")
                valid = valid and url_reachable

        summary = "Tool configuration is valid." if valid else "Tool configuration needs attention."
        return ToolCheckResponse(valid=valid, summary=summary, checks=checks, normalized_entry=normalized)

    def _normalize_request(self, request: ToolRegistrationRequest | ToolCheckRequest) -> ToolConfigEntry:
        if request.raw_json.strip():
            return self._entry_from_raw_json(request.raw_json.strip())

        env = {item.key.strip(): item.value for item in request.env if item.key.strip()}
        name = request.name.strip()
        if not name:
            raise ValueError("Tool name is required.")

        if request.transport == "stdio":
            return ToolConfigEntry(
                name=name,
                github_url=request.github_url.strip(),
                description=request.description.strip(),
                transport="stdio",
                command=request.command.strip(),
                args=[item for item in request.args if item.strip()],
                env=env,
                capabilities=list(request.capabilities),
                usage_scopes=list(request.usage_scopes),
                source="form",
            )

        return ToolConfigEntry(
            name=name,
            github_url=request.github_url.strip(),
            description=request.description.strip(),
            transport="http",
            url=request.url.strip(),
            env=env,
            capabilities=list(request.capabilities),
            usage_scopes=list(request.usage_scopes),
            source="form",
        )

    def _entry_from_raw_json(self, raw_json: str) -> ToolConfigEntry:
        payload = self._parse_raw_json(raw_json)

        if "mcpServers" in payload:
            servers = payload.get("mcpServers", {})
            if len(servers) != 1:
                raise ValueError("Raw JSON must contain exactly one MCP server entry.")
            name, server = next(iter(servers.items()))
        elif len(payload) == 1 and all(isinstance(value, dict) for value in payload.values()):
            name, server = next(iter(payload.items()))
        else:
            if "name" not in payload:
                raise ValueError("Raw JSON must include a tool name or a single mcpServers entry.")
            name = str(payload["name"])
            server = payload

        transport = "http" if server.get("url") else "stdio"
        metadata = server.get("ai_iac_metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        return ToolConfigEntry(
            name=name,
            github_url=str(server.get("github_url", "")),
            description=str(server.get("description", "")),
            transport=transport,
            command=str(server.get("command", "")),
            args=[str(item) for item in server.get("args", [])],
            env={str(key): str(value) for key, value in server.get("env", {}).items()},
            url=str(server.get("url", "")),
            capabilities=[str(item) for item in metadata.get("capabilities", []) if str(item)],
            usage_scopes=[str(item) for item in metadata.get("usage_scopes", []) if str(item)],
            source="json",
        )

    def _parse_raw_json(self, raw_json: str) -> dict[str, object]:
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            wrapped = "{\n" + raw_json + "\n}"
            try:
                parsed = json.loads(wrapped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON: {exc.msg}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Raw JSON must be an object.")
        return parsed

    def _entry_to_server_config(self, entry: ToolConfigEntry) -> dict[str, object]:
        server: dict[str, object] = {}
        if entry.transport == "stdio":
            server["command"] = entry.command
            if entry.args:
                server["args"] = entry.args
        else:
            server["url"] = entry.url
        if entry.env:
            server["env"] = entry.env
        if entry.github_url:
            server["github_url"] = entry.github_url
        if entry.description:
            server["description"] = entry.description
        if entry.capabilities or entry.usage_scopes:
            server["ai_iac_metadata"] = {
                "capabilities": entry.capabilities,
                "usage_scopes": entry.usage_scopes,
            }
        return server

    def _entries_from_config(self, config: dict[str, object]) -> list[ToolConfigEntry]:
        entries: list[ToolConfigEntry] = []
        servers = config.get("mcpServers", {})
        if not isinstance(servers, dict):
            return entries

        for name, raw_server in servers.items():
            if not isinstance(raw_server, dict):
                continue
            transport = "http" if raw_server.get("url") else "stdio"
            entries.append(
                ToolConfigEntry(
                    name=str(name),
                    github_url=str(raw_server.get("github_url", "")),
                    description=str(raw_server.get("description", "")),
                    transport=transport,
                    command=str(raw_server.get("command", "")),
                    args=[str(item) for item in raw_server.get("args", [])] if isinstance(raw_server.get("args"), list) else [],
                    env={str(key): str(value) for key, value in raw_server.get("env", {}).items()} if isinstance(raw_server.get("env"), dict) else {},
                    url=str(raw_server.get("url", "")),
                    capabilities=[str(item) for item in dict(raw_server.get("ai_iac_metadata", {})).get("capabilities", []) if str(item)] if isinstance(raw_server.get("ai_iac_metadata"), dict) else [],
                    usage_scopes=[str(item) for item in dict(raw_server.get("ai_iac_metadata", {})).get("usage_scopes", []) if str(item)] if isinstance(raw_server.get("ai_iac_metadata"), dict) else [],
                    source="json",
                )
            )
        return sorted(entries, key=lambda item: item.name.lower())

    def _load_config(self) -> dict[str, object]:
        if not self.config_path.exists():
            config: dict[str, object] = {"mcpServers": {}}
            self._write_config(config)
            return config
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def _write_config(self, config: dict[str, object]) -> None:
        self.config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def _command_available(self, command: str) -> bool:
        if Path(command).exists():
            return True
        return shutil.which(command) is not None

    def _check_url(self, value: str) -> bool:
        try:
            request = Request(value, headers={"User-Agent": "MultiClaw/0.1"})
            with urlopen(request, timeout=5) as response:
                return 200 <= getattr(response, "status", 200) < 400
        except (URLError, ValueError):
            return False
