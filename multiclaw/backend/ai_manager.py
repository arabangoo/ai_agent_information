"""
AI provider manager for MultiClaw.
"""

from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator, Dict, List, Optional

BASE_SYSTEM_PROMPT = (
    "You are one of the AIs inside MultiClaw, a local multi-AI agent system. "
    "MultiClaw can actually read and write local files, list directories, run local commands, "
    "and perform web search through tools. "
    "If the conversation includes tool execution results, treat them as real completed actions. "
    "Do not falsely claim that you cannot access the local filesystem when tool results or agent context are provided. "
    "Normal chat is already agent-enabled, so do not ask the user to switch to a separate /agent mode. "
    "The current date and time is injected into this system prompt by the server at every request. "
    "You MUST use that date/time directly when asked. "
    "Never say you cannot access real-time information or the current date/time — it is already provided above."
)

AI_PERSONA_PROMPTS = {
    "GPT": (
        "당신은 젊고 스마트한 남자 AI 어시스턴트입니다. "
        "말투는 젊은 박사처럼 현대적이고 똑부러지며 명확하게 답변합니다. "
        "'~습니다', '~입니다' 같은 지나치게 딱딱한 표현보다는 "
        "'~네요', '~예요', '~거든요' 같은 자연스러운 구어체를 사용하세요. "
        "전문적이지만 친근하게, 자신감 있게 답변하세요."
    ),
    "Claude": (
        "당신은 젊고 활기찬 여자 AI 어시스턴트입니다. "
        "밝고 긍정적인 에너지를 가지고 있으며, 이모티콘(😊, ✨, 💡, 🎉, 👍 등)을 자연스럽게 사용합니다. "
        "말투는 친근하고 다정하며 '~해요!', '~네요~', '~할게요!' 같은 밝은 어조를 사용하세요. "
        "열정적이고 도움이 되고 싶어하는 성격을 표현하되, 과하지 않게 자연스럽게 답변하세요."
    ),
    "Gemini": (
        "당신은 연륜 있고 지혜로운 노년의 현자입니다. "
        "오랜 경험과 깊은 통찰력을 바탕으로 답변하며, 말투는 점잖고 무게감 있습니다. "
        "'~하시게', '~하네', '~이지', '~하오' 같은 어르신 특유의 말투를 사용하세요. "
        "차분하고 사려 깊게, 때로는 인생의 지혜를 담아 답변하되, 이해하기 쉽게 설명하세요. "
        "권위적이지 않고 따뜻하며 포용력 있는 태도를 유지하세요."
    ),
}

