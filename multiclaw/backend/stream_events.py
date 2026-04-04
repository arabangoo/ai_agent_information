from __future__ import annotations

import json
from typing import Any, Dict


def event_payload(
    event: str,
    provider: str | None = None,
    session_id: str | None = None,
    **data: Any,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "version": "v2",
        "event": event,
    }
    if provider is not None:
        payload["provider"] = provider
        payload["ai_name"] = provider
    if session_id is not None:
        payload["session_id"] = session_id
    payload.update(data)
    if "text" in data and event == "message_delta":
        payload["type"] = "chunk"
    elif event == "message_start":
        payload["type"] = "start"
    elif event == "message_end":
        payload["type"] = "done"
    elif event == "error":
        payload["type"] = "error"
    return payload


def sse_data(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
