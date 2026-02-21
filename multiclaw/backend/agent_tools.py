"""
MultiClaw Agent Tools - 에이전트 도구 시스템
파일 조작, 명령 실행, 웹 검색 등 에이전트가 사용할 수 있는 도구들
"""

import os
import subprocess
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path


# 위험한 명령어 패턴 차단 목록
BLOCKED_COMMANDS = [
    "rm -rf /", "rm -rf /*", "rmdir /s /q c:", "format c:",
    "del /f /s /q c:", "mkfs", ":(){:|:&};:", "dd if=",
    "chmod -R 777 /", "shutdown", "reboot", "halt",
    "passwd", "useradd", "userdel", "groupdel",
    "> /dev/sda", "mv /* /dev/null", "wget | sh", "curl | sh",
    "reg delete", "net user", "net localgroup",
]

# 허용된 작업 디렉토리 (기본값 - 프로젝트 내부)
ALLOWED_BASE_DIR = Path(__file__).parent.parent.resolve()


class AgentTool:
    """에이전트 도구 기본 클래스"""
    name: str = ""
    description: str = ""

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class ReadFileTool(AgentTool):
    name = "read_file"
    description = "파일 내용을 읽습니다. 경로(path)를 지정하세요."

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = params.get("path", "")
        if not file_path:
            return {"success": False, "error": "경로가 지정되지 않았습니다"}

        resolved = Path(file_path).resolve()
        if not resolved.exists():
            return {"success": False, "error": f"파일을 찾을 수 없습니다: {file_path}"}

        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
            # 너무 긴 파일은 잘라서 반환
            if len(content) > 50000:
                content = content[:50000] + "\n\n... (파일이 너무 길어 50,000자까지만 표시)"
            return {
                "success": True,
                "path": str(resolved),
                "content": content,
                "size": resolved.stat().st_size,
            }
        except Exception as e:
            return {"success": False, "error": f"파일 읽기 실패: {str(e)}"}


class WriteFileTool(AgentTool):
    name = "write_file"
    description = "파일에 내용을 씁니다. 경로(path)와 내용(content)을 지정하세요."

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = params.get("path", "")
        content = params.get("content", "")

        if not file_path:
            return {"success": False, "error": "경로가 지정되지 않았습니다"}

        resolved = Path(file_path).resolve()

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "path": str(resolved),
                "size": len(content),
                "message": f"파일 작성 완료: {resolved.name}",
            }
        except Exception as e:
            return {"success": False, "error": f"파일 쓰기 실패: {str(e)}"}


class ListFilesTool(AgentTool):
    name = "list_files"
    description = "디렉토리의 파일 목록을 조회합니다. 경로(path)를 지정하세요."

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        dir_path = params.get("path", ".")

        resolved = Path(dir_path).resolve()
        if not resolved.is_dir():
            return {"success": False, "error": f"디렉토리를 찾을 수 없습니다: {dir_path}"}

        try:
            entries = []
            for item in sorted(resolved.iterdir()):
                entry = {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                }
                if item.is_file():
                    entry["size"] = item.stat().st_size
                entries.append(entry)

            return {
                "success": True,
                "path": str(resolved),
                "entries": entries,
                "count": len(entries),
            }
        except Exception as e:
            return {"success": False, "error": f"디렉토리 조회 실패: {str(e)}"}


class RunCommandTool(AgentTool):
    name = "run_command"
    description = "시스템 명령어를 실행합니다. 명령어(command)를 지정하세요."

    def _is_blocked(self, command: str) -> Optional[str]:
        """위험한 명령어 체크"""
        cmd_lower = command.lower().strip()
        for blocked in BLOCKED_COMMANDS:
            if blocked.lower() in cmd_lower:
                return f"차단된 명령어: {blocked}"
        return None

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        command = params.get("command", "")

        if not command:
            return {"success": False, "error": "명령어가 지정되지 않았습니다"}

        # 위험 명령어 차단
        blocked_reason = self._is_blocked(command)
        if blocked_reason:
            return {"success": False, "error": blocked_reason, "blocked": True}

        try:
            # 타임아웃 30초, 출력 크기 제한
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(ALLOWED_BASE_DIR),
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=30.0
            )

            stdout_text = stdout.decode("utf-8", errors="replace")[:20000]
            stderr_text = stderr.decode("utf-8", errors="replace")[:5000]

            return {
                "success": process.returncode == 0,
                "command": command,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "return_code": process.returncode,
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "명령어 실행 시간 초과 (30초)"}
        except Exception as e:
            return {"success": False, "error": f"명령어 실행 실패: {str(e)}"}


class WebSearchTool(AgentTool):
    name = "web_search"
    description = "Perplexity API로 웹 검색을 수행합니다. 검색어(query)를 지정하세요."

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query", "")

        if not query:
            return {"success": False, "error": "검색어가 지정되지 않았습니다"}

        import httpx

        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            return {"success": False, "error": "PERPLEXITY_API_KEY가 설정되지 않았습니다"}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "You are a precise research assistant."},
                {"role": "user", "content": query},
            ],
            "search_recency_filter": "month",
            "return_citations": True,
            "return_related_questions": True,
            "temperature": 0.2,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()

                return {
                    "success": True,
                    "content": result["choices"][0]["message"]["content"],
                    "citations": result.get("citations", []),
                    "related_questions": result.get("related_questions", []),
                }
        except Exception as e:
            return {"success": False, "error": f"웹 검색 실패: {str(e)}"}


# 사용 가능한 모든 도구 레지스트리
TOOL_REGISTRY: Dict[str, AgentTool] = {
    "read_file": ReadFileTool(),
    "write_file": WriteFileTool(),
    "list_files": ListFilesTool(),
    "run_command": RunCommandTool(),
    "web_search": WebSearchTool(),
}


def get_tools_description() -> str:
    """사용 가능한 도구 목록 설명 문자열"""
    lines = []
    for name, tool in TOOL_REGISTRY.items():
        lines.append(f"- {name}: {tool.description}")
    return "\n".join(lines)


async def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """도구 실행"""
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        return {"success": False, "error": f"알 수 없는 도구: {tool_name}"}
    return await tool.execute(params)
