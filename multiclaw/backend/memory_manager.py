"""
Session-scoped memory manager for MultiClaw.

The public API stays close to the original version, but the underlying
storage is now isolated by session.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime_config import RuntimeConfig, get_runtime_config
from session_context import sanitize_session_id


DEFAULT_SUMMARY_HEADER = (
    "# MultiClaw Long-Term Memory\n\n"
    "Important notes and preferences are stored here.\n\n"
    "---\n\n"
)


class MemoryManager:
    def __init__(
        self,
        base_dir: str | None = None,
        runtime_config: RuntimeConfig | None = None,
    ):
        self.runtime_config = runtime_config or get_runtime_config()
        if base_dir is None:
            self.base_dir = self.runtime_config.memory_root
        else:
            self.base_dir = Path(base_dir).resolve()
        self.sessions_dir = self.base_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.metadata = self.get_session_metadata()
        print("MemoryManager initialized")

    def _resolve_session_id(self, session_id: Optional[str] = None) -> str:
        return sanitize_session_id(session_id, self.runtime_config.default_session_id)

    def _session_dir(self, session_id: Optional[str] = None) -> Path:
        session_dir = self.sessions_dir / self._resolve_session_id(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def _daily_dir(self, session_id: Optional[str] = None) -> Path:
        daily_dir = self._session_dir(session_id) / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)
        return daily_dir

    def _memory_file(self, session_id: Optional[str] = None) -> Path:
        memory_file = self._session_dir(session_id) / "MEMORY.md"
        if not memory_file.exists():
            memory_file.write_text(DEFAULT_SUMMARY_HEADER, encoding="utf-8")
        return memory_file

    def _metadata_file(self, session_id: Optional[str] = None) -> Path:
        return self._session_dir(session_id) / "metadata.json"

    def _load_metadata(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        metadata_file = self._metadata_file(session_id)
        if metadata_file.exists():
            try:
                return json.loads(metadata_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"total_entries": 0, "last_updated": None, "categories": {}}

    def _save_metadata(self, metadata: Dict[str, Any], session_id: Optional[str] = None) -> None:
        metadata["last_updated"] = datetime.now().isoformat()
        self._metadata_file(session_id).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if self._resolve_session_id(session_id) == self.runtime_config.default_session_id:
            self.metadata = metadata

    def get_session_metadata(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        return self._load_metadata(session_id)

    def save_memory(
        self,
        content: str,
        category: str = "general",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        timestamp = datetime.now()
        daily_file = self._daily_dir(session_id) / f"{timestamp.strftime('%Y-%m-%d')}.md"
        entry = f"\n## [{timestamp.strftime('%H:%M:%S')}] [{category}]\n{content}\n"

        if daily_file.exists():
            daily_file.write_text(
                daily_file.read_text(encoding="utf-8") + entry,
                encoding="utf-8",
            )
        else:
            header = f"# Daily Log - {timestamp.strftime('%Y-%m-%d')}\n"
            daily_file.write_text(header + entry, encoding="utf-8")

        metadata = self._load_metadata(session_id)
        metadata["total_entries"] = metadata.get("total_entries", 0) + 1
        categories = metadata.get("categories", {})
        categories[category] = categories.get(category, 0) + 1
        metadata["categories"] = categories
        self._save_metadata(metadata, session_id)

        return {
            "success": True,
            "message": "memory saved",
            "session_id": self._resolve_session_id(session_id),
            "date": timestamp.strftime("%Y-%m-%d"),
            "category": category,
        }

    def update_summary(self, summary: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        memory_file = self._memory_file(session_id)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        updated = memory_file.read_text(encoding="utf-8") + f"\n### [{timestamp}] Update\n{summary}\n"
        lines = updated.splitlines()
        if len(lines) > 200:
            updated = "\n".join(lines[:200]) + "\n\n> (Older lines were truncated.)\n"
        memory_file.write_text(updated, encoding="utf-8")
        metadata = self._load_metadata(session_id)
        self._save_metadata(metadata, session_id)
        return {"success": True, "message": "summary updated"}

    def search_memory(
        self,
        query: str,
        max_results: int = 10,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        results = []
        keywords = query.lower().split()
        memory_file = self._memory_file(session_id)
        if memory_file.exists():
            content = memory_file.read_text(encoding="utf-8")
            if any(keyword in content.lower() for keyword in keywords):
                results.append(
                    {
                        "source": "MEMORY.md",
                        "type": "summary",
                        "content": content[:2000],
                        "relevance": "high",
                    }
                )

        daily_files = sorted(self._daily_dir(session_id).glob("*.md"), reverse=True)[:30]
        for daily_file in daily_files:
            try:
                content = daily_file.read_text(encoding="utf-8")
            except Exception:
                continue
            if any(keyword in content.lower() for keyword in keywords):
                sections = content.split("\n## ")
                matching_sections = [
                    section[:500]
                    for section in sections
                    if any(keyword in section.lower() for keyword in keywords)
                ]
                if matching_sections:
                    results.append(
                        {
                            "source": daily_file.name,
                            "type": "daily_log",
                            "content": "\n---\n".join(matching_sections[:3]),
                            "relevance": "medium",
                        }
                    )
            if len(results) >= max_results:
                break

        return {
            "success": True,
            "query": query,
            "session_id": self._resolve_session_id(session_id),
            "results": results[:max_results],
            "count": len(results[:max_results]),
        }

    def get_daily_log(
        self,
        target_date: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if target_date is None:
            target_date = date.today().isoformat()
        daily_file = self._daily_dir(session_id) / f"{target_date}.md"
        if not daily_file.exists():
            return {
                "success": True,
                "session_id": self._resolve_session_id(session_id),
                "date": target_date,
                "content": "No log for this date.",
                "exists": False,
            }
        return {
            "success": True,
            "session_id": self._resolve_session_id(session_id),
            "date": target_date,
            "content": daily_file.read_text(encoding="utf-8"),
            "exists": True,
        }

    def get_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "success": True,
            "session_id": self._resolve_session_id(session_id),
            "content": self._memory_file(session_id).read_text(encoding="utf-8"),
            "metadata": self._load_metadata(session_id),
        }

    def get_context_for_chat(self, session_id: Optional[str] = None) -> str:
        parts: List[str] = []
        summary = self._memory_file(session_id).read_text(encoding="utf-8")
        if len(summary.strip()) > 50:
            parts.append(f"<long_term_memory>\n{summary[:1500]}\n</long_term_memory>")

        today_file = self._daily_dir(session_id) / f"{date.today().isoformat()}.md"
        if today_file.exists():
            today_log = today_file.read_text(encoding="utf-8")
            if len(today_log.strip()) > 50:
                parts.append(f"<today_log>\n{today_log[:1000]}\n</today_log>")
        return "\n\n".join(parts)

    def clear_all(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        target_session_id = self._resolve_session_id(session_id)
        session_dir = self._session_dir(target_session_id)
        for path in sorted(session_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
        self._memory_file(target_session_id)
        self._save_metadata({"total_entries": 0, "last_updated": None, "categories": {}}, target_session_id)
        return {
            "success": True,
            "message": "memory cleared",
            "session_id": target_session_id,
        }

    def get_global_stats(self) -> Dict[str, Any]:
        total_entries = 0
        session_count = 0
        for session_dir in self.sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue
            session_count += 1
            metadata = self._load_metadata(session_dir.name)
            total_entries += metadata.get("total_entries", 0)
        return {
            "session_count": session_count,
            "total_entries": total_entries,
        }
