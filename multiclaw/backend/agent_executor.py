"""
MultiClaw Agent Executor

Pipeline:
1. Plan
2. Validate
3. Policy check
4. Execute
5. Audit
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List

from ai_manager import AIManager
from agent_tools import TOOL_REGISTRY, execute_tool, get_tools_description
from cancellation_manager import CancellationManager
from memory_manager import MemoryManager
from runtime_config import RuntimeConfig, get_runtime_config
from session_context import SessionContext
from tool_policy import ToolPolicy
from voting_system import VotingSystem


# 파괴적/위험 작업만 투표 필요 — 이외 모든 도구는 자동 승인
VOTE_REQUIRED_TOOLS = frozenset({
    "write_file",
    "run_command",
    "kill_process",
    "git_run",
})


PLAN_PROMPT_TEMPLATE = """당신은 MultiClaw의 로컬 시스템 에이전트 플래너입니다.
MultiClaw는 로컬 파일 읽기/쓰기, 디렉토리 조회, 시스템 명령 실행, 웹 검색을 실제로 수행할 수 있습니다.
또한 MCP(Model Context Protocol) 서버에 연결된 외부 도구도 사용할 수 있습니다.
사용자가 파일/폴더/경로/명령/검색을 요청하면 도구를 써야 하며, 로컬 시스템 접근이 불가능하다고 말하면 안 됩니다.

사용 가능한 도구 (이름을 그대로 "tool" 필드에 사용):
{tools_description}

사용자 요청: {user_message}

{memory_context}

중요 규칙:
- 파일, 폴더, 경로, 드라이브(C:\\ 등), 확장자, 생성/수정/삭제/읽기/목록/검색 요청이 있으면 반드시 도구 계획을 만드세요.
- MCP 도구는 이름이 "ServerName__tool_name" 형식입니다. params는 해당 도구의 스키마에 맞게 작성하세요.
- 일반 대화가 아닌 이상 "도구 없이 답변"으로 빼지 마세요.
- 상대 경로와 절대 경로를 모두 사용할 수 있습니다.
- JSON 외 텍스트를 절대 출력하지 마세요.

반드시 JSON만 반환:
{{
  "plan": [
    {{
      "tool": "tool_name",
      "params": {{"key": "value"}},
      "description": "이 단계에서 수행할 작업"
    }}
  ],
  "explanation": "전체 작업 계획 설명"
}}

정말로 도구가 필요 없는 순수 일반 대화일 때만:
{{
  "plan": [],
  "explanation": "일반 대화 - 도구 사용 불필요"
}}"""


FINAL_RESPONSE_PROMPT = """당신은 MultiClaw입니다.
아래 작업은 이미 실제로 실행되었고, 결과도 확보되어 있습니다.
로컬 파일이나 시스템에 접근할 수 없다고 말하지 말고, 실행 결과를 바탕으로 사용자에게 명확히 설명하세요.

사용자 요청: {user_message}
실행 결과:
{execution_results}

