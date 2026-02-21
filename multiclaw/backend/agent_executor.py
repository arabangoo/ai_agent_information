"""
MultiClaw Agent Executor - 에이전트 실행 엔진
작업 분석 → 투표 → 실행 → 응답의 전체 흐름 관리
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from ai_manager import AIManager
from agent_tools import TOOL_REGISTRY, execute_tool, get_tools_description
from voting_system import VotingSystem
from memory_manager import MemoryManager


PLAN_PROMPT_TEMPLATE = """당신은 멀티클로(MultiClaw) AI 에이전트입니다.
사용자의 요청을 분석하여 어떤 도구를 사용할지 계획을 세워주세요.

사용 가능한 도구:
{tools_description}

사용자 요청: {user_message}

{memory_context}

반드시 아래 JSON 형식으로만 답변하세요 (다른 텍스트 없이):
{{
    "plan": [
        {{
            "tool": "도구이름",
            "params": {{"key": "value"}},
            "description": "이 단계에서 할 일"
        }}
    ],
    "explanation": "전체 계획 설명"
}}

도구가 필요 없는 일반 질문이면:
{{
    "plan": [],
    "explanation": "일반 대화 - 도구 사용 불필요"
}}"""


FINAL_RESPONSE_PROMPT = """당신은 멀티클로(MultiClaw) AI 에이전트입니다.
에이전트 작업이 완료되었습니다. 결과를 사용자에게 알기 쉽게 설명해주세요.

사용자 요청: {user_message}
실행된 작업과 결과:
{execution_results}

투표 정보:
{vote_summary}

