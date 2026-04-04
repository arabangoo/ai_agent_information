"""
MultiClaw Agent Tools

Keeps the current built-in tools while exposing them through
an extensible registry that can later host plugins.
"""

from __future__ import annotations

import asyncio
import re
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


TOOL_REGISTRY = AgentToolRegistry()
for tool in (
    ReadFileTool(),
    WriteFileTool(),
    ListFilesTool(),
    RunCommandTool(),
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