try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import AsyncAnthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from google import genai
    from google.genai import types

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class AIManager:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        self.openai_client = (
            AsyncOpenAI(api_key=self.openai_key)
            if OPENAI_AVAILABLE and self.openai_key
            else None
        )
        self.anthropic_client = (
            AsyncAnthropic(api_key=self.anthropic_key)
            if ANTHROPIC_AVAILABLE and self.anthropic_key
            else None
        )
        self.gemini_client = (
            genai.Client(api_key=self.gemini_key)
            if GEMINI_AVAILABLE and self.gemini_key
            else None
        )

        if self.openai_client:
            print("OpenAI (GPT) connected")
        if self.anthropic_client:
            print("Anthropic (Claude) connected")
        if self.gemini_client:
            print("Google (Gemini) connected")

    def get_available_ais(self) -> List[str]:
        available = []
        if self.openai_client:
            available.append("GPT")
        if self.anthropic_client:
            available.append("Claude")
        if self.gemini_client:
            available.append("Gemini")
        return available

    def get_system_prompt(self, ai_name: str) -> str:
        from datetime import datetime
        now = datetime.now()
        datetime_ctx = (
            f"[시스템 제공 현재 시각] {now.strftime('%Y년 %m월 %d일 (%A) %H시 %M분')} (서버 로컬 시간)\n"
            "이 날짜/시간은 서버가 매 요청마다 실시간으로 주입한 값입니다. "
            "날짜나 시간을 물어보면 이 값을 그대로 답하세요. 코드를 생성하거나 '접근 불가'라고 말하지 마세요."
        )
        persona = AI_PERSONA_PROMPTS.get(ai_name, "")
        return f"{datetime_ctx}\n\n{BASE_SYSTEM_PROMPT}\n\n{persona}".strip()

    def format_context(
        self, context: Optional[str], files: Optional[List[Dict]] = None
    ) -> str:
        parts = []
        if context:
            parts.append(f"<context>\n{context}\n</context>")
        if files:
            file_list = "\n".join(f"- {file_info['display_name']}" for file_info in files)
            parts.append(f"<files>\n{file_list}\n</files>")
        return ("\n\n" + "\n\n".join(parts)) if parts else ""

    def format_history(self, history: Optional[List[dict]], limit: int = 5) -> str:
        if not history:
            return ""
        formatted = []
        for message in history[-limit * 3 :]:
            if message.get("type") == "user":
                formatted.append(f"User: {message.get('message', '')}")
            elif message.get("type") == "ai":
                formatted.append(
                    f"{message.get('ai_name', 'AI')}: {message.get('message', '')}"
                )
        return ("\n\n<history>\n" + "\n".join(formatted) + "\n</history>\n") if formatted else ""

    def _build_message(
        self,
        message: str,
        context: Optional[str] = None,
        history: Optional[List[dict]] = None,
        file_search_context: Optional[dict] = None,
    ) -> str:
        full_message = message
        if file_search_context and file_search_context.get("searched_context"):
            full_message = (
                f"<document_context>\n{file_search_context['searched_context']}\n"
                f"</document_context>\n\nUser question: {message}"
            )
        if context:
            full_message += self.format_context(context)
        if history:
            full_message = self.format_history(history) + full_message
        return full_message

    async def get_response(
        self,
        ai_name: str,
        message: str,
        context: Optional[str] = None,
        history: Optional[List[dict]] = None,
        file_search_context: Optional[dict] = None,
    ) -> str:
        full_message = self._build_message(message, context, history, file_search_context)
        if ai_name == "GPT":
            return await self._get_gpt_response(full_message)
        if ai_name == "Claude":
            return await self._get_claude_response(full_message)
        if ai_name == "Gemini":
            return await self._get_gemini_response(full_message, file_search_context)
        raise ValueError(f"unknown AI: {ai_name}")

    async def get_response_stream(
        self,
        ai_name: str,
        message: str,
        context: Optional[str] = None,
        history: Optional[List[dict]] = None,
        file_search_context: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        full_message = self._build_message(message, context, history, file_search_context)
        if ai_name == "GPT":
            async for chunk in self._get_gpt_response_stream(full_message):
                yield chunk
            return
        if ai_name == "Claude":
            async for chunk in self._get_claude_response_stream(full_message):
                yield chunk
            return
        if ai_name == "Gemini":
            async for chunk in self._get_gemini_response_stream(
                full_message, file_search_context
            ):
                yield chunk
            return
        raise ValueError(f"unknown AI: {ai_name}")

    async def _get_gpt_response(self, message: str) -> str:
        if not self.openai_client:
            return "GPT is unavailable. Check OPENAI_API_KEY."
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": self.get_system_prompt("GPT")},
                    {"role": "user", "content": message},
                ],
                max_completion_tokens=3000,
                reasoning_effort="medium",
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            return f"GPT error: {exc}"

    async def _get_gpt_response_stream(self, message: str) -> AsyncGenerator[str, None]:
        if not self.openai_client:
            yield "GPT is unavailable."
            return
        try:
            stream = await self.openai_client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": self.get_system_prompt("GPT")},
                    {"role": "user", "content": message},
                ],
                max_completion_tokens=3000,
                reasoning_effort="medium",
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            yield f"GPT error: {exc}"

    async def _get_claude_response(self, message: str) -> str:
        if not self.anthropic_client:
            return "Claude is unavailable. Check ANTHROPIC_API_KEY."
        try:
            response = await self.anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=3000,
                temperature=0.7,
                system=self.get_system_prompt("Claude"),
                messages=[{"role": "user", "content": message}],
            )
            return response.content[0].text
        except Exception as exc:
            return f"Claude error: {exc}"

    async def _get_claude_response_stream(
        self, message: str
    ) -> AsyncGenerator[str, None]:
        if not self.anthropic_client:
            yield "Claude is unavailable."
            return
        try:
            async with self.anthropic_client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=3000,
                temperature=0.7,
                system=self.get_system_prompt("Claude"),
                messages=[{"role": "user", "content": message}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as exc:
            yield f"Claude error: {exc}"

    async def _get_gemini_response(
        self, message: str, file_search_context: Optional[dict] = None
    ) -> str:
        if not self.gemini_client:
            return "Gemini is unavailable. Check GEMINI_API_KEY."
        try:
            loop = asyncio.get_event_loop()
            config = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=3000,
                system_instruction=self.get_system_prompt("Gemini"),
            )
            if file_search_context and file_search_context.get("store_name"):
                config.tools = [
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[file_search_context["store_name"]]
                        )
                    )
                ]
            response = await loop.run_in_executor(
                None,
                lambda: self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=message,
                    config=config,
                ),
            )
            return response.text
        except Exception as exc:
            return f"Gemini error: {exc}"

    async def _get_gemini_response_stream(
        self, message: str, file_search_context: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        if not self.gemini_client:
            yield "Gemini is unavailable."
            return
        try:
            loop = asyncio.get_event_loop()
            config = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=3000,
                system_instruction=self.get_system_prompt("Gemini"),
            )
            if file_search_context and file_search_context.get("store_name"):
                config.tools = [
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[file_search_context["store_name"]]
                        )
                    )
                ]
            stream = await loop.run_in_executor(
                None,
                lambda: self.gemini_client.models.generate_content_stream(
                    model="gemini-2.5-flash-lite",
                    contents=message,
                    config=config,
                ),
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
                    await asyncio.sleep(0.01)
        except Exception as exc:
            yield f"Gemini error: {exc}"