결과를 한국어로 명확하고 친절하게 설명해주세요."""


class AgentExecutor:
    """멀티클로 에이전트 실행 엔진"""

    def __init__(
        self,
        ai_manager: AIManager,
        voting_system: VotingSystem,
        memory_manager: MemoryManager,
    ):
        self.ai_manager = ai_manager
        self.voting_system = voting_system
        self.memory_manager = memory_manager

    async def _create_plan(self, user_message: str) -> Dict[str, Any]:
        """AI에게 작업 계획 생성 요청"""
        memory_context = self.memory_manager.get_context_for_chat()
        if memory_context:
            memory_context = f"\n참고할 메모리:\n{memory_context}"
        else:
            memory_context = ""

        prompt = PLAN_PROMPT_TEMPLATE.format(
            tools_description=get_tools_description(),
            user_message=user_message,
            memory_context=memory_context,
        )

        # Gemini를 기본 플래너로 사용 (가장 빠르고 JSON 파싱이 좋음)
        available = self.ai_manager.get_available_ais()
        planner_ai = "Gemini" if "Gemini" in available else available[0]

        try:
            response = await self.ai_manager.get_response(
                ai_name=planner_ai,
                message=prompt,
                context=None,
                history=None,
                file_search_context=None,
            )

            # JSON 추출 (코드블록 안에 있을 수 있음)
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                plan_data = json.loads(json_match.group())
                return {
                    "success": True,
                    "plan": plan_data.get("plan", []),
                    "explanation": plan_data.get("explanation", ""),
                    "planner": planner_ai,
                }
            else:
                return {
                    "success": False,
                    "plan": [],
                    "explanation": "계획을 파싱할 수 없습니다",
                    "planner": planner_ai,
                    "raw_response": response,
                }
        except json.JSONDecodeError:
            return {
                "success": False,
                "plan": [],
                "explanation": "JSON 파싱 실패",
                "planner": planner_ai,
            }
        except Exception as e:
            return {
                "success": False,
                "plan": [],
                "explanation": f"계획 생성 실패: {str(e)}",
                "planner": planner_ai,
            }

    async def _generate_final_response(
        self,
        user_message: str,
        execution_results: List[Dict],
        vote_summaries: List[str],
    ) -> Dict[str, str]:
        """3개 AI에게 최종 응답 생성 요청"""
        results_text = ""
        for i, result in enumerate(execution_results, 1):
            results_text += f"\n[단계 {i}] {result.get('description', '')}\n"
            results_text += f"도구: {result.get('tool', '')}\n"
            results_text += f"결과: {json.dumps(result.get('result', {}), ensure_ascii=False, indent=2)[:1000]}\n"

        vote_text = "\n".join(vote_summaries) if vote_summaries else "투표 없음"

        prompt = FINAL_RESPONSE_PROMPT.format(
            user_message=user_message,
            execution_results=results_text,
            vote_summary=vote_text,
        )

        # 모든 사용 가능한 AI에게 최종 응답 요청
        available_ais = self.ai_manager.get_available_ais()
        responses = {}

        for ai_name in available_ais:
            try:
                resp = await self.ai_manager.get_response(
                    ai_name=ai_name,
                    message=prompt,
                    context=None,
                    history=None,
                    file_search_context=None,
                )
                responses[ai_name] = resp
            except Exception as e:
                responses[ai_name] = f"응답 생성 실패: {str(e)}"

        return responses

    async def execute(self, user_message: str) -> Dict[str, Any]:
        """
        에이전트 명령 실행 - 전체 흐름

        Returns:
            {
                "plan": {...},
                "steps": [{vote, execution, ...}, ...],
                "ai_responses": {"GPT": "...", "Claude": "...", "Gemini": "..."},
                "approved": bool,
                "summary": str
            }
        """
        timestamp = datetime.now()
        result = {
            "plan": None,
            "steps": [],
            "ai_responses": {},
            "approved": True,
            "summary": "",
        }

        # Step 1: 작업 계획 생성
        print(f"\n{'='*60}")
        print(f"🦀 멀티클로 에이전트 실행")
        print(f"📋 요청: {user_message}")
        print(f"{'='*60}")

        plan_result = await self._create_plan(user_message)
        result["plan"] = plan_result

        if not plan_result.get("plan"):
            # 도구 사용이 필요 없는 일반 질문
            print("💬 일반 대화 모드 (도구 사용 불필요)")
            responses = {}
            available_ais = self.ai_manager.get_available_ais()
            for ai_name in available_ais:
                try:
                    resp = await self.ai_manager.get_response(
                        ai_name=ai_name,
                        message=user_message,
                        context=None,
                        history=None,
                        file_search_context=None,
                    )
                    responses[ai_name] = resp
                except Exception as e:
                    responses[ai_name] = f"응답 실패: {str(e)}"

            result["ai_responses"] = responses
            result["summary"] = "일반 대화 - 에이전트 도구 사용 없음"
            return result

        print(f"📋 계획: {plan_result.get('explanation', '')}")
        print(f"🔧 실행할 도구: {len(plan_result['plan'])}개")

        # Step 2: 각 단계별로 투표 → 실행
        execution_results = []
        vote_summaries = []
        all_approved = True

        for i, step in enumerate(plan_result["plan"], 1):
            tool_name = step.get("tool", "")
            params = step.get("params", {})
            description = step.get("description", "")

            print(f"\n--- 단계 {i}: {description} ---")

            # 투표
            vote_result = await self.voting_system.conduct_vote(
                user_command=user_message,
                tool_name=tool_name,
                parameters=params,
            )

            step_result = {
                "step": i,
                "tool": tool_name,
                "params": params,
                "description": description,
                "vote": vote_result,
                "result": None,
            }

            vote_summaries.append(
                f"단계 {i} ({tool_name}): {vote_result['summary']}"
            )

            if vote_result["approved"]:
                # 투표 통과 → 도구 실행
                print(f"✅ 투표 통과 → 도구 실행: {tool_name}")
                tool_result = await execute_tool(tool_name, params)
                step_result["result"] = tool_result
                execution_results.append({
                    "tool": tool_name,
                    "description": description,
                    "result": tool_result,
                })
            else:
                # 투표 거부
                print(f"❌ 투표 거부 → 실행 중단: {tool_name}")
                step_result["result"] = {
                    "success": False,
                    "error": f"투표에서 거부됨: {vote_result['summary']}",
                }
                all_approved = False
                # 거부된 단계 이후는 실행하지 않음
                result["steps"].append(step_result)
                break

            result["steps"].append(step_result)

        result["approved"] = all_approved

        # Step 3: 3개 AI에게 최종 응답 생성 요청
        print("\n📝 최종 응답 생성 중...")
        result["ai_responses"] = await self._generate_final_response(
            user_message, execution_results, vote_summaries
        )

        # Step 4: 메모리에 기록
        memory_entry = (
            f"에이전트 명령: {user_message}\n"
            f"실행 결과: {'성공' if all_approved else '거부'}\n"
            f"사용된 도구: {', '.join(s['tool'] for s in plan_result['plan'])}"
        )
        self.memory_manager.save_memory(memory_entry, category="agent_execution")

        summary = f"{'✅ 작업 완료' if all_approved else '❌ 작업 거부'} ({len(result['steps'])}단계)"
        result["summary"] = summary

        print(f"\n{'='*60}")
        print(f"🦀 에이전트 실행 완료: {summary}")
        print(f"{'='*60}\n")

        return result
