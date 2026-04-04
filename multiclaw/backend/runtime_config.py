from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_BLOCKED_COMMANDS = (
    "rm -rf /",
    "rm -rf /*",
    "rmdir /s /q c:",
    "format c:",
    "del /f /s /q c:",
    "mkfs",
    ":(){:|:&};:",
    "dd if=",
    "chmod -R 777 /",
    "shutdown",
    "reboot",
    "halt",
    "passwd",
    "useradd",
    "userdel",
    "groupdel",
    "> /dev/sda",
    "mv /* /dev/null",
    "wget | sh",
    "curl | sh",
    "reg delete",
    "net user",
    "net localgroup",
    "git reset --hard",
)


@dataclass(frozen=True)
class RuntimeConfig:
    workspace_root: Path
    backend_root: Path
    data_root: Path
    memory_root: Path
    default_session_id: str = "default"
    command_timeout_seconds: float = 30.0
    max_command_stdout_chars: int = 20_000
    max_command_stderr_chars: int = 5_000
    max_read_chars: int = 50_000
    max_upload_bytes: int = 100 * 1024 * 1024
    allowed_upload_extensions: tuple[str, ...] = (
        ".pdf",
        ".docx",
        ".txt",
        ".json",
        ".png",
        ".jpg",
        ".jpeg",
    )
    blocked_commands: tuple[str, ...] = field(default_factory=lambda: DEFAULT_BLOCKED_COMMANDS)

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        backend_root = Path(__file__).resolve().parent
        workspace_root = backend_root.parent
        data_root = Path(os.getenv("MULTICLAW_DATA_ROOT", backend_root / "data")).resolve()
        memory_root = Path(
            os.getenv("MULTICLAW_MEMORY_ROOT", data_root / "memory")
        ).resolve()
        default_session_id = os.getenv("MULTICLAW_DEFAULT_SESSION_ID", "default").strip() or "default"
        return cls(
            workspace_root=workspace_root,
            backend_root=backend_root,
            data_root=data_root,
            memory_root=memory_root,
            default_session_id=default_session_id,
        )


_CONFIG: RuntimeConfig | None = None


def get_runtime_config() -> RuntimeConfig:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = RuntimeConfig.from_env()
    return _CONFIG
