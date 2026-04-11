"""
MultiClaw Agent Tools

Keeps the current built-in tools while exposing them through
an extensible registry that can later host plugins.
"""

from __future__ import annotations

import asyncio
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx

try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    async_playwright = None
    PLAYWRIGHT_AVAILABLE = False

try:
    from ddgs import DDGS

    DDGS_AVAILABLE = True
except ImportError:
    DDGS = None
    DDGS_AVAILABLE = False

try:
    import ssl

    SSL_ERRORS = (ssl.SSLError,)
except ImportError:
    SSL_ERRORS = ()

from runtime_config import get_runtime_config
from session_context import SessionContext
from tool_policy import ToolPolicy
from tool_registry import AgentToolRegistry, ToolExecutionContext


class AgentTool:
    name: str = ""
    description: str = ""
    source: str = "core"

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return []

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        raise NotImplementedError


class ReadFileTool(AgentTool):
    name = "read_file"
    description = "Reads a UTF-8 text file from the local filesystem. Absolute Windows paths are allowed."

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return [] if params.get("path") else ["path is required"]

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        resolved = Path(params["path"])
        if not resolved.exists():
            return {"success": False, "error": f"file not found: {resolved}"}

        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
            if len(content) > context.runtime_config.max_read_chars:
                content = (
                    content[: context.runtime_config.max_read_chars]
                    + "\n\n... (truncated)"
                )
            return {
                "success": True,
                "path": str(resolved),
                "content": content,
                "size": resolved.stat().st_size,
            }
        except Exception as exc:
            return {"success": False, "error": f"failed to read file: {exc}"}


class WriteFileTool(AgentTool):
    name = "write_file"
    description = "Creates or updates a text file on the local filesystem. Absolute Windows paths are allowed."

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        errors = []
        if not params.get("path"):
            errors.append("path is required")
        if "content" not in params:
            errors.append("content is required")
        return errors

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        resolved = Path(params["path"])
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(str(params.get("content", "")), encoding="utf-8")
            return {
                "success": True,
                "path": str(resolved),
                "size": len(str(params.get("content", ""))),
                "message": f"file written: {resolved.name}",
            }
        except Exception as exc:
            return {"success": False, "error": f"failed to write file: {exc}"}


class ListFilesTool(AgentTool):
    name = "list_files"
    description = "Lists files and folders in a local directory. Absolute Windows paths are allowed."

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return [] if params.get("path") else ["path is required"]

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        resolved = Path(params["path"])
        if not resolved.is_dir():
            return {"success": False, "error": f"directory not found: {resolved}"}

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
        except Exception as exc:
            return {"success": False, "error": f"failed to list directory: {exc}"}


class RunCommandTool(AgentTool):
    name = "run_command"
    description = "Runs a local shell command. Dangerous commands are still blocked automatically."

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return [] if params.get("command") else ["command is required"]

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        command = str(params["command"]).strip()
        decision = context.tool_policy.assess(self.name, {"command": command})
        if not decision.allowed:
            return {
                "success": False,
                "error": decision.reason,
                "blocked": True,
            }

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(params.get("cwd") or context.runtime_config.workspace_root),
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=context.runtime_config.command_timeout_seconds,
            )
            return {
                "success": process.returncode == 0,
                "command": command,
                "stdout": stdout.decode("utf-8", errors="replace")[
                    : context.runtime_config.max_command_stdout_chars
                ],
                "stderr": stderr.decode("utf-8", errors="replace")[
                    : context.runtime_config.max_command_stderr_chars
                ],
                "return_code": process.returncode,
            }
        except asyncio.CancelledError:
            if "process" in locals() and process.returncode is None:
                process.kill()
                await process.communicate()
            raise
        except asyncio.TimeoutError:
            return {"success": False, "error": "command timed out"}
        except Exception as exc:
            return {"success": False, "error": f"command failed: {exc}"}