검증 및 투표 결과:
{vote_summary}
"""


class AgentExecutor:
    def __init__(
        self,
        ai_manager: AIManager,
        voting_system: VotingSystem,
        memory_manager: MemoryManager,
        tool_policy: ToolPolicy,
        cancellation_manager: CancellationManager,
        runtime_config: RuntimeConfig | None = None,
    ):
        self.ai_manager = ai_manager
        self.voting_system = voting_system
        self.memory_manager = memory_manager
        self.tool_policy = tool_policy
        self.cancellation_manager = cancellation_manager
        self.runtime_config = runtime_config or get_runtime_config()

    def _looks_like_live_web_query(self, user_message: str) -> bool:
        message = user_message.lower()
        keywords = [
            "latest",
            "recent",
            "today",
            "news",
            "current",
            "up-to-date",
            "search the web",
            "web search",
            "look up",
            "최신",
            "최근",
            "오늘",
            "뉴스",
            "실시간",
            "웹검색",
            "웹 검색",
            "찾아봐",
            "검색해",
        ]
        return any(keyword in message for keyword in keywords)

    def _should_force_web_search(
        self, user_message: str, plan_result: Dict[str, Any]
    ) -> bool:
        planned_tools = [
            step.get("tool")
            for step in plan_result.get("plan", [])
            if isinstance(step, dict)
        ]
        if "web_search" in planned_tools or "fetch_url" in planned_tools:
            return False
        return self._looks_like_live_web_query(user_message)

    def _build_fallback_web_plan(self, user_message: str) -> Dict[str, Any]:
        return {
            "success": True,
            "plan": [
                {
                    "tool": "web_search",
                    "params": {"query": user_message, "max_results": 5},
                    "description": "Search the live web for current information relevant to the request.",
                }
            ],
            "explanation": (
                "Injected a live web search step because the request appears to need "
                "current or externally verified information."
            ),
            "planner": "system-fallback",
        }

    def _check_cancelled(self, session_context: SessionContext) -> None:
        self.cancellation_manager.raise_if_cancelled(session_context.session_id)

    async def _create_plan(
        self, user_message: str, session_context: SessionContext
    ) -> Dict[str, Any]:
        memory_context = self.memory_manager.get_context_for_chat(
            session_id=session_context.session_id
        )
        prompt = PLAN_PROMPT_TEMPLATE.format(
            tools_description=get_tools_description(),
            user_message=user_message,
            memory_context=(
                f"Relevant memory:\n{memory_context}" if memory_context else "No memory context."
            ),
        )

        available = self.ai_manager.get_available_ais()
        planner_ai = "Gemini" if "Gemini" in available else available[0]
        response = await self.ai_manager.get_response(
            ai_name=planner_ai,
            message=prompt,
            context=None,
            history=None,
            file_search_context=None,
        )

        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            return {
                "success": False,
                "plan": [],
                "explanation": "planner did not return valid JSON",
                "planner": planner_ai,
                "raw_response": response,
            }

        try:
            payload = json.loads(json_match.group())
        except json.JSONDecodeError:
            return {
                "success": False,
                "plan": [],
                "explanation": "planner JSON parsing failed",
                "planner": planner_ai,
                "raw_response": response,
            }

        return {
            "success": True,
            "plan": payload.get("plan", []),
            "explanation": payload.get("explanation", ""),
            "planner": planner_ai,
        }

    def _validate_plan(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        validated_steps = []
        for index, step in enumerate(plan, start=1):
            tool_name = step.get("tool", "")
            params = step.get("params", {})
            description = step.get("description", "") or f"Step {index}"
            validation_errors: List[str] = []

            if not tool_name:
                validation_errors.append("tool is required")
            elif not TOOL_REGISTRY.has(tool_name):
                validation_errors.append(f"unknown tool: {tool_name}")

            if not isinstance(params, dict):
                validation_errors.append("params must be an object")
                params = {}

            tool = TOOL_REGISTRY.get(tool_name) if tool_name else None
            if tool is not None:
                validation_errors.extend(tool.validate_params(params))

            validated_steps.append(
                {
                    "step": index,
                    "tool": tool_name,
                    "params": params,
                    "description": description,
                    "validation": {
                        "valid": len(validation_errors) == 0,
                        "errors": validation_errors,
                    },
                }
            )

        return validated_steps

    async def _generate_final_response(
        self,
        user_message: str,
        execution_results: List[Dict[str, Any]],
        vote_summaries: List[str],
    ) -> Dict[str, str]:
        results_text = []
        for item in execution_results:
            results_text.append(
                json.dumps(
                    {
                        "tool": item.get("tool"),
                        "description": item.get("description"),
                        "result": item.get("result"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )[:1200]
            )

        prompt = FINAL_RESPONSE_PROMPT.format(
            user_message=user_message,
            execution_results="\n\n".join(results_text) if results_text else "No tool execution.",
            vote_summary="\n".join(vote_summaries) if vote_summaries else "No vote",
        )

        responses: Dict[str, str] = {}
        for ai_name in self.ai_manager.get_available_ais():
            try:
                responses[ai_name] = await self.ai_manager.get_response(
                    ai_name=ai_name,
                    message=prompt,
                    context=None,
                    history=None,
                    file_search_context=None,
                )
            except Exception as exc:
                responses[ai_name] = f"response generation failed: {exc}"
        return responses

    def _audit_log(
        self,
        session_context: SessionContext,
        user_message: str,
        result: Dict[str, Any],
    ) -> None:
        audit_payload = {
            "request": user_message,
            "approved": result.get("approved", False),
            "summary": result.get("summary", ""),
            "steps": [
                {
                    "step": step.get("step"),
                    "tool": step.get("tool"),
                    "validation": step.get("validation"),
                    "policy": step.get("policy"),
                    "vote_summary": step.get("vote", {}).get("summary")
                    if isinstance(step.get("vote"), dict)
                    else None,
                    "success": (
                        step.get("result", {}).get("success")
                        if isinstance(step.get("result"), dict)
                        else None
                    ),
                }
                for step in result.get("steps", [])
            ],
        }
        self.memory_manager.save_memory(
            json.dumps(audit_payload, ensure_ascii=False, indent=2),
            category="agent_audit",
            session_id=session_context.session_id,
        )

    async def execute(
        self, user_message: str, session_context: SessionContext
    ) -> Dict[str, Any]:
        started_at = datetime.now().isoformat()
        self._check_cancelled(session_context)
        result: Dict[str, Any] = {
            "session_id": session_context.session_id,
            "started_at": started_at,
            "plan": None,
            "steps": [],
            "ai_responses": {},
            "approved": True,
            "summary": "",
            "pipeline": {
                "plan": "pending",
                "validate": "pending",
                "policy": "pending",
                "execute": "pending",
                "audit": "pending",
            },
        }

        plan_result = await self._create_plan(user_message, session_context)
        self._check_cancelled(session_context)
        if self._should_force_web_search(user_message, plan_result):
            plan_result = self._build_fallback_web_plan(user_message)
        result["plan"] = plan_result
        result["pipeline"]["plan"] = "completed" if plan_result.get("success") else "failed"

        if not plan_result.get("plan"):
            responses = {}
            for ai_name in self.ai_manager.get_available_ais():
                self._check_cancelled(session_context)
                responses[ai_name] = await self.ai_manager.get_response(
                    ai_name=ai_name,
                    message=user_message,
                    context=None,
                    history=None,
                    file_search_context=None,
                )
            result["ai_responses"] = responses
            result["summary"] = "answered without tool execution"
            result["pipeline"]["validate"] = "completed"
            result["pipeline"]["policy"] = "completed"
            result["pipeline"]["execute"] = "completed"
            self._audit_log(session_context, user_message, result)
            result["pipeline"]["audit"] = "completed"
            return result

        validated_steps = self._validate_plan(plan_result["plan"])
        result["steps"] = validated_steps
        result["pipeline"]["validate"] = "completed"

        execution_results: List[Dict[str, Any]] = []
        vote_summaries: List[str] = []

        for step in result["steps"]:
            self._check_cancelled(session_context)
            if not step["validation"]["valid"]:
                step["policy"] = {"allowed": False, "reason": "validation failed"}
                step["vote"] = {
                    "approved": False,
                    "approve_count": 0,
                    "reject_count": 0,
                    "total_voters": 0,
                    "votes": [],
                    "summary": "validation failed",
                }
                step["result"] = {
                    "success": False,
                    "error": "; ".join(step["validation"]["errors"]),
                }
                result["approved"] = False
                result["summary"] = "agent plan validation failed"
                result["pipeline"]["policy"] = "completed"
                result["pipeline"]["execute"] = "failed"
                break

            policy_decision = self.tool_policy.assess(step["tool"], step["params"])
            step["policy"] = {
                "allowed": policy_decision.allowed,
                "reason": policy_decision.reason,
            }

            if not policy_decision.allowed:
                step["vote"] = {
                    "approved": False,
                    "approve_count": 0,
                    "reject_count": 0,
                    "total_voters": 0,
                    "votes": [],
                    "summary": "blocked by tool policy",
                }
                step["result"] = {
                    "success": False,
                    "error": policy_decision.reason,
                    "blocked": True,
                }
                result["approved"] = False
                result["summary"] = "agent request blocked by policy"
                result["pipeline"]["policy"] = "completed"
                result["pipeline"]["execute"] = "failed"
                break

            step["params"] = policy_decision.normalized_params

            if step["tool"] not in VOTE_REQUIRED_TOOLS:
                step["vote"] = {
                    "approved": True,
                    "approve_count": 3,
                    "reject_count": 0,
                    "total_voters": 3,
                    "votes": [],
                    "summary": "auto-approved",
                }
                vote_summaries.append(f"step {step['step']} ({step['tool']}): auto-approved")
            else:
                vote_result = await self.voting_system.conduct_vote(
                    user_command=user_message,
                    tool_name=step["tool"],
                    parameters=step["params"],
                )
                self._check_cancelled(session_context)
                step["vote"] = vote_result
                vote_summaries.append(f"step {step['step']} ({step['tool']}): {vote_result['summary']}")

                if not vote_result["approved"]:
                    step["result"] = {
                        "success": False,
                        "error": f"vote rejected: {vote_result['summary']}",
                    }
                    result["approved"] = False
                    result["summary"] = "agent request rejected by vote"
                    result["pipeline"]["policy"] = "completed"
                    result["pipeline"]["execute"] = "failed"
                    break

            tool_result = await execute_tool(
                step["tool"],
                step["params"],
                session_context=session_context,
                tool_policy=self.tool_policy,
            )
            self._check_cancelled(session_context)
            step["result"] = tool_result
            execution_results.append(
                {
                    "tool": step["tool"],
                    "description": step["description"],
                    "result": tool_result,
                }
            )

            if not tool_result.get("success", False):
                result["approved"] = False
                result["summary"] = "tool execution failed"
                result["pipeline"]["policy"] = "completed"
                result["pipeline"]["execute"] = "failed"
                break

        if result["pipeline"].get("execute") != "failed":
            result["pipeline"]["policy"] = "completed"
            result["pipeline"]["execute"] = "completed"

        self._check_cancelled(session_context)
        result["ai_responses"] = await self._generate_final_response(
            user_message, execution_results, vote_summaries
        )
        if result["pipeline"].get("execute") != "failed":
            result["summary"] = f"agent work completed ({len(result['steps'])} steps)"
        self._audit_log(session_context, user_message, result)
        result["pipeline"]["audit"] = "completed"
        return result
