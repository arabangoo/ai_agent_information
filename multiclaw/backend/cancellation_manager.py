from __future__ import annotations

import asyncio
from typing import Dict


class CancellationManager:
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._cancelled_sessions: set[str] = set()

    def register(self, session_id: str, task: asyncio.Task | None) -> None:
        if task is not None:
            self._tasks[session_id] = task
        self._cancelled_sessions.discard(session_id)

    def clear(self, session_id: str) -> None:
        self._tasks.pop(session_id, None)
        self._cancelled_sessions.discard(session_id)

    def cancel(self, session_id: str) -> bool:
        self._cancelled_sessions.add(session_id)
        task = self._tasks.get(session_id)
        if task is None:
            return False
        task.cancel()
        return True

    def raise_if_cancelled(self, session_id: str) -> None:
        if session_id in self._cancelled_sessions:
            raise asyncio.CancelledError(f"session cancelled: {session_id}")
