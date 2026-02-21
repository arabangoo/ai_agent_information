"""
AI Manager - 멀티 AI 통합 관리
GPT, Claude, Gemini API 통합
"""

import os
from typing import List, Optional, AsyncGenerator, Dict
import asyncio

# OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Anthropic
try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Google Gemini
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class AIManager:
    """멀티 AI 관리자"""
    
    def __init__(self):
        # API 키 로드
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        
        # 클라이언트 초기화
        self.openai_client = None
        self.anthropic_client = None
        self.gemini_client = None
        
        if OPENAI_AVAILABLE and self.openai_key:
            self.openai_client = AsyncOpenAI(api_key=self.openai_key)
            print("✅ OpenAI (GPT) 연결 완료")
        
        if ANTHROPIC_AVAILABLE and self.anthropic_key:
            self.anthropic_client = AsyncAnthropic(api_key=self.anthropic_key)
            print("✅ Anthropic (Claude) 연결 완료")
        
        if GEMINI_AVAILABLE and self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)
            print("✅ Google (Gemini) 연결 완료")
    
    def get_available_ais(self) -> List[str]:
        """사용 가능한 AI 목록"""
        available = []
        if self.openai_client:
            available.append("GPT")
        if self.anthropic_client:
            available.append("Claude")
        if self.gemini_client:
            available.append("Gemini")
        return available
    
    def format_context(self, context: Optional[str], files: Optional[List[Dict]] = None) -> str:
        """컨텍스트 포맷팅"""
        parts = []
        
        if context:
            parts.append(f"<업로드된 파일 정보>\n{context}\n</업로드된 파일 정보>")
        
        if files:
            file_list = "\n".join([f"- {f['display_name']}" for f in files])
            parts.append(f"<참고 파일 목록>\n{file_list}\n</참고 파일 목록>")
        
        if parts:
            return "\n\n" + "\n\n".join(parts) + "\n\n위 정보를 참고하여 답변해주세요."
        
        return ""
    
    def format_history(self, history: List[dict], limit: int = 5) -> str:
        """대화 히스토리 포맷팅"""
        if not history:
            return ""
        
        recent_history = history[-limit*3:]  # 최근 N개 대화
        formatted = []
        
        for msg in recent_history:
            if msg["type"] == "user":
                formatted.append(f"User: {msg['message']}")
            elif msg["type"] == "ai":
                formatted.append(f"{msg['ai_name']}: {msg['message']}")
        
        if formatted:
            return "\n\n<이전 대화>\n" + "\n".join(formatted) + "\n</이전 대화>\n"
        return ""
    
    async def get_response(
        self,
        ai_name: str,
        message: str,
        context: Optional[str] = None,
        history: Optional[List[dict]] = None,
        file_search_context: Optional[dict] = None
    ) -> str:
        """AI 응답 생성"""

        # 프롬프트 구성
        full_message = message

        # RAG 컨텍스트 추가 (Gemini가 검색한 결과)
        if file_search_context and file_search_context.get("searched_context"):
            rag_context = file_search_context["searched_context"]
            full_message = f"""<참고 문서 내용>
{rag_context}
</참고 문서 내용>

사용자 질문: {message}

**중요 지침:**
- 위 문서 내용은 참고용입니다. 사용자의 질문이 문서 내용과 관련이 있을 때만 활용하세요.
- 질문이 일반적인 내용(인사, 날씨, 일상 대화 등)이라면 문서 내용을 무시하고 자연스럽게 답변하세요.
- 사용자가 명시적으로 "문서에서", "파일에서", "업로드한 자료에서" 등의 표현을 사용하거나, 문서 내용과 명확히 관련된 질문일 때만 문서를 참조하세요.
- 문서를 참조할 때는 출처를 명시해주세요."""

        if context:
            full_message += self.format_context(context)
        if history:
            full_message = self.format_history(history) + full_message

        if ai_name == "GPT":
            return await self._get_gpt_response(full_message)
        elif ai_name == "Claude":
            return await self._get_claude_response(full_message)
        elif ai_name == "Gemini":
            return await self._get_gemini_response(full_message, file_search_context)
        else:
            raise ValueError(f"알 수 없는 AI: {ai_name}")
    
    async def get_response_stream(
        self,
        ai_name: str,
        message: str,
        context: Optional[str] = None,
        history: Optional[List[dict]] = None,
        file_search_context: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        """AI 응답 스트리밍"""

        # 프롬프트 구성
        full_message = message

        # RAG 컨텍스트 추가 (Gemini가 검색한 결과)
        if file_search_context and file_search_context.get("searched_context"):
            rag_context = file_search_context["searched_context"]
            full_message = f"""<참고 문서 내용>
{rag_context}
</참고 문서 내용>

사용자 질문: {message}

**중요 지침:**
- 위 문서 내용은 참고용입니다. 사용자의 질문이 문서 내용과 관련이 있을 때만 활용하세요.
- 질문이 일반적인 내용(인사, 날씨, 일상 대화 등)이라면 문서 내용을 무시하고 자연스럽게 답변하세요.
- 사용자가 명시적으로 "문서에서", "파일에서", "업로드한 자료에서" 등의 표현을 사용하거나, 문서 내용과 명확히 관련된 질문일 때만 문서를 참조하세요.
- 문서를 참조할 때는 출처를 명시해주세요."""

        if context:
            full_message += self.format_context(context)
        if history:
            full_message = self.format_history(history) + full_message

        if ai_name == "GPT":
            async for chunk in self._get_gpt_response_stream(full_message):
                yield chunk
        elif ai_name == "Claude":
            async for chunk in self._get_claude_response_stream(full_message):
                yield chunk
        elif ai_name == "Gemini":
            async for chunk in self._get_gemini_response_stream(full_message, file_search_context):
                yield chunk
    
    # ==================== GPT ====================
    
    async def _get_gpt_response(self, message: str) -> str:
        """GPT 응답 (일반)"""
        if not self.openai_client:
            return "GPT를 사용할 수 없습니다. API 키를 확인해주세요."

        max_retries = 3
        retry_delay = 2  # 초

        for attempt in range(max_retries):
            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "당신은 젊고 스마트한 남자 AI 어시스턴트입니다. 말투는 젊은 박사처럼 현대적이고 똑부러지며 명확하게 답변합니다. '~습니다', '~입니다' 같은 딱딱한 표현보다는 '~네요', '~예요', '~거든요' 같은 자연스러운 구어체를 사용하세요. 전문적이지만 친근하게, 자신감 있게 답변하세요."},
                        {"role": "user", "content": message}
                    ],
                    temperature=0.7,
                    max_tokens=3000
                )
                return response.choices[0].message.content
            except Exception as e:
                error_msg = str(e)
                # Rate limit, timeout, 서버 오류 등에 대해 재시도
                if any(keyword in error_msg.lower() for keyword in ["rate_limit", "timeout", "503", "502", "500", "overloaded"]):
                    if attempt < max_retries - 1:
                        print(f"⚠️ GPT API 오류, {retry_delay}초 후 재시도 ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 지수 백오프
                        continue
                return f"GPT 오류: {error_msg}"

        return "GPT가 현재 응답할 수 없습니다. 잠시 후 다시 시도해주세요."
    
    async def _get_gpt_response_stream(self, message: str) -> AsyncGenerator[str, None]:
        """GPT 응답 (스트리밍)"""
        if not self.openai_client:
            yield "GPT를 사용할 수 없습니다."
            return

        max_retries = 3
        retry_delay = 2  # 초

        for attempt in range(max_retries):
            try:
                stream = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "당신은 젊고 스마트한 남자 AI 어시스턴트입니다. 말투는 젊은 박사처럼 현대적이고 똑부러지며 명확하게 답변합니다. '~습니다', '~입니다' 같은 딱딱한 표현보다는 '~네요', '~예요', '~거든요' 같은 자연스러운 구어체를 사용하세요. 전문적이지만 친근하게, 자신감 있게 답변하세요."},
                        {"role": "user", "content": message}
                    ],
                    temperature=0.7,
                    max_tokens=3000,
                    stream=True
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return  # 성공 시 종료
            except Exception as e:
                error_msg = str(e)
                if any(keyword in error_msg.lower() for keyword in ["rate_limit", "timeout", "503", "502", "500", "overloaded"]):
                    if attempt < max_retries - 1:
                        print(f"⚠️ GPT API 오류, {retry_delay}초 후 재시도 ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 지수 백오프
                        continue
                yield f"GPT 오류: {error_msg}"
                return

        yield "GPT가 현재 응답할 수 없습니다. 잠시 후 다시 시도해주세요."
    
    # ==================== Claude ====================
    
    async def _get_claude_response(self, message: str) -> str:
        """Claude 응답 (일반)"""
        if not self.anthropic_client:
            return "Claude를 사용할 수 없습니다. API 키를 확인해주세요."

        max_retries = 3
        retry_delay = 2  # 초

        for attempt in range(max_retries):
            try:
                response = await self.anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=3000,
                    temperature=0.7,
                    system="당신은 젊고 활기찬 여자 AI 어시스턴트입니다. 밝고 긍정적인 에너지를 가지고 있으며, 이모티콘(😊, ✨, 💡, 🎉, 👍 등)을 자연스럽게 사용합니다. 말투는 친근하고 다정하며 '~해요!', '~네요~', '~할게요!' 같은 밝은 어조를 사용하세요. 열정적이고 도움이 되고 싶어하는 성격을 표현하되, 과하지 않게 자연스럽게 답변하세요.",
                    messages=[
                        {"role": "user", "content": message}
                    ]
                )
                return response.content[0].text
            except Exception as e:
                error_msg = str(e)
                # 529 Overloaded 에러 또는 rate limit 에러인 경우 재시도
                if "529" in error_msg or "overloaded" in error_msg.lower() or "rate_limit" in error_msg.lower():
                    if attempt < max_retries - 1:
                        print(f"⚠️ Claude API 과부하, {retry_delay}초 후 재시도 ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 지수 백오프
                        continue
                return f"Claude 오류: {error_msg}"

        return "Claude가 현재 과부하 상태입니다. 잠시 후 다시 시도해주세요. 😊"
    
    async def _get_claude_response_stream(self, message: str) -> AsyncGenerator[str, None]:
        """Claude 응답 (스트리밍)"""
        if not self.anthropic_client:
            yield "Claude를 사용할 수 없습니다."
            return

        max_retries = 3
        retry_delay = 2  # 초

        for attempt in range(max_retries):
            try:
                async with self.anthropic_client.messages.stream(
                    model="claude-sonnet-4-20250514",
                    max_tokens=3000,
                    temperature=0.7,
                    system="당신은 젊고 활기찬 여자 AI 어시스턴트입니다. 밝고 긍정적인 에너지를 가지고 있으며, 이모티콘(😊, ✨, 💡, 🎉, 👍 등)을 자연스럽게 사용합니다. 말투는 친근하고 다정하며 '~해요!', '~네요~', '~할게요!' 같은 밝은 어조를 사용하세요. 열정적이고 도움이 되고 싶어하는 성격을 표현하되, 과하지 않게 자연스럽게 답변하세요.",
                    messages=[
                        {"role": "user", "content": message}
                    ]
                ) as stream:
                    async for text in stream.text_stream:
                        yield text
                return  # 성공 시 종료
            except Exception as e:
                error_msg = str(e)
                # 529 Overloaded 에러 또는 rate limit 에러인 경우 재시도
                if "529" in error_msg or "overloaded" in error_msg.lower() or "rate_limit" in error_msg.lower():
                    if attempt < max_retries - 1:
                        print(f"⚠️ Claude API 과부하, {retry_delay}초 후 재시도 ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 지수 백오프
                        continue
                yield f"Claude 오류: {error_msg}"
                return

        yield "Claude가 현재 과부하 상태입니다. 잠시 후 다시 시도해주세요. 😊"
    
    # ==================== Gemini ====================

    async def _get_gemini_response(self, message: str, file_search_context: Optional[dict] = None) -> str:
        """Gemini 응답 (일반) - File Search Store 지원"""
        if not self.gemini_client:
            return "Gemini를 사용할 수 없습니다. API 키를 확인해주세요."

        max_retries = 3
        retry_delay = 2  # 초

        for attempt in range(max_retries):
            try:
                loop = asyncio.get_event_loop()

                # Gemini 시스템 프롬프트 추가
                system_instruction = "당신은 연륜 있고 지혜로운 노년의 현자입니다. 오랜 경험과 깊은 통찰력을 바탕으로 답변하며, 말투는 점잖고 무게감 있습니다. '~하시게', '~하네', '~이지', '~하오' 같은 어르신 특유의 말투를 사용하세요. 차분하고 사려 깊게, 때로는 인생의 지혜를 담아 답변하되, 이해하기 쉽게 설명하세요. 권위적이지 않고 따뜻하며 포용력 있는 태도를 유지하세요."

                # File Search Store 활용 여부 판단
                if file_search_context and file_search_context.get("store_name"):
                    store_name = file_search_context["store_name"]
                    print(f"🔍 File Search Store 사용: {store_name}")

                    # File Search Tool 설정
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.gemini_client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=message,
                            config=types.GenerateContentConfig(
                                temperature=0.7,
                                max_output_tokens=3000,
                                system_instruction=system_instruction,
                                tools=[
                                    types.Tool(
                                        file_search=types.FileSearch(
                                            file_search_store_names=[store_name]
                                        )
                                    )
                                ]
                            )
                        )
                    )
                else:
                    # File Search 미사용 (일반 모드)
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.gemini_client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=message,
                            config=types.GenerateContentConfig(
                                temperature=0.7,
                                max_output_tokens=3000,
                                system_instruction=system_instruction
                            )
                        )
                    )

                return response.text
            except Exception as e:
                error_msg = str(e)
                # Rate limit, quota, 서버 오류 등에 대해 재시도
                if any(keyword in error_msg.lower() for keyword in ["rate_limit", "quota", "timeout", "503", "502", "500", "429", "resource_exhausted"]):
                    if attempt < max_retries - 1:
                        print(f"⚠️ Gemini API 오류, {retry_delay}초 후 재시도 ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 지수 백오프
                        continue
                return f"Gemini 오류: {error_msg}"

        return "Gemini가 현재 응답할 수 없습니다. 잠시 후 다시 시도해주세요."
    
    async def _get_gemini_response_stream(self, message: str, file_search_context: Optional[dict] = None) -> AsyncGenerator[str, None]:
        """Gemini 응답 (스트리밍) - File Search Store 지원"""
        if not self.gemini_client:
            yield "Gemini를 사용할 수 없습니다."
            return

        max_retries = 3
        retry_delay = 2  # 초

        for attempt in range(max_retries):
            try:
                loop = asyncio.get_event_loop()

                # Gemini 시스템 프롬프트 추가
                system_instruction = "당신은 연륜 있고 지혜로운 노년의 현자입니다. 오랜 경험과 깊은 통찰력을 바탕으로 답변하며, 말투는 점잖고 무게감 있습니다. '~하시게', '~하네', '~이지', '~하오' 같은 어르신 특유의 말투를 사용하세요. 차분하고 사려 깊게, 때로는 인생의 지혜를 담아 답변하되, 이해하기 쉽게 설명하세요. 권위적이지 않고 따뜻하며 포용력 있는 태도를 유지하세요."

                # File Search Store 활용 여부 판단
                if file_search_context and file_search_context.get("store_name"):
                    store_name = file_search_context["store_name"]
                    print(f"🔍 File Search Store 사용 (스트리밍): {store_name}")

                    # File Search Tool 설정
                    stream = await loop.run_in_executor(
                        None,
                        lambda: self.gemini_client.models.generate_content_stream(
                            model="gemini-2.5-flash",
                            contents=message,
                            config=types.GenerateContentConfig(
                                temperature=0.7,
                                max_output_tokens=3000,
                                system_instruction=system_instruction,
                                tools=[
                                    types.Tool(
                                        file_search=types.FileSearch(
                                            file_search_store_names=[store_name]
                                        )
                                    )
                                ]
                            )
                        )
                    )
                else:
                    # File Search 미사용 (일반 모드)
                    stream = await loop.run_in_executor(
                        None,
                        lambda: self.gemini_client.models.generate_content_stream(
                            model="gemini-2.5-flash",
                            contents=message,
                            config=types.GenerateContentConfig(
                                temperature=0.7,
                                max_output_tokens=3000,
                                system_instruction=system_instruction
                            )
                        )
                    )

                for chunk in stream:
                    if chunk.text:
                        yield chunk.text
                        await asyncio.sleep(0.01)
                return  # 성공 시 종료
            except Exception as e:
                error_msg = str(e)
                # Rate limit, quota, 서버 오류 등에 대해 재시도
                if any(keyword in error_msg.lower() for keyword in ["rate_limit", "quota", "timeout", "503", "502", "500", "429", "resource_exhausted"]):
                    if attempt < max_retries - 1:
                        print(f"⚠️ Gemini API 오류, {retry_delay}초 후 재시도 ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # 지수 백오프
                        continue
                yield f"Gemini 오류: {error_msg}"
                return

        yield "Gemini가 현재 응답할 수 없습니다. 잠시 후 다시 시도해주세요."
