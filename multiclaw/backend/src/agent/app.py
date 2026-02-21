# mypy: disable - error - code = "no-untyped-def,misc"
import pathlib
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles

# Define the FastAPI app
app = FastAPI()


def create_frontend_router(build_dir="../frontend/dist"):
    """Creates a router to serve the React frontend.

    Args:
        build_dir: Path to the React build directory relative to this file.

    Returns:
        A Starlette application serving the frontend.
    """
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        print(
            f"WARN: Frontend build directory not found or incomplete at {build_path}. Serving frontend will likely fail."
        )
        # Return a dummy router if build isn't ready
        from starlette.routing import Route

        async def dummy_frontend(request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )

        return Route("/{path:path}", endpoint=dummy_frontend)

    return StaticFiles(directory=build_path, html=True)


# Mount the frontend under /app to not conflict with the LangGraph API routes
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)


# CORS 설정 추가
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Perplexity + Gemini API
from agent.graph import graph
from langchain_core.messages import HumanMessage
from fastapi import HTTPException, Form, File, UploadFile
from pydantic import BaseModel
from typing import Optional
import uuid
import sys
import os

# utils 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.images import image_to_base64, validate_image_file


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[str]
    related_questions: list[str]
    iterations: int
    session_id: str


@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "service": "Perplexity + Gemini Research",
        "memory": "volatile (in-memory only)",
        "status": "running"
    }


@app.post("/api/research", response_model=QueryResponse)
async def research(
    query: str = Form(...),
    session_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    멀티모달 리서치 요청 처리
    - 텍스트 + 이미지 입력 지원
    - Perplexity로 검색
    - Gemini로 분석
    - 세션 내에서 대화 기억
    """
    try:
        session_id = session_id or str(uuid.uuid4())
        
        # 이미지 처리
        image_base64 = None
        if file and validate_image_file(file):
            image_base64 = await image_to_base64(file)
            print(f"📸 이미지 업로드됨: {file.filename}")
        
        print(f"\n{'='*60}")
        print(f"📥 질문: {query}")
        if image_base64:
            print(f"📸 이미지: 포함됨 (Base64 길이: {len(image_base64)})")
        print(f"🔑 Session: {session_id[:8]}...")
        print(f"{'='*60}")
        
        # config에 thread_id 전달
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        
        # 초기 상태 (이미지 추가)
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "image": image_base64,
            "search_results": [],
            "citations": [],
            "related_questions": [],
            "analysis": "",
            "final_answer": "",
            "iteration": 0,
            "needs_more_research": False
        }
        
        # 그래프 실행 (직접 호출)
        result = await graph.ainvoke(initial_state, config)
        
        print(f"\n{'='*60}")
        print(f"✅ 완료!")
        print(f"📊 결과: {result.get('final_answer', 'No answer')[:100]}...")
        print(f"{'='*60}\n")
        
        return QueryResponse(
            answer=result.get("final_answer", "답변을 생성할 수 없습니다. 다시 시도해주세요."),
            citations=list(set(result.get("citations", [])))[:10],
            related_questions=result.get("related_questions", [])[:5],
            iterations=result.get("iteration", 0),
            session_id=session_id
        )
        
    except Exception as e:
        print(f"\n❌ 오류: {str(e)}\n")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    """서버 상태 확인"""
    return {"status": "healthy"}
