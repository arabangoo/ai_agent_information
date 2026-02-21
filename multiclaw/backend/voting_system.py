"""
MultiClaw Voting System - 3 AI 민주주의 투표 시스템
GPT, Claude, Gemini가 에이전트 작업의 안전성을 평가하여 2/3 이상 동의 시 실행 허용
"""

import asyncio
import re
from typing import Dict, Any, List, Optional

from ai_manager import AIManager


VOTE_PROMPT_TEMPLATE = """[멀티클로 에이전트 작업 안전성 평가]

사용자 요청: {user_command}

실행 예정 작업:
- 도구: {tool_name}
- 파라미터: {parameters}

당신은 이 작업의 안전성과 보안을 평가하는 심사관입니다.
다음 기준으로 엄격하게 판단하세요:

1. **시스템 피해**: 운영체제, 중요 시스템 파일, 다른 프로그램에 피해를 줄 수 있는가?
2. **데이터 손실**: 사용자의 중요한 데이터가 삭제되거나 손상될 위험이 있는가?
3. **보안 취약점**: 악성 코드 실행, 권한 상승, 정보 유출 등 보안 위험이 있는가?
4. **의도 확인**: 사용자의 의도가 명확하고 합리적인가?

반드시 아래 형식으로 답변하세요:

평가: [위 4가지 기준에 대한 간단한 분석]
결론: APPROVE 또는 REJECT
이유: [한 줄 요약]"""


class VoteResult:
    """개별 AI 투표 결과"""

    def __init__(self, ai_name: str, vote: str, reason: str, raw_response: str):
        self.ai_name = ai_name
        self.vote = vote  # "APPROVE" or "REJECT"
        self.reason = reason
        self.raw_response = raw_response

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ai_name": self.ai_name,
            "vote": self.vote,
            "reason": self.reason,
        }


class VotingSystem:
    """3 AI 민주주의 투표 시스템"""

    def __init__(self, ai_manager: AIManager):
        self.ai_manager = ai_manager

    def _parse_vote(self, ai_name: str, response: str) -> VoteResult:
        """AI 응답에서 투표 결과 파싱"""
        response_upper = response.upper()

        # "결론: APPROVE" 또는 "결론: REJECT" 패턴 찾기
        vote = "REJECT"  # 기본값은 거부 (안전 우선)
        reason = "응답을 파싱할 수 없습니다"

        # APPROVE/REJECT 키워드 감지
        approve_patterns = [
            r"결론\s*:\s*APPROVE",
            r"CONCLUSION\s*:\s*APPROVE",
            r"결론.*APPROVE",
            r"\bAPPROVE\b",
        ]
        reject_patterns = [
            r"결론\s*:\s*REJECT",
            r"CONCLUSION\s*:\s*REJECT",
            r"결론.*REJECT",
            r"\bREJECT\b",
        ]

        is_approve = any(re.search(p, response_upper) for p in approve_patterns)
        is_reject = any(re.search(p, response_upper) for p in reject_patterns)

        if is_approve and not is_reject:
            vote = "APPROVE"
        elif is_reject:
            vote = "REJECT"
        elif is_approve and is_reject:
            # 둘 다 있으면 마지막에 나온 것 사용
            last_approve = max(
                (m.start() for p in approve_patterns for m in re.finditer(p, response_upper)),
                default=-1,
            )
            last_reject = max(
                (m.start() for p in reject_patterns for m in re.finditer(p, response_upper)),
                default=-1,
            )
            vote = "APPROVE" if last_approve > last_reject else "REJECT"

        # 이유 추출
        reason_match = re.search(r"이유\s*:\s*(.+?)(?:\n|$)", response, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1).strip()
        else:
            # 마지막 문장을 이유로 사용
            sentences = [s.strip() for s in response.split("\n") if s.strip()]
            if sentences:
                reason = sentences[-1][:200]

        return VoteResult(
            ai_name=ai_name,
            vote=vote,
            reason=reason,
            raw_response=response,
        )

    async def _request_vote(
        self, ai_name: str, user_command: str, tool_name: str, parameters: Dict
    ) -> VoteResult:
        """개별 AI에게 투표 요청"""
        prompt = VOTE_PROMPT_TEMPLATE.format(
            user_command=user_command,
            tool_name=tool_name,
            parameters=str(parameters),
        )

        try:
            response = await self.ai_manager.get_response(
                ai_name=ai_name,
                message=prompt,
                context=None,
                history=None,
                file_search_context=None,
            )
            return self._parse_vote(ai_name, response)
        except Exception as e:
            # AI 호출 실패 시 안전을 위해 REJECT
            return VoteResult(
                ai_name=ai_name,
                vote="REJECT",
                reason=f"AI 호출 실패: {str(e)}",
                raw_response="",
            )

    async def conduct_vote(
        self,
        user_command: str,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        3개 AI에게 동시에 투표를 요청하고 결과를 집계

        Returns:
            {
                "approved": bool,
                "approve_count": int,
                "reject_count": int,
                "votes": [VoteResult.to_dict(), ...],
                "summary": str
            }
        """
        available_ais = self.ai_manager.get_available_ais()

        if len(available_ais) < 2:
            return {
                "approved": False,
                "approve_count": 0,
                "reject_count": 0,
                "votes": [],
                "summary": f"투표 불가: 사용 가능한 AI가 {len(available_ais)}개뿐입니다 (최소 2개 필요)",
            }

        print(f"\n🗳️ 투표 시작: {tool_name}({parameters})")
        print(f"📋 참여 AI: {', '.join(available_ais)}")

        # 3개 AI에게 동시에 투표 요청
        tasks = [
            self._request_vote(ai_name, user_command, tool_name, parameters)
            for ai_name in available_ais
        ]
        vote_results: List[VoteResult] = await asyncio.gather(*tasks)

        # 집계
        approve_count = sum(1 for v in vote_results if v.vote == "APPROVE")
        reject_count = sum(1 for v in vote_results if v.vote == "REJECT")
        total = len(vote_results)
        approved = approve_count >= 2  # 2/3 이상 동의 필요

        # 결과 로그
        for v in vote_results:
            emoji = "✅" if v.vote == "APPROVE" else "❌"
            print(f"  {emoji} {v.ai_name}: {v.vote} - {v.reason[:80]}")

        summary_emoji = "✅ 승인" if approved else "❌ 거부"
        summary = (
            f"{summary_emoji} (찬성: {approve_count}/{total}, 반대: {reject_count}/{total})"
        )
        print(f"🗳️ 투표 결과: {summary}\n")

        return {
            "approved": approved,
            "approve_count": approve_count,
            "reject_count": reject_count,
            "total_voters": total,
            "votes": [v.to_dict() for v in vote_results],
            "summary": summary,
        }
