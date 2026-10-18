"""Exercise the real Node MCP transport and scripted MultiClaw agent caller.

Run npm ci in backend/mcp_bridge first. No model credentials or browser needed.
"""

import asyncio
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

import agent_tools
import runtime_config
from agent_executor import AgentExecutor
from cancellation_manager import CancellationManager
from mcp_runtime_service import PARALLEL_SEARCH_URL, MCPRuntimeService
from mcp_tool_wrapper import refresh_mcp_tools
from runtime_config import RuntimeConfig
from session_context import SessionContext
from tool_manager_models import ToolRegistrationRequest
from tool_policy import ToolPolicy, ToolPolicyDecision

PROJECT_AGENT = "MultiClaw/2.0.0 (+https://github.com/arabangoo/ai_agent_information)"
PAGE_URL = "https://www.python.org/downloads/?source=multiclaw#release"
SEARCH_ARGS = {
    "objective": "Find the current Python release",
    "search_queries": ["Python latest release official"],
}


class MCPFixture:
    """A local JSON/Streamable HTTP MCP server, not a transport mock."""

    def __init__(self):
        self.requests = []
        self.error = False
        self.hang = False
        self.call_status = None
        self.malformed = False
        self.started = threading.Event()
        self.release = threading.Event()
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def reply(self, status, body=None):
                data = json.dumps(body).encode() if body is not None else b""
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self):
                self.reply(405)

            def do_DELETE(self):
                self.reply(200)

            def do_POST(self):
                request = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"]))
                )
                fixture.requests.append(
                    {"path": self.path, "headers": dict(self.headers), "body": request}
                )
                method = request.get("method")
                if "id" not in request:
                    self.reply(202)
                    return
                if method == "initialize":
                    result = {
                        "protocolVersion": request["params"]["protocolVersion"],
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "fixture", "version": "1"},
                    }
                elif method == "tools/list":
                    result = {
                        "tools": [
                            {
                                "name": "web_search",
                                "description": "Search the web",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "objective": {"type": "string"},
                                        "search_queries": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                    "required": ["objective", "search_queries"],
                                },
                            },
                            {
                                "name": "web_fetch",
                                "description": "Read web pages",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "urls": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        }
                                    },
                                    "required": ["urls"],
                                },
                            },
                        ]
                    }
                elif method == "tools/call":
                    fixture.started.set()
                    if fixture.call_status is not None:
                        self.reply(fixture.call_status, {"error": "fixture denied"})
                        return
                    if fixture.hang:
                        fixture.release.wait(10)
                    result = {
                        "content": [
                            {
                                "type": "text",
                                "text": "Fixture search result: Python release "
                                + PAGE_URL,
                            }
                        ]
                    }
                    if request["params"]["name"] == "web_fetch":
                        result["content"][0]["text"] = (
                            "Fixture page text: Python release notes " + PAGE_URL
                        )
                    if fixture.error:
                        result = {
                            "isError": True,
                            "content": [
                                {"type": "text", "text": "fixture quota exceeded"}
                            ],
                        }
                    if fixture.malformed:
                        result = {"content": 42}
                else:
                    self.reply(400)
                    return
                self.reply(
                    200, {"jsonrpc": "2.0", "id": request["id"], "result": result}
                )

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/mcp?fixture=1"

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def calls(self):
        return [r for r in self.requests if r["body"].get("method") == "tools/call"]


class ScriptedAI:
    """Fixed model replies verify tool/result plumbing, not live model behavior."""

    def __init__(self, plan):
        self.plan = plan
        self.prompts = []

    def get_available_ais(self):
        return ["GPT"]

    async def get_response(self, **kwargs):
        self.prompts.append(kwargs["message"])
        if len(self.prompts) == 1:
            return json.dumps(
                {"plan": self.plan, "explanation": "scripted Parallel selection"}
            )
        return "Consumed fixture result: " + (
            PAGE_URL if PAGE_URL in kwargs["message"] else "no page"
        )


class ParallelMCPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        backend = Path(__file__).resolve().parents[1]
        self.config = RuntimeConfig(
            workspace_root=root,
            backend_root=backend,
            data_root=root / "data",
            memory_root=root / "memory",
            parallel_search_enabled=True,
        )
        self.config_path = root / "tool_manager_config.json"
        self.config_path.write_text('{"mcpServers": {}}\n')
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if not any(
                word in k.upper() for word in ("KEY", "TOKEN", "SECRET", "PASSWORD")
            )
        }
        self.env = patch.dict(os.environ, clean_env, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.config_patch = patch.object(runtime_config, "_CONFIG", self.config)
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.runtime = MCPRuntimeService()

    def fixture(self):
        fixture = MCPFixture()
        self.addCleanup(fixture.close)
        self.runtime.tool_manager.register(
            ToolRegistrationRequest(name="parallel", transport="http", url=fixture.url)
        )
        return fixture

    async def discover(self):
        count = await asyncio.to_thread(
            refresh_mcp_tools, agent_tools.TOOL_REGISTRY, self.runtime
        )
        self.addCleanup(
            lambda: [
                agent_tools.TOOL_REGISTRY._tools.pop(name, None)
                for name in list(agent_tools.TOOL_REGISTRY._tools)
                if name.startswith("parallel__")
            ]
        )
        self.assertEqual(count, 2)
        self.assertIn('"search_queries"', agent_tools.get_tools_description())

    def executor(self, ai, policy=None):
        memory = Mock()
        memory.get_context_for_chat.return_value = ""
        return AgentExecutor(
            ai,
            Mock(),
            memory,
            policy or ToolPolicy(self.config),
            CancellationManager(),
            self.config,
        )

    async def test_opt_in_and_disabled_preserve_native_default(self):
        original = self.config_path.read_bytes()
        self.assertEqual(self.runtime.available_servers()[0].url, PARALLEL_SEARCH_URL)
        self.assertEqual(
            self.runtime._entry_to_bridge_server(self.runtime._get_server("parallel")),
            {"transport": "http", "url": "https://search.parallel.ai/mcp"},
        )
        self.runtime.parallel_search_enabled = False
        self.assertEqual(self.runtime.available_servers(), [])
        self.assertFalse(self.runtime.has_server("parallel"))
        self.assertTrue(agent_tools.TOOL_REGISTRY.has("web_search"))
        self.assertEqual(self.config_path.read_bytes(), original)
        with patch.dict(os.environ, {"MULTICLAW_PARALLEL_SEARCH": "0"}):
            self.assertFalse(RuntimeConfig.from_env().parallel_search_enabled)
        with patch.dict(os.environ, {"MULTICLAW_PARALLEL_SEARCH": "1"}):
            self.assertTrue(RuntimeConfig.from_env().parallel_search_enabled)
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(RuntimeConfig.from_env().parallel_search_enabled)

    async def test_saved_override_wins_even_when_preset_disabled(self):
        self.runtime.tool_manager.register(
            ToolRegistrationRequest(
                name="PARALLEL", transport="http", url="https://example.org/custom-mcp"
            )
        )
        original = self.config_path.read_bytes()
        self.assertEqual(len(self.runtime.available_servers()), 1)
        self.assertEqual(
            self.runtime._get_server("parallel").url, "https://example.org/custom-mcp"
        )
        self.runtime.parallel_search_enabled = False
        self.assertEqual(self.runtime._get_server("parallel").name, "PARALLEL")
        self.assertEqual(self.config_path.read_bytes(), original)

    async def test_incomplete_explicit_entry_is_not_replaced(self):
        self.runtime.tool_manager.register(
            ToolRegistrationRequest(name="parallel", transport="http", url="")
        )
        self.assertEqual(self.runtime.available_servers(), [])
        self.assertEqual(self.runtime._get_server("parallel").url, "")

    async def test_disabling_preset_removes_discovered_tools(self):
        self.fixture()
        await self.discover()
        self.runtime.tool_manager.delete("parallel")
        self.runtime.parallel_search_enabled = False
        count = await asyncio.to_thread(
            refresh_mcp_tools, agent_tools.TOOL_REGISTRY, self.runtime
        )
        self.assertEqual(count, 0)
        self.assertFalse(agent_tools.TOOL_REGISTRY.has("parallel__web_search"))
        self.assertTrue(agent_tools.TOOL_REGISTRY.has("web_search"))

    async def test_dispatch_search_fetch_and_observed_headers(self):
        fixture = self.fixture()
        await self.discover()
        search = await agent_tools.execute_tool("parallel__web_search", SEARCH_ARGS)
        fetch = await agent_tools.execute_tool(
            "parallel__web_fetch", {"urls": [PAGE_URL]}
        )
        self.assertTrue(search["success"])
        self.assertTrue(fetch["success"])
        self.assertIn(PAGE_URL, search["content"])
        self.assertIn("Python release notes", fetch["content"])
        self.assertEqual(fixture.calls()[0]["body"]["params"]["arguments"], SEARCH_ARGS)
        self.assertEqual(
            fixture.calls()[1]["body"]["params"]["arguments"], {"urls": [PAGE_URL]}
        )
        self.assertTrue(
            any(r["body"]["method"] == "tools/list" for r in fixture.requests)
        )
        for request in fixture.requests:
            headers = {k.lower(): v for k, v in request["headers"].items()}
            self.assertEqual(request["path"], "/mcp?fixture=1")
            self.assertEqual(headers["user-agent"], PROJECT_AGENT)
            self.assertNotIn("authorization", headers)

    async def test_scripted_agent_consumes_results_without_ddgs_override(self):
        fixture = self.fixture()
        await self.discover()
        ai = ScriptedAI(
            [
                {"tool": "parallel__web_search", "params": SEARCH_ARGS},
                {"tool": "parallel__web_fetch", "params": {"urls": [PAGE_URL]}},
            ]
        )
        with patch.object(
            agent_tools.WebSearchTool,
            "execute",
            side_effect=AssertionError("ddgs must not replace explicit MCP selection"),
        ):
            result = await self.executor(ai).execute(
                "Search the web for the latest Python release using Parallel",
                SessionContext("fixture"),
            )
        self.assertEqual(result["pipeline"]["execute"], "completed")
        self.assertIn(PAGE_URL, result["ai_responses"]["GPT"])
        self.assertIn("Fixture page text", ai.prompts[-1])
        self.assertEqual(len(fixture.calls()), 2)

    async def test_policy_denial_prevents_remote_call(self):
        fixture = self.fixture()
        await self.discover()
        policy = Mock(spec=ToolPolicy)
        policy.assess.return_value = ToolPolicyDecision(
            False, "search disabled by policy", SEARCH_ARGS
        )
        ai = ScriptedAI([{"tool": "parallel__web_search", "params": SEARCH_ARGS}])
        result = await self.executor(ai, policy).execute(
            "latest release via Parallel", SessionContext("fixture")
        )
        self.assertEqual(result["pipeline"]["execute"], "failed")
        self.assertEqual(fixture.calls(), [])

    async def test_remote_tool_error_is_not_success_or_fallback(self):
        fixture = self.fixture()
        fixture.error = True
        await self.discover()
        ai = ScriptedAI([{"tool": "parallel__web_search", "params": SEARCH_ARGS}])
        result = await self.executor(ai).execute(
            "latest release via Parallel", SessionContext("fixture")
        )
        self.assertFalse(result["steps"][0]["result"]["success"])
        self.assertIn("fixture quota exceeded", result["steps"][0]["result"]["error"])
        self.assertEqual(len(fixture.calls()), 1)
        # Cover the synchronous Tool Manager caller too.
        sync_result = await asyncio.to_thread(
            self.runtime.call_tool, "parallel", "web_search", SEARCH_ARGS
        )
        self.assertFalse(sync_result.success)

    async def test_unknown_explicit_search_is_validated_not_replaced(self):
        ai = ScriptedAI([{"tool": "missing__web_search", "params": SEARCH_ARGS}])
        result = await self.executor(ai).execute(
            "latest release", SessionContext("fixture")
        )
        self.assertEqual(result["steps"][0]["tool"], "missing__web_search")
        self.assertIn("unknown tool", result["steps"][0]["result"]["error"])

    async def test_authentication_error_is_failure(self):
        fixture = self.fixture()
        await self.discover()
        fixture.call_status = 401
        result = await agent_tools.execute_tool("parallel__web_search", SEARCH_ARGS)
        self.assertFalse(result["success"])
        self.assertIn("fixture denied", result["error"])
        self.assertEqual(len(fixture.calls()), 1)

    async def test_malformed_tool_response_is_failure(self):
        fixture = self.fixture()
        await self.discover()
        fixture.malformed = True
        result = await agent_tools.execute_tool("parallel__web_search", SEARCH_ARGS)
        self.assertFalse(result["success"])
        self.assertTrue(result["error"])

    async def test_missing_required_argument_stops_before_remote_call(self):
        fixture = self.fixture()
        await self.discover()
        ai = ScriptedAI(
            [{"tool": "parallel__web_search", "params": {"objective": "release"}}]
        )
        result = await self.executor(ai).execute(
            "latest release", SessionContext("fixture")
        )
        self.assertFalse(result["steps"][0]["validation"]["valid"])
        self.assertEqual(fixture.calls(), [])

    async def test_timeout_is_reported(self):
        fixture = self.fixture()
        fixture.hang = True
        await self.discover()
        self.runtime.default_timeout_seconds = 0.1
        result = await agent_tools.execute_tool("parallel__web_search", SEARCH_ARGS)
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["error"].lower())

    async def test_cancellation_reaps_http_bridge(self):
        fixture = self.fixture()
        fixture.hang = True
        await self.discover()
        spawned = []
        create_process = asyncio.create_subprocess_exec

        async def capture_process(*args, **kwargs):
            process = await create_process(*args, **kwargs)
            spawned.append(process)
            return process

        with patch(
            "mcp_runtime_service.asyncio.create_subprocess_exec",
            side_effect=capture_process,
        ):
            task = asyncio.create_task(
                agent_tools.execute_tool("parallel__web_search", SEARCH_ARGS)
            )
            self.assertTrue(await asyncio.to_thread(fixture.started.wait, 5))
            cancellation = CancellationManager()
            cancellation.register("fixture", task)
            self.assertTrue(cancellation.cancel("fixture"))
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(len(spawned), 1)
        self.assertIsNotNone(spawned[0].returncode)

    async def test_invalid_explicit_endpoint_fails_without_builtin_fallback(self):
        self.runtime.tool_manager.register(
            ToolRegistrationRequest(name="parallel", transport="http", url="not a URL")
        )
        result = await self.runtime.call_tool_async(
            "parallel", "web_search", SEARCH_ARGS
        )
        self.assertFalse(result.success)
        self.assertIn("invalid url", result.message.lower())
        self.assertEqual(self.runtime._get_server("parallel").url, "not a URL")

    async def test_default_ddgs_search_contract_is_preserved(self):
        async def search(*_args, **_kwargs):
            return [
                {
                    "title": "Python",
                    "url": PAGE_URL,
                    "snippet": "release",
                    "source": "web",
                }
            ]

        async def preview(*_args):
            return {"success": True, "preview_text": "release notes"}

        ai = ScriptedAI([])
        with (
            patch.object(agent_tools.WebSearchTool, "_search_web", side_effect=search),
            patch.object(
                agent_tools.WebSearchTool, "_fetch_preview", side_effect=preview
            ),
        ):
            result = await self.executor(ai).execute(
                "latest Python release", SessionContext("fixture")
            )
        self.assertEqual(result["steps"][0]["tool"], "web_search")
        self.assertEqual(result["steps"][0]["result"]["engine"], "ddgs")
        self.assertEqual(result["steps"][0]["result"]["citations"], [PAGE_URL])


if __name__ == "__main__":
    unittest.main()