class WebSearchTool(AgentTool):
    name = "web_search"
    description = (
        "Searches the web from Python without requiring a Perplexity API key. "
        "Returns live search results that the three AIs can synthesize."
    )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return [] if params.get("query") else ["query is required"]

    async def _search_web(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        if not DDGS_AVAILABLE:
            raise RuntimeError("ddgs is not installed")

        def run_search() -> List[Dict[str, Any]]:
            with DDGS() as ddgs:
                raw_results = ddgs.text(query, region="kr-kr", max_results=max_results)

            normalized_results: List[Dict[str, Any]] = []
            for item in raw_results:
                normalized_results.append(
                    {
                        "title": item.get("title", "").strip(),
                        "url": item.get("href", "").strip(),
                        "snippet": item.get("body", "").strip(),
                        "source": item.get("source", "web"),
                    }
                )
            return [item for item in normalized_results if item["title"] and item["url"]]

        return await asyncio.to_thread(run_search)

    async def _fetch_preview(self, url: str) -> Dict[str, Any]:
        async def request_page(verify: bool) -> httpx.Response:
            async with httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True,
                verify=verify,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    )
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response

        try:
            response = await request_page(verify=True)
        except (httpx.ConnectError,) + SSL_ERRORS:
            response = await request_page(verify=False)
            insecure_tls = True
        except Exception as exc:
            return {
                "success": False,
                "error": f"preview fetch failed: {exc}",
            }

        try:
            text = response.text.replace("\r", " ").replace("\n", " ")
            text = " ".join(text.split())
            payload = {
                "success": True,
                "status_code": response.status_code,
                "preview_text": text[:1200],
            }
            if "insecure_tls" in locals():
                payload["insecure_tls"] = insecure_tls
            return payload
        except Exception as exc:
            return {
                "success": False,
                "error": f"preview fetch failed: {exc}",
            }

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        try:
            query = str(params["query"]).strip()
            max_results = int(params.get("max_results", 5))
            max_results = max(1, min(max_results, 10))

            results = await self._search_web(query, max_results=max_results)
            if not results:
                return {
                    "success": False,
                    "error": "no live web search results were found",
                }

            preview_tasks = [
                self._fetch_preview(item["url"]) for item in results[: min(3, len(results))]
            ]
            previews = await asyncio.gather(*preview_tasks)

            for item, preview in zip(results, previews):
                item["page_preview"] = preview

            summary_lines = []
            for index, item in enumerate(results, start=1):
                summary_lines.append(
                    "\n".join(
                        [
                            f"{index}. {item['title']}",
                            f"URL: {item['url']}",
                            f"Snippet: {item['snippet'] or '(no snippet)'}",
                            (
                                f"Page preview: {item['page_preview']['preview_text']}"
                                if item.get("page_preview", {}).get("success")
                                else "Page preview: unavailable"
                            ),
                        ]
                    )
                )

            return {
                "success": True,
                "query": query,
                "engine": "ddgs",
                "content": "\n\n".join(summary_lines),
                "results": results,
                "citations": [item["url"] for item in results],
                "related_questions": [],
            }
        except Exception as exc:
            return {"success": False, "error": f"web search failed: {exc}"}


class FetchUrlTool(AgentTool):
    name = "fetch_url"
    description = (
        "Fetches and reads a public web page URL so the AIs can inspect the page text "
        "after or without a search step."
    )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return [] if params.get("url") else ["url is required"]

    def _strip_html(self, html: str) -> str:
        cleaned = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
        cleaned = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", cleaned)
        cleaned = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", cleaned)
        cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"&nbsp;", " ", cleaned)
        cleaned = re.sub(r"&amp;", "&", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        url = str(params["url"]).strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return {"success": False, "error": "url must start with http:// or https://"}

        async def request_page(verify: bool) -> httpx.Response:
            async with httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
                verify=verify,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    )
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response

        try:
            response = await request_page(verify=True)
        except (httpx.ConnectError,) + SSL_ERRORS:
            response = await request_page(verify=False)
            insecure_tls = True
        except Exception as exc:
            return {"success": False, "error": f"fetch url failed: {exc}"}

        try:
            html = response.text
            title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
            title = self._strip_html(title_match.group(1)) if title_match else ""
            text = self._strip_html(html)
            text = text[:5000] if len(text) > 5000 else text

            payload = {
                "success": True,
                "url": str(response.url),
                "status_code": response.status_code,
                "title": title,
                "content": text,
                "content_type": response.headers.get("content-type", ""),
            }
            if "insecure_tls" in locals():
                payload["insecure_tls"] = insecure_tls
            return payload
        except Exception as exc:
            return {"success": False, "error": f"fetch url failed: {exc}"}


