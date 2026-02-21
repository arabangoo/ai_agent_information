"""
MultiClaw Memory Manager - 로컬 장기 메모리 시스템
OpenClaw 스타일의 로컬 파일 기반 장기 메모리
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional


class MemoryManager:
    """로컬 장기 메모리 관리자"""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), "data", "memory")

        self.base_dir = Path(base_dir)
        self.daily_dir = self.base_dir / "daily"
        self.memory_file = self.base_dir / "MEMORY.md"
        self.metadata_file = self.base_dir / "metadata.json"

        # 디렉토리 생성
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.daily_dir.mkdir(parents=True, exist_ok=True)

        # MEMORY.md 초기화
        if not self.memory_file.exists():
            self.memory_file.write_text(
                "# MultiClaw 장기 메모리\n\n"
                "이 파일은 중요한 대화 내용과 사용자 선호도를 기록합니다.\n\n"
                "---\n\n",
                encoding="utf-8",
            )

        # 메타데이터 로드
        self.metadata = self._load_metadata()
        print("✅ MemoryManager 초기화 완료")

    def _load_metadata(self) -> Dict[str, Any]:
        if self.metadata_file.exists():
            try:
                return json.loads(self.metadata_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"total_entries": 0, "last_updated": None, "categories": {}}

    def _save_metadata(self):
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata_file.write_text(
            json.dumps(self.metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save_memory(self, content: str, category: str = "general") -> Dict[str, Any]:
        """메모리 항목 저장"""
        timestamp = datetime.now()

        # 일별 로그에 저장
        daily_file = self.daily_dir / f"{timestamp.strftime('%Y-%m-%d')}.md"

        entry = f"\n## [{timestamp.strftime('%H:%M:%S')}] [{category}]\n{content}\n"

        if daily_file.exists():
            existing = daily_file.read_text(encoding="utf-8")
            daily_file.write_text(existing + entry, encoding="utf-8")
        else:
            header = f"# 대화 로그 - {timestamp.strftime('%Y년 %m월 %d일')}\n"
            daily_file.write_text(header + entry, encoding="utf-8")

        # 메타데이터 업데이트
        self.metadata["total_entries"] = self.metadata.get("total_entries", 0) + 1
        cat_count = self.metadata.get("categories", {})
        cat_count[category] = cat_count.get(category, 0) + 1
        self.metadata["categories"] = cat_count
        self._save_metadata()

        return {
            "success": True,
            "message": "메모리 저장 완료",
            "date": timestamp.strftime("%Y-%m-%d"),
            "category": category,
        }

    def update_summary(self, summary: str) -> Dict[str, Any]:
        """MEMORY.md 핵심 요약 업데이트"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        current = self.memory_file.read_text(encoding="utf-8")

        # 기존 내용에 새 요약 추가
        new_entry = f"\n### [{timestamp}] 업데이트\n{summary}\n"
        updated = current + new_entry

        # 200줄 제한 (OpenClaw 스타일)
        lines = updated.split("\n")
        if len(lines) > 200:
            updated = "\n".join(lines[:200])
            updated += "\n\n> (200줄 제한으로 이전 내용은 일별 로그를 참조하세요)\n"

        self.memory_file.write_text(updated, encoding="utf-8")
        self._save_metadata()

        return {"success": True, "message": "장기 메모리 요약 업데이트 완료"}

    def search_memory(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """키워드 기반 메모리 검색"""
        results = []
        query_lower = query.lower()
        keywords = query_lower.split()

        # MEMORY.md 검색
        if self.memory_file.exists():
            content = self.memory_file.read_text(encoding="utf-8")
            if any(kw in content.lower() for kw in keywords):
                results.append({
                    "source": "MEMORY.md",
                    "type": "summary",
                    "content": content[:2000],
                    "relevance": "high",
                })

        # 일별 로그 검색 (최근 30일)
        daily_files = sorted(self.daily_dir.glob("*.md"), reverse=True)[:30]
        for daily_file in daily_files:
            try:
                content = daily_file.read_text(encoding="utf-8")
                if any(kw in content.lower() for kw in keywords):
                    # 관련 섹션 추출
                    sections = content.split("\n## ")
                    matching_sections = []
                    for section in sections:
                        if any(kw in section.lower() for kw in keywords):
                            matching_sections.append(section[:500])

                    if matching_sections:
                        results.append({
                            "source": daily_file.name,
                            "type": "daily_log",
                            "content": "\n---\n".join(matching_sections[:3]),
                            "relevance": "medium",
                        })
            except Exception:
                continue

            if len(results) >= max_results:
                break

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
        }

    def get_daily_log(self, target_date: str = None) -> Dict[str, Any]:
        """일별 로그 조회"""
        if target_date is None:
            target_date = date.today().isoformat()

        daily_file = self.daily_dir / f"{target_date}.md"

        if not daily_file.exists():
            return {
                "success": True,
                "date": target_date,
                "content": "해당 날짜의 로그가 없습니다.",
                "exists": False,
            }

        return {
            "success": True,
            "date": target_date,
            "content": daily_file.read_text(encoding="utf-8"),
            "exists": True,
        }

    def get_summary(self) -> Dict[str, Any]:
        """MEMORY.md 요약 반환"""
        content = ""
        if self.memory_file.exists():
            content = self.memory_file.read_text(encoding="utf-8")

        return {
            "success": True,
            "content": content,
            "metadata": self.metadata,
        }

    def get_context_for_chat(self) -> str:
        """채팅에 주입할 메모리 컨텍스트 생성"""
        parts = []

        # MEMORY.md에서 핵심 정보
        if self.memory_file.exists():
            summary = self.memory_file.read_text(encoding="utf-8")
            if len(summary.strip()) > 50:  # 의미 있는 내용이 있을 때만
                parts.append(f"<장기_메모리>\n{summary[:1500]}\n</장기_메모리>")

        # 오늘 대화 로그
        today_file = self.daily_dir / f"{date.today().isoformat()}.md"
        if today_file.exists():
            today_log = today_file.read_text(encoding="utf-8")
            if len(today_log.strip()) > 50:
                parts.append(f"<오늘_대화_기록>\n{today_log[:1000]}\n</오늘_대화_기록>")

        return "\n\n".join(parts) if parts else ""

    def clear_all(self) -> Dict[str, Any]:
        """모든 메모리 초기화"""
        # 일별 로그 삭제
        for f in self.daily_dir.glob("*.md"):
            f.unlink()

        # MEMORY.md 초기화
        self.memory_file.write_text(
            "# MultiClaw 장기 메모리\n\n"
            "이 파일은 중요한 대화 내용과 사용자 선호도를 기록합니다.\n\n"
            "---\n\n",
            encoding="utf-8",
        )

        # 메타데이터 초기화
        self.metadata = {"total_entries": 0, "last_updated": None, "categories": {}}
        self._save_metadata()

        return {"success": True, "message": "모든 메모리가 초기화되었습니다"}
