from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from runtime_config import RuntimeConfig


def sanitize_session_id(raw_session_id: Optional[str], default_session_id: str) -> str:
    candidate = (raw_session_id or "").strip()
    if not candidate:
        return default_session_id
    sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "-", candidate).strip("-._")
    return sanitized or default_session_id


@dataclass(frozen=True)
class SessionContext:
    session_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionStore:
    def __init__(self, runtime_config: RuntimeConfig):
        self.runtime_config = runtime_config
        self._histories: Dict[str, List[Dict[str, Any]]] = {}

    def get_context(self, session_id: Optional[str] = None, **metadata: Any) -> SessionContext:
        resolved_session_id = sanitize_session_id(
            session_id, self.runtime_config.default_session_id
        )
        return SessionContext(session_id=resolved_session_id, metadata=metadata)

    def get_history(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        resolved_session_id = sanitize_session_id(
            session_id, self.runtime_config.default_session_id
        )
        return list(self._histories.get(resolved_session_id, []))

    def append_message(self, session_id: Optional[str], entry: Dict[str, Any]) -> None:
        resolved_session_id = sanitize_session_id(
            session_id, self.runtime_config.default_session_id
        )
        self._histories.setdefault(resolved_session_id, []).append(entry)

    def clear_history(self, session_id: Optional[str] = None) -> None:
        if session_id is None:
            self._histories.clear()
            return
        resolved_session_id = sanitize_session_id(
            session_id, self.runtime_config.default_session_id
        )
        self._histories.pop(resolved_session_id, None)

    def stats(self) -> Dict[str, Any]:
        return {
            "session_count": len(self._histories),
            "message_count": sum(len(messages) for messages in self._histories.values()),
        }
