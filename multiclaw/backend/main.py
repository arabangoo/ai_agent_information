"""
멀티클로 (MultiClaw) - AI 에이전트 시스템
3개 AI(GPT, Claude, Gemini) 민주주의 투표 기반 안전한 에이전트
FastAPI Backend Server
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import tempfile
import time
import asyncio
import json
from datetime import datetime
import re
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

from ai_manager import AIManager
from file_search_manager import FileSearchManager
from memory_manager import MemoryManager
from voting_system import VotingSystem
from agent_executor import AgentExecutor

app = FastAPI(title="MultiClaw - AI Agent System")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 시스템 초기화
ai_manager = AIManager()
file_search_manager = FileSearchManager()
memory_manager = MemoryManager()
voting_system = VotingSystem(ai_manager)
agent_executor = AgentExecutor(ai_manager, voting_system, memory_manager)

# 대화 히스토리 (메모리 저장 - 프로덕션에서는 DB 사용)
chat_history: List[Dict[str, Any]] = []

# Request Models
class ChatRequest(BaseModel):
    message: str
    include_context: bool = True

class AgentRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class MemorySearchRequest(BaseModel):
    query: str
    max_results: int = 10

class AIResponse(BaseModel):
    ai_name: str
    response: str
    timestamp: str
    has_context: bool = False

# ==================== 시작 시 초기화 ====================

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화"""
    print("🦀 멀티클로 (MultiClaw) 시작")
    print("🗳️ 3 AI 민주주의 투표 에이전트 시스템")

    # AI 연결 확인
    available_ais = ai_manager.get_available_ais()
    print(f"✅ 사용 가능한 AI: {', '.join(available_ais)}")
    print(f"📝 장기 메모리: {memory_manager.base_dir}")

# ==================== 헬스 체크 ====================

@app.get("/health")
async def health_check():
    """시스템 상태 확인"""
    return {
        "status": "healthy",
        "system": "MultiClaw",
        "available_ais": ai_manager.get_available_ais(),
        "uploaded_files_count": len(file_search_manager.get_uploaded_files()),
        "chat_history_count": len(chat_history),
        "memory_entries": memory_manager.metadata.get("total_entries", 0)
    }

# ==================== 파일 업로드 ====================

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    파일 업로드 및 File Search Store에 인덱싱
    """
    try:
        # 파일 검증
        allowed_extensions = {'.pdf', '.docx', '.txt', '.json', '.png', '.jpg', '.jpeg'}
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(400, f"지원하지 않는 파일 형식: {file_ext}")

        # 파일 읽기
        content = await file.read()
        file_size = len(content)

        if file_size > 100 * 1024 * 1024:  # 100MB
            raise HTTPException(400, "파일 크기는 100MB 이하여야 합니다")

        # 임시 파일 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # File Search Store에 업로드
        print(f"📤 업로드 시작: {file.filename}")
        result = await file_search_manager.upload_file(tmp_path, file.filename)

        # 임시 파일 삭제
        os.unlink(tmp_path)

        # 히스토리에 기록
        chat_history.append({
            "type": "system",
            "message": f"📎 파일 업로드: {file.filename}",
            "timestamp": datetime.now().isoformat(),
            "file_info": result
        })

        # 메모리에도 기록
        memory_manager.save_memory(
            f"파일 업로드: {file.filename} ({file_size} bytes)",
            category="file_upload"
        )

        return {
            "success": True,
            "message": "파일 업로드 완료",
            "filename": file.filename,
            "file_size": file_size,
            **result
        }

    except Exception as e:
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass
        raise HTTPException(500, f"업로드 실패: {str(e)}")

# ==================== 채팅 ====================

def parse_message(message: str) -> tuple[str, List[str]]:
    """
    메시지에서 AI 지명 파싱
    @GPT, @Claude, @Gemini

    Returns:
        (실제 메시지, 지명된 AI 리스트)
    """
    # AI 지명 패턴 찾기
    mentions = re.findall(r'@(GPT|Claude|Gemini)', message, re.IGNORECASE)

    # 지명 제거한 실제 메시지
    clean_message = re.sub(r'@(GPT|Claude|Gemini)\s*', '', message, flags=re.IGNORECASE).strip()

    # 대소문자 정규화
    mentioned_ais = [ai.upper() if ai.upper() == 'GPT' else ai.capitalize() for ai in mentions]

    return clean_message, mentioned_ais

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    채팅 요청 처리 (일반 응답) - 메모리 컨텍스트 포함
    """
    try:
        # 메시지 파싱
        clean_message, mentioned_ais = parse_message(request.message)

        # 사용자 메시지 히스토리에 추가
        user_message = {
            "type": "user",
            "message": request.message,
            "timestamp": datetime.now().isoformat()
        }
        chat_history.append(user_message)

        # 메모리에 대화 기록
        memory_manager.save_memory(f"사용자: {clean_message}", category="chat")

        # File Search 컨텍스트 가져오기
        file_search_context = None
        if request.include_context:
            file_search_context = await file_search_manager.get_context(clean_message)

        # 장기 메모리 컨텍스트
        memory_context = memory_manager.get_context_for_chat()

        # AI 응답 생성
        responses = []

        if mentioned_ais:
            # 지명된 AI만 응답
            for ai_name in mentioned_ais:
                # 메모리 컨텍스트를 메시지에 포함
                enhanced_message = clean_message
                if memory_context:
                    enhanced_message = f"{memory_context}\n\n{clean_message}"

                response = await ai_manager.get_response(
                    ai_name,
                    enhanced_message,
                    context=None,
                    history=chat_history,
                    file_search_context=file_search_context
                )
                responses.append({
                    "ai_name": ai_name,
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "has_context": file_search_context is not None
                })
        else:
            # 랜덤으로 1~3개 AI 선택
            import random
            available_ais = ai_manager.get_available_ais()
            selected_ais = random.sample(available_ais, k=random.randint(1, len(available_ais)))

            for ai_name in selected_ais:
                enhanced_message = clean_message
                if memory_context:
                    enhanced_message = f"{memory_context}\n\n{clean_message}"

                response = await ai_manager.get_response(
                    ai_name,
                    enhanced_message,
                    context=None,
                    history=chat_history,
                    file_search_context=file_search_context
                )
                responses.append({
                    "ai_name": ai_name,
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "has_context": file_search_context is not None
                })

        # 응답 히스토리에 추가
        for resp in responses:
            chat_history.append({
                "type": "ai",
                "ai_name": resp["ai_name"],
                "message": resp["response"],
                "timestamp": resp["timestamp"]
            })

        return {
            "success": True,
            "user_message": clean_message,
            "mentioned_ais": mentioned_ais,
            "responses": responses
        }

    except Exception as e:
        raise HTTPException(500, f"채팅 처리 실패: {str(e)}")