class PlaywrightTool(AgentTool):
    browser_name = "chromium"

    def _ensure_playwright(self) -> None:
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "playwright is not installed. Install the Python package and Chromium browser."
            )

    async def _open_page(
        self,
        url: str,
        timeout_ms: int,
        wait_until: str = "networkidle",
    ):
        self._ensure_playwright()
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        return playwright, browser, page

    async def _close_page(self, playwright, browser) -> None:
        await browser.close()
        await playwright.stop()


class BrowserExtractTool(PlaywrightTool):
    name = "browser_extract"
    description = (
        "Uses Playwright to open a real browser page, wait for dynamic content, "
        "and extract readable text from the full page or a selector."
    )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return [] if params.get("url") else ["url is required"]

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        url = str(params["url"]).strip()
        selector = str(params.get("selector", "body")).strip() or "body"
        timeout_ms = int(params.get("timeout_ms", 30000))
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return {"success": False, "error": "url must start with http:// or https://"}

        try:
            playwright, browser, page = await self._open_page(url, timeout_ms=timeout_ms)
            try:
                if selector != "body":
                    await page.wait_for_selector(selector, timeout=timeout_ms)
                title = await page.title()
                content = await page.locator(selector).inner_text(timeout=timeout_ms)
                html = await page.content()
                return {
                    "success": True,
                    "url": page.url,
                    "title": title,
                    "selector": selector,
                    "content": content[:10000],
                    "html_preview": html[:4000],
                }
            finally:
                await self._close_page(playwright, browser)
        except Exception as exc:
            return {"success": False, "error": f"browser extract failed: {exc}"}


class BrowserScreenshotTool(PlaywrightTool):
    name = "browser_screenshot"
    description = (
        "Uses Playwright to render a page and save a screenshot to session data so "
        "the agent can visually inspect dynamic web content."
    )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return [] if params.get("url") else ["url is required"]

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        url = str(params["url"]).strip()
        timeout_ms = int(params.get("timeout_ms", 30000))
        full_page = bool(params.get("full_page", True))
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return {"success": False, "error": "url must start with http:// or https://"}

        session_dir = (
            context.runtime_config.data_root
            / "browser"
            / context.session_context.session_id
        )
        session_dir.mkdir(parents=True, exist_ok=True)
        filename = str(params.get("filename", "page.png")).strip() or "page.png"
        screenshot_path = (session_dir / filename).resolve()

        try:
            playwright, browser, page = await self._open_page(url, timeout_ms=timeout_ms)
            try:
                await page.screenshot(path=str(screenshot_path), full_page=full_page)
                return {
                    "success": True,
                    "url": page.url,
                    "path": str(screenshot_path),
                    "full_page": full_page,
                }
            finally:
                await self._close_page(playwright, browser)
        except Exception as exc:
            return {"success": False, "error": f"browser screenshot failed: {exc}"}


