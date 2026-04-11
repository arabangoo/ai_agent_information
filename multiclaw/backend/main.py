"""
MultiClaw backend server.

The external service shape stays familiar while internal execution is now
session-aware, policy-driven, and easier to extend.
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_executor import AgentExecutor
from agent_tools import get_registered_tools
from ai_manager import AIManager
from cancellation_manager import CancellationManager
from file_search_manager import FileSearchManager
from memory_manager import MemoryManager
from agent_tools import TOOL_REGISTRY
from mcp_runtime_service import MCPRuntimeService
from mcp_tool_wrapper import refresh_mcp_tools
from runtime_config import get_runtime_config
from session_context import SessionStore
from stream_events import event_payload, sse_data
from tool_manager_models import MCPCallRequest, ToolCheckRequest, ToolRegistrationRequest
from tool_manager_service import ToolManagerService
from tool_policy import ToolPolicy
from voting_system import VotingSystem

load_dotenv()

runtime_config = get_runtime_config()

app = FastAPI(title="MultiClaw - AI Agent System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_manager = AIManager()
file_search_manager = FileSearchManager()
memory_manager = MemoryManager(runtime_config=runtime_config)
tool_policy = ToolPolicy(runtime_config)
voting_system = VotingSystem(ai_manager)
session_store = SessionStore(runtime_config)
cancellation_manager = CancellationManager()
tool_manager_service = ToolManagerService()
mcp_runtime_service = MCPRuntimeService()
agent_executor = AgentExecutor(
    ai_manager=ai_manager,
    voting_system=voting_system,
    memory_manager=memory_manager,
    tool_policy=tool_policy,
    cancellation_manager=cancellation_manager,
    runtime_config=runtime_config,
)


class ChatRequest(BaseModel):
    message: str
    include_context: bool = True
    session_id: Optional[str] = None


class AgentRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class MemorySearchRequest(BaseModel):
    query: str
    max_results: int = 10
    session_id: Optional[str] = None


def parse_message(message: str) -> tuple[str, List[str]]:
    mentions = re.findall(r"@(GPT|Claude|Gemini)", message, re.IGNORECASE)
    clean_message = re.sub(
        r"@(GPT|Claude|Gemini)\s*", "", message, flags=re.IGNORECASE
    ).strip()
    mentioned_ais = [
        ai.upper() if ai.upper() == "GPT" else ai.capitalize() for ai in mentions
    ]
    return clean_message, mentioned_ais


def select_ais(mentioned_ais: List[str]) -> List[str]:
    if mentioned_ais:
        return mentioned_ais
    available_ais = ai_manager.get_available_ais()
    return available_ais


def append_session_message(session_id: str, entry: Dict[str, Any]) -> None:
    session_store.append_message(session_id, entry)


def build_ai_responses(
    agent_result: Dict[str, Any], mentioned_ais: List[str]
) -> List[Dict[str, Any]]:
    responses = []
    ai_responses = agent_result.get("ai_responses", {})
    selected_ai_names = mentioned_ais or list(ai_responses.keys())
    timestamp = datetime.now().isoformat()

    for ai_name in selected_ai_names:
        if ai_name not in ai_responses:
            continue
        responses.append(
            {
                "ai_name": ai_name,
                "response": ai_responses[ai_name],
                "timestamp": timestamp,
                "has_context": False,
            }
        )
    return responses


async def run_agent_conversation(
    message: str, session_id: Optional[str], include_context: bool = True
) -> Dict[str, Any]:
    session_context = session_store.get_context(session_id)
    cancellation_manager.register(session_context.session_id, asyncio.current_task())
    try:
        clean_message, mentioned_ais = parse_message(message)

        append_session_message(
            session_context.session_id,
            {
                "type": "user",
                "message": message,
                "timestamp": datetime.now().isoformat(),
            },
        )
        memory_manager.save_memory(
            f"User: {clean_message}",
            category="chat",
            session_id=session_context.session_id,
        )

        if include_context:
            await file_search_manager.get_context(clean_message)

        agent_result = await agent_executor.execute(clean_message, session_context)
        responses = build_ai_responses(agent_result, mentioned_ais)

        for response in responses:
            append_session_message(
                session_context.session_id,
                {
                    "type": "ai",
                    "ai_name": response["ai_name"],
                    "message": response["response"],
                    "timestamp": response["timestamp"],
                },
            )

        return {
            "success": True,
            "session_id": session_context.session_id,
            "user_message": clean_message,
            "mentioned_ais": mentioned_ais,
            "responses": responses,
            "agent_result": agent_result,
        }
    finally:
        cancellation_manager.clear(session_context.session_id)


@app.on_event("startup")
async def startup_event():
    print("MultiClaw starting")
    print(f"Available AIs: {', '.join(ai_manager.get_available_ais())}")
    print(f"Memory root: {memory_manager.base_dir}")
    count = await asyncio.to_thread(refresh_mcp_tools, TOOL_REGISTRY, mcp_runtime_service)
    print(f"MCP tools loaded: {count}")


@app.get("/health")
async def health_check():
    history_stats = session_store.stats()
    memory_stats = memory_manager.get_global_stats()
    return {
        "status": "healthy",
        "system": "MultiClaw",
        "available_ais": ai_manager.get_available_ais(),
        "uploaded_files_count": len(file_search_manager.get_uploaded_files()),
        "chat_history_count": history_stats["message_count"],
        "session_count": history_stats["session_count"],
        "memory_entries": memory_stats["total_entries"],
        "registered_tools": get_registered_tools(),
        "mcp_servers": len(tool_manager_service.list_entries()),
    }


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = Query(default=None),
):
    session_context = session_store.get_context(session_id)
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in runtime_config.allowed_upload_extensions:
        raise HTTPException(400, f"unsupported file type: {file_ext}")

    content = await file.read()
    file_size = len(content)
    if file_size > runtime_config.max_upload_bytes:
        raise HTTPException(400, "file must be 100MB or smaller")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        result = await file_search_manager.upload_file(tmp_path, file.filename or "upload")
        append_session_message(
            session_context.session_id,
            {
                "type": "system",
                "message": f"Uploaded file: {file.filename}",
                "timestamp": datetime.now().isoformat(),
                "file_info": result,
            },
        )
        memory_manager.save_memory(
            f"Uploaded file: {file.filename} ({file_size} bytes)",
            category="file_upload",
            session_id=session_context.session_id,
        )
        return {
            "success": True,
            "message": "file upload completed",
            "session_id": session_context.session_id,
            "filename": file.filename,
            "file_size": file_size,
            **result,
        }
    except Exception as exc:
        raise HTTPException(500, f"upload failed: {exc}") from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        return await run_agent_conversation(
            request.message,
            request.session_id,
            include_context=request.include_context,
        )
    except asyncio.CancelledError:
        session_context = session_store.get_context(request.session_id)
        return {
            "success": False,
            "cancelled": True,
            "session_id": session_context.session_id,
            "responses": [],
            "agent_result": {
                "session_id": session_context.session_id,
                "steps": [],
                "ai_responses": {},
                "approved": False,
                "summary": "conversation cancelled",
                "pipeline": {"cancelled": "completed"},
            },
        }


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        session_context = session_store.get_context(request.session_id)
        try:
            clean_message, mentioned_ais = parse_message(request.message)
            append_session_message(
                session_context.session_id,
                {
                    "type": "user",
                    "message": request.message,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            memory_manager.save_memory(
                f"User: {clean_message}",
                category="chat",
                session_id=session_context.session_id,
            )

            file_search_context = None
            if request.include_context:
                file_search_context = await file_search_manager.get_context(clean_message)

            memory_context = memory_manager.get_context_for_chat(
                session_id=session_context.session_id
            )
            history = session_store.get_history(session_context.session_id)

            for ai_name in select_ais(mentioned_ais):
                yield sse_data(
                    event_payload(
                        "message_start",
                        provider=ai_name,
                        session_id=session_context.session_id,
                    )
                )
                enhanced_message = (
                    f"{memory_context}\n\n{clean_message}"
                    if memory_context
                    else clean_message
                )
                full_response = ""
                async for chunk in ai_manager.get_response_stream(
                    ai_name,
                    enhanced_message,
                    context=None,
                    history=history,
                    file_search_context=file_search_context,
                ):
                    full_response += chunk
                    yield sse_data(
                        event_payload(
                            "message_delta",
                            provider=ai_name,
                            session_id=session_context.session_id,
                            text=chunk,
                        )
                    )
                append_session_message(
                    session_context.session_id,
                    {
                        "type": "ai",
                        "ai_name": ai_name,
                        "message": full_response,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
                yield sse_data(
                    event_payload(
                        "message_end",
                        provider=ai_name,
                        session_id=session_context.session_id,
                    )
                )
            yield sse_data(
                event_payload("session_end", session_id=session_context.session_id)
            )
            yield "data: [COMPLETE]\n\n"
        except Exception as exc:
            yield sse_data(
                event_payload(
                    "error",
                    session_id=session_context.session_id,
                    message=str(exc),
                )
            )

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/agent")
async def agent_execute(request: AgentRequest):
    try:
        return await run_agent_conversation(
            request.message,
            request.session_id,
            include_context=True,
        )
    except asyncio.CancelledError:
        session_context = session_store.get_context(request.session_id)
        return {
            "success": False,
            "cancelled": True,
            "session_id": session_context.session_id,
            "responses": [],
            "agent_result": {
                "session_id": session_context.session_id,
                "steps": [],
                "ai_responses": {},
                "approved": False,
                "summary": "conversation cancelled",
                "pipeline": {"cancelled": "completed"},
            },
        }
    except Exception as exc:
        raise HTTPException(500, f"agent execution failed: {exc}") from exc


@app.post("/api/chat/cancel")
async def cancel_chat(session_id: Optional[str] = Query(default=None)):
    session_context = session_store.get_context(session_id)
    was_running = cancellation_manager.cancel(session_context.session_id)
    return {
        "success": True,
        "session_id": session_context.session_id,
        "cancel_requested": True,
        "was_running": was_running,
    }


@app.get("/api/memory")
async def get_memory(session_id: Optional[str] = Query(default=None)):
    return memory_manager.get_summary(session_id=session_id)


@app.post("/api/memory/search")
async def search_memory(request: MemorySearchRequest):
    return memory_manager.search_memory(
        request.query,
        request.max_results,
        session_id=request.session_id,
    )


@app.delete("/api/memory")
async def clear_memory(session_id: Optional[str] = Query(default=None)):
    return memory_manager.clear_all(session_id=session_id)


@app.get("/api/memory/daily")
async def get_daily_memory(
    date: Optional[str] = Query(default=None),
    session_id: Optional[str] = Query(default=None),
):
    return memory_manager.get_daily_log(date, session_id=session_id)


@app.get("/api/history")
async def get_history(session_id: Optional[str] = Query(default=None)):
    history = session_store.get_history(session_id)
    return {
        "success": True,
        "session_id": session_store.get_context(session_id).session_id,
        "history": history,
        "count": len(history),
    }


@app.delete("/api/history")
async def clear_history(session_id: Optional[str] = Query(default=None)):
    session_store.clear_history(session_id)
    return {
        "success": True,
        "message": "history cleared",
        "session_id": session_store.get_context(session_id).session_id
        if session_id
        else "all",
    }


@app.get("/api/documents")
async def list_documents():
    return await file_search_manager.list_documents()


@app.delete("/api/documents/{document_id:path}")
async def delete_document(document_id: str):
    return await file_search_manager.delete_document(document_id)


@app.delete("/api/documents")
async def clear_all_documents():
    return await file_search_manager.clear_all_documents()


# ---------------------------------------------------------------------------
# Tool Manager (MCP) endpoints
# ---------------------------------------------------------------------------


@app.get("/api/tool-manager/config")
def get_tool_manager_config():
    return tool_manager_service.get_config()


@app.post("/api/tool-manager/register")
def register_tool(request: ToolRegistrationRequest):
    result = tool_manager_service.register(request)
    refresh_mcp_tools(TOOL_REGISTRY, mcp_runtime_service)
    return result


@app.post("/api/tool-manager/check")
def check_tool(request: ToolCheckRequest):
    return tool_manager_service.check(request)


@app.delete("/api/tool-manager/{name}")
def delete_tool(name: str):
    result = tool_manager_service.delete(name)
    refresh_mcp_tools(TOOL_REGISTRY, mcp_runtime_service)
    return result


@app.get("/api/tool-manager/{name}/tools")
def list_mcp_tools(name: str):
    try:
        tools = mcp_runtime_service.list_tools(name)
        return {"server_name": name, "tools": tools, "success": True}
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.post("/api/tool-manager/{name}/call")
def call_mcp_tool(name: str, request: MCPCallRequest):
    result = mcp_runtime_service.call_tool(name, request.tool_name, request.arguments)
    if not result.success:
        raise HTTPException(500, result.message)
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