# ==================== 스트리밍 채팅 ====================

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    채팅 요청 처리 (스트리밍 응답)
    """
    async def generate():
        try:
            # 메시지 파싱
            clean_message, mentioned_ais = parse_message(request.message)

            # 사용자 메시지 히스토리에 추가
            chat_history.append({
                "type": "user",
                "message": request.message,
                "timestamp": datetime.now().isoformat()
            })

            # 메모리에 대화 기록
            memory_manager.save_memory(f"사용자: {clean_message}", category="chat")

            # File Search 컨텍스트
            file_search_context = None
            if request.include_context:
                file_search_context = await file_search_manager.get_context(clean_message)

            # 장기 메모리 컨텍스트
            memory_context = memory_manager.get_context_for_chat()

            # AI 선택
            if mentioned_ais:
                selected_ais = mentioned_ais
            else:
                import random
                available_ais = ai_manager.get_available_ais()
                selected_ais = random.sample(available_ais, k=random.randint(1, len(available_ais)))

            # 각 AI별로 스트리밍 응답
            for ai_name in selected_ais:
                yield f"data: {json.dumps({'type': 'start', 'ai_name': ai_name})}\n\n"

                enhanced_message = clean_message
                if memory_context:
                    enhanced_message = f"{memory_context}\n\n{clean_message}"

                full_response = ""
                async for chunk in ai_manager.get_response_stream(
                    ai_name,
                    enhanced_message,
                    context=None,
                    history=chat_history,
                    file_search_context=file_search_context
                ):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'ai_name': ai_name, 'text': chunk})}\n\n"

                yield f"data: {json.dumps({'type': 'done', 'ai_name': ai_name})}\n\n"

                # 히스토리에 추가
                chat_history.append({
                    "type": "ai",
                    "ai_name": ai_name,
                    "message": full_response,
                    "timestamp": datetime.now().isoformat()
                })

            yield "data: [COMPLETE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# ==================== 에이전트 (멀티클로 핵심) ====================

@app.post("/api/agent")
async def agent_execute(request: AgentRequest):
    """
    멀티클로 에이전트 명령 실행
    3개 AI가 투표하여 2/3 이상 동의 시 작업 실행
    """
    try:
        # /agent 접두사 제거
        message = request.message
        if message.startswith("/agent "):
            message = message[7:].strip()

        # 에이전트 실행
        result = await agent_executor.execute(message)

        # 히스토리에 기록
        chat_history.append({
            "type": "system",
            "message": f"🦀 에이전트 명령: {message}",
            "timestamp": datetime.now().isoformat()
        })

        # AI 응답을 히스토리에 추가
        for ai_name, resp in result.get("ai_responses", {}).items():
            chat_history.append({
                "type": "ai",
                "ai_name": ai_name,
                "message": resp,
                "timestamp": datetime.now().isoformat()
            })

        return {
            "success": True,
            "agent_result": result
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"에이전트 실행 실패: {str(e)}")

# ==================== 장기 메모리 ====================

@app.get("/api/memory")
async def get_memory():
    """장기 메모리 요약 조회"""
    return memory_manager.get_summary()

@app.post("/api/memory/search")
async def search_memory(request: MemorySearchRequest):
    """메모리 검색"""
    return memory_manager.search_memory(request.query, request.max_results)

@app.delete("/api/memory")
async def clear_memory():
    """메모리 초기화"""
    return memory_manager.clear_all()

@app.get("/api/memory/daily")
async def get_daily_memory(date: Optional[str] = None):
    """일별 메모리 로그 조회"""
    return memory_manager.get_daily_log(date)

# ==================== 대화 히스토리 ====================

@app.get("/api/history")
async def get_history():
    """대화 히스토리 조회"""
    return {
        "success": True,
        "history": chat_history,
        "count": len(chat_history)
    }

@app.delete("/api/history")
async def clear_history():
    """대화 히스토리 초기화"""
    global chat_history
    chat_history = []
    return {
        "success": True,
        "message": "대화 히스토리가 초기화되었습니다"
    }

# ==================== 문서 관리 ====================

@app.get("/api/documents")
async def list_documents():
    """업로드된 문서 목록"""
    return await file_search_manager.list_documents()

@app.delete("/api/documents/{document_id:path}")
async def delete_document(document_id: str):
    """문서 삭제"""
    return await file_search_manager.delete_document(document_id)

@app.delete("/api/documents")
async def clear_all_documents():
    """모든 문서 삭제"""
    return await file_search_manager.clear_all_documents()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