class BrowserCollectLinksTool(PlaywrightTool):
    name = "browser_collect_links"
    description = (
        "Uses Playwright to load a real page and collect visible links for crawling, "
        "pagination, and follow-up reading."
    )

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        return [] if params.get("url") else ["url is required"]

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        url = str(params["url"]).strip()
        timeout_ms = int(params.get("timeout_ms", 30000))
        max_links = max(1, min(int(params.get("max_links", 30)), 100))
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return {"success": False, "error": "url must start with http:// or https://"}

        try:
            playwright, browser, page = await self._open_page(url, timeout_ms=timeout_ms)
            try:
                raw_links = await page.eval_on_selector_all(
                    "a[href]",
                    """elements => elements.map(el => ({
                        text: (el.innerText || el.textContent || '').trim(),
                        href: el.href || '',
                    }))""",
                )
                links = []
                seen = set()
                for item in raw_links:
                    href = str(item.get("href", "")).strip()
                    if not href or href in seen:
                        continue
                    seen.add(href)
                    links.append(
                        {
                            "text": str(item.get("text", "")).strip(),
                            "url": href,
                        }
                    )
                    if len(links) >= max_links:
                        break

                return {
                    "success": True,
                    "url": page.url,
                    "links": links,
                    "count": len(links),
                }
            finally:
                await self._close_page(playwright, browser)
        except Exception as exc:
            return {"success": False, "error": f"browser collect links failed: {exc}"}


class GetDatetimeTool(AgentTool):
    name = "get_datetime"
    description = (
        "현재 날짜와 시간을 반환합니다. "
        "날짜, 시간, 요일, 타임존 등을 물어볼 때 사용하세요. 외부 명령 실행 없이 즉시 반환됩니다."
    )
    source = "core"

    async def execute(
        self, params: Dict[str, Any], context: ToolExecutionContext
    ) -> Dict[str, Any]:
        from datetime import datetime
        import time

        now = datetime.now()
        return {
            "success": True,
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y년 %m월 %d일"),
            "time": now.strftime("%H시 %M분 %S초"),
            "weekday": ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][now.weekday()],
            "timestamp": int(time.time()),
        }


