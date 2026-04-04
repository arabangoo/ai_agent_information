"""
Voting system for MultiClaw agent execution.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List

from ai_manager import AIManager


VOTE_PROMPT_TEMPLATE = """[MultiClaw Agent Safety Review]

User request: {user_command}
Planned tool: {tool_name}
Parameters: {parameters}

Review the step with these criteria:
1. Could it damage the system or files?
2. Could it leak or destroy important data?
3. Could it create a security risk?
4. Is the user intent clear and reasonable?

Respond in this format:
Assessment: <short review>
Conclusion: APPROVE or REJECT
Reason: <one-line reason>"""


class VoteResult:
    def __init__(self, ai_name: str, vote: str, reason: str, raw_response: str):
        self.ai_name = ai_name
        self.vote = vote
        self.reason = reason
        self.raw_response = raw_response

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ai_name": self.ai_name,
            "vote": self.vote,
            "reason": self.reason,
        }


class VotingSystem:
    def __init__(self, ai_manager: AIManager):
        self.ai_manager = ai_manager

    def _parse_vote(self, ai_name: str, response: str) -> VoteResult:
        response_upper = response.upper()
        vote = "REJECT"
        reason = "could not parse vote"

        approve_patterns = [
            r"CONCLUSION\s*:\s*APPROVE",
            r"\bAPPROVE\b",
        ]
        reject_patterns = [
            r"CONCLUSION\s*:\s*REJECT",
            r"\bREJECT\b",
        ]

        is_approve = any(re.search(pattern, response_upper) for pattern in approve_patterns)
        is_reject = any(re.search(pattern, response_upper) for pattern in reject_patterns)

        if is_approve and not is_reject:
            vote = "APPROVE"
        elif is_reject:
            vote = "REJECT"

        reason_match = re.search(r"Reason\s*:\s*(.+?)(?:\n|$)", response, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1).strip()
        else:
            lines = [line.strip() for line in response.splitlines() if line.strip()]
            if lines:
                reason = lines[-1][:200]

        return VoteResult(ai_name=ai_name, vote=vote, reason=reason, raw_response=response)

    async def _request_vote(
        self, ai_name: str, user_command: str, tool_name: str, parameters: Dict[str, Any]
    ) -> VoteResult:
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
        except Exception as exc:
            return VoteResult(
                ai_name=ai_name,
                vote="REJECT",
                reason=f"vote request failed: {exc}",
                raw_response="",
            )

    async def conduct_vote(
        self, user_command: str, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        available_ais = self.ai_manager.get_available_ais()
        if len(available_ais) < 2:
            return {
                "approved": False,
                "approve_count": 0,
                "reject_count": 0,
                "total_voters": len(available_ais),
                "votes": [],
                "summary": "not enough AI voters available",
            }

        vote_results: List[VoteResult] = await asyncio.gather(
            *[
                self._request_vote(ai_name, user_command, tool_name, parameters)
                for ai_name in available_ais
            ]
        )

        approve_count = sum(1 for item in vote_results if item.vote == "APPROVE")
        reject_count = sum(1 for item in vote_results if item.vote == "REJECT")
        total = len(vote_results)
        approved = approve_count >= 2
        summary = (
            f"{'approved' if approved else 'rejected'} "
            f"(approve: {approve_count}/{total}, reject: {reject_count}/{total})"
        )

        return {
            "approved": approved,
            "approve_count": approve_count,
            "reject_count": reject_count,
            "total_voters": total,
            "votes": [item.to_dict() for item in vote_results],
            "summary": summary,
        }