class GetSystemInfoTool(AgentTool):
    name = "get_system_info"
    description = (
        "PC 시스템 정보를 반환합니다: OS, CPU 사용률, RAM, 디스크, Python 버전, 호스트명. "
        "시스템 상태를 확인할 때 사용하세요."
    )
    source = "core"

    async def execute(self, params: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        try:
            import psutil
            cpu_percent = await asyncio.to_thread(psutil.cpu_percent, 0.3)
            mem = psutil.virtual_memory()
            try:
                disk = psutil.disk_usage("/")
            except Exception:
                disk = psutil.disk_usage("C:\\")
            return {
                "success": True,
                "os": platform.system(),
                "os_version": platform.version()[:120],
                "architecture": platform.machine(),
                "python_version": platform.python_version(),
                "hostname": platform.node(),
                "cpu_cores_logical": psutil.cpu_count(logical=True),
                "cpu_cores_physical": psutil.cpu_count(logical=False),
                "cpu_percent": cpu_percent,
                "ram_total_gb": round(mem.total / 1e9, 2),
                "ram_used_gb": round(mem.used / 1e9, 2),
                "ram_percent": mem.percent,
                "disk_total_gb": round(disk.total / 1e9, 2),
                "disk_used_gb": round(disk.used / 1e9, 2),
                "disk_percent": disk.percent,
            }
        except ImportError:
            return {"success": False, "error": "psutil not installed. Run: pip install psutil"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


class RunPythonTool(AgentTool):
    name = "run_python"
    description = (
        "Python 코드를 실행하고 결과를 반환합니다. "
        "params: {code: str, timeout: int (optional, default 30)}"
    )
    source = "core"

    async def execute(self, params: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        code = str(params.get("code", "")).strip()
        if not code:
            return {"success": False, "error": "code is required"}
        timeout = min(int(params.get("timeout", 30)), 60)
        try:
            completed = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            return {
                "success": completed.returncode == 0,
                "stdout": completed.stdout[:5000],
                "stderr": completed.stderr[:2000],
                "returncode": completed.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Python execution timed out after {timeout}s"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


class ListProcessesTool(AgentTool):
    name = "list_processes"
    description = (
        "실행 중인 프로세스 목록을 반환합니다. "
        "params: {name_filter: str (optional, 이름에 포함된 문자열로 필터)}"
    )
    source = "core"

    async def execute(self, params: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        try:
            import psutil
            name_filter = str(params.get("name_filter", "")).lower().strip()
            processes = []
            for proc in psutil.process_iter(["pid", "name", "status", "cpu_percent", "memory_percent"]):
                try:
                    info = proc.info
                    if name_filter and name_filter not in (info["name"] or "").lower():
                        continue
                    processes.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "status": info["status"],
                        "cpu_percent": round(info["cpu_percent"] or 0, 1),
                        "memory_percent": round(info["memory_percent"] or 0, 2),
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            processes.sort(key=lambda x: x["memory_percent"], reverse=True)
            return {"success": True, "count": len(processes), "processes": processes[:50]}
        except ImportError:
            return {"success": False, "error": "psutil not installed. Run: pip install psutil"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


class KillProcessTool(AgentTool):
    name = "kill_process"
    description = (
        "프로세스를 종료합니다. "
        "params: {pid: int} 또는 {name: str (이름에 포함된 프로세스 전부 종료)}"
    )
    source = "core"

    async def execute(self, params: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        try:
            import psutil
            pid = params.get("pid")
            name = str(params.get("name", "")).strip()
            if not pid and not name:
                return {"success": False, "error": "pid or name is required"}
            killed = []
            if pid:
                proc = psutil.Process(int(pid))
                proc_name = proc.name()
                proc.terminate()
                killed.append({"pid": int(pid), "name": proc_name})
            else:
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        if name.lower() in (proc.info["name"] or "").lower():
                            proc.terminate()
                            killed.append({"pid": proc.info["pid"], "name": proc.info["name"]})
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            return {
                "success": len(killed) > 0,
                "killed": killed,
                "message": f"{len(killed)} process(es) terminated" if killed else "No matching process found",
            }
        except ImportError:
            return {"success": False, "error": "psutil not installed"}
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process {pid} not found"}
        except psutil.AccessDenied:
            return {"success": False, "error": "Access denied - insufficient permissions"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


class GetClipboardTool(AgentTool):
    name = "get_clipboard"
    description = "클립보드 내용을 읽어서 반환합니다."
    source = "core"

    async def execute(self, params: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        try:
            import pyperclip
            content = pyperclip.paste()
            return {"success": True, "content": content, "length": len(content)}
        except ImportError:
            return {"success": False, "error": "pyperclip not installed. Run: pip install pyperclip"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


class SetClipboardTool(AgentTool):
    name = "set_clipboard"
    description = "텍스트를 클립보드에 복사합니다. params: {text: str}"
    source = "core"

    async def execute(self, params: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        text = str(params.get("text", ""))
        try:
            import pyperclip
            pyperclip.copy(text)
            return {"success": True, "message": f"Copied {len(text)} characters to clipboard"}
        except ImportError:
            return {"success": False, "error": "pyperclip not installed. Run: pip install pyperclip"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


class GetEnvTool(AgentTool):
    name = "get_env"
    description = (
        "환경 변수를 읽습니다. "
        "params: {key: str (특정 키, 생략 시 민감 정보 제외한 전체 목록)}"
    )
    source = "core"

    _SENSITIVE = {"KEY", "SECRET", "PASSWORD", "TOKEN", "PASS", "CREDENTIAL", "APIKEY", "API_KEY"}

    async def execute(self, params: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        key = str(params.get("key", "")).strip()
        if key:
            value = os.environ.get(key)
            return {"success": value is not None, "key": key, "value": value, "exists": value is not None}
        safe = {
            k: v for k, v in os.environ.items()
            if not any(s in k.upper() for s in self._SENSITIVE)
        }
        return {"success": True, "count": len(safe), "env": safe}


class GetNetworkInfoTool(AgentTool):
    name = "get_network_info"
    description = "네트워크 인터페이스 정보, IP 주소, 송수신 통계를 반환합니다."
    source = "core"

    async def execute(self, params: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        try:
            import psutil, socket
            interfaces = []
            for iface_name, addrs in psutil.net_if_addrs().items():
                iface: Dict[str, Any] = {"name": iface_name, "addresses": []}
                for addr in addrs:
                    iface["addresses"].append({
                        "family": str(addr.family.name if hasattr(addr.family, "name") else addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                    })
                interfaces.append(iface)
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
            except Exception:
                hostname, local_ip = "unknown", "unknown"
            net_io = psutil.net_io_counters()
            return {
                "success": True,
                "hostname": hostname,
                "local_ip": local_ip,
                "interfaces": interfaces,
                "bytes_sent_mb": round(net_io.bytes_sent / 1e6, 2),
                "bytes_recv_mb": round(net_io.bytes_recv / 1e6, 2),
            }
        except ImportError:
            return {"success": False, "error": "psutil not installed"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


class GitRunTool(AgentTool):
    name = "git_run"
    description = (
        "git 명령을 실행합니다. "
        "params: {command: str (예: 'status', 'log --oneline -5', 'diff'), cwd: str (optional)}"
    )
    source = "core"

    _BLOCKED = ["push --force", "reset --hard", "clean -f", "filter-branch", "reflog delete"]

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        command = str(params.get("command", "")).strip()
        if not command:
            return ["command is required"]
        for blocked in self._BLOCKED:
            if blocked in command.lower():
                return [f"blocked git operation: {blocked}"]
        return []

    async def execute(self, params: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        command = str(params.get("command", "")).strip()
        cwd = str(params.get("cwd", "")).strip() or str(context.runtime_config.workspace_root)
        try:
            completed = await asyncio.to_thread(
                subprocess.run,
                ["git"] + command.split(),
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
                encoding="utf-8",
                errors="replace",
            )
            return {
                "success": completed.returncode == 0,
                "stdout": completed.stdout[:5000],
                "stderr": completed.stderr[:1000],
                "returncode": completed.returncode,
            }
        except FileNotFoundError:
            return {"success": False, "error": "git is not installed or not in PATH"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "git command timed out"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


class OpenFileTool(AgentTool):
    name = "open_file"
    description = (
        "파일, 폴더, 또는 URL을 기본 프로그램으로 엽니다. "
        "params: {path: str}"
    )
    source = "core"

    async def execute(self, params: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        path = str(params.get("path", "")).strip()
        if not path:
            return {"success": False, "error": "path is required"}
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                await asyncio.to_thread(subprocess.run, ["open", path])
            else:
                await asyncio.to_thread(subprocess.run, ["xdg-open", path])
            return {"success": True, "message": f"Opened: {path}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


TOOL_REGISTRY = AgentToolRegistry()
for tool in (
    # 시스템 정보 (안전)
    GetDatetimeTool(),
    GetSystemInfoTool(),
    GetNetworkInfoTool(),
    GetEnvTool(),
    ListProcessesTool(),
    GetClipboardTool(),
    # 파일 시스템
    ReadFileTool(),
    WriteFileTool(),
    ListFilesTool(),
    OpenFileTool(),
    # 코드/명령 실행
    RunPythonTool(),
    RunCommandTool(),
    GitRunTool(),
    # 프로세스/클립보드 (위험)
    KillProcessTool(),
    SetClipboardTool(),
    # 웹
    WebSearchTool(),
    FetchUrlTool(),
    BrowserExtractTool(),
    BrowserScreenshotTool(),
    BrowserCollectLinksTool(),
):
    TOOL_REGISTRY.register(tool)


def get_tools_description() -> str:
    return TOOL_REGISTRY.describe()


def get_registered_tools() -> List[Dict[str, str]]:
    return TOOL_REGISTRY.list_tools()


async def execute_tool(
    tool_name: str,
    params: Dict[str, Any],
    session_context: SessionContext | None = None,
    tool_policy: ToolPolicy | None = None,
) -> Dict[str, Any]:
    runtime_config = get_runtime_config()
    execution_context = ToolExecutionContext(
        session_context=session_context
        or SessionContext(session_id=runtime_config.default_session_id),
        runtime_config=runtime_config,
        tool_policy=tool_policy or ToolPolicy(runtime_config),
    )
    return await TOOL_REGISTRY.execute(tool_name, params, execution_context)
