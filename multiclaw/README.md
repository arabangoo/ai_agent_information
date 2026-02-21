# MultiClaw (멀티클로) - AI 다수결 투표 에이전트 시스템

**3개 AI가 투표로 안전성을 검증하는 AI Agent + RAG Chat 시스템**

GPT, Claude, Gemini가 동시에 답변하며, 에이전트 작업은 3개 AI의 다수결 투표(2/3 이상 동의)를 거쳐 안전하게 실행됩니다.

## 핵심 특징

- **AI 다수결 투표**: 에이전트 작업 실행 전 GPT, Claude, Gemini가 안전성을 평가하여 2/3 이상 동의 시 실행
- **멀티 AI 동시 응답**: 3개 AI가 각자의 개성 있는 말투로 동시 답변
- **AI 에이전트**: 파일 읽기/쓰기, 명령 실행, 웹 검색 등 도구 실행
- **로컬 장기 메모리**: 대화 내용을 로컬 파일에 저장하여 세션 간 기억 유지
- **Gemini File Search Store RAG**: 파일 업로드만으로 자동 청킹, 임베딩, 인덱싱
- **실시간 스트리밍**: SSE 방식으로 답변이 실시간 생성

<img width="1274" height="668" alt="image_4" src="https://github.com/user-attachments/assets/5b8c882d-b09c-4de0-8d61-98d6c9265010" />
<img width="1263" height="662" alt="image_5" src="https://github.com/user-attachments/assets/9ac9ccd2-b7ca-4283-8bfb-179ad05bb7f4" />
<img width="1000" height="600" alt="image_6" src="https://github.com/user-attachments/assets/87c6ac76-67a7-4fc7-86c3-7dac08b30209" />

## 빠른 시작

### 1. API 키 설정

```bash
# 대화형 API 키 설정
setup-env.bat
```

또는 수동으로 `backend/.env` 생성:
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIzaSy...
PERPLEXITY_API_KEY=pplx-...    # 선택 (에이전트 웹 검색용)
```

### 2. 설치

```bash
# 간단 설치 (권장)
install-simple.bat

# 또는 pip install -e . 방식
install.bat

# 또는 가상환경 사용
install-venv.bat
```

### 3. 실행

```bash
# 백엔드 + 프론트엔드 동시 실행
run-all.bat

# 가상환경 사용 시
run-all-venv.bat
```

### 4. 접속

브라우저에서 **http://localhost:5173/app/** 열기

**필수 요구사항:**
- Python 3.11+
- Node.js 18+
- Gemini API Key (필수 - AI 호출 + File Search Store)
- OpenAI API Key (GPT 호출)
- Anthropic API Key (Claude 호출)
- Perplexity API Key (선택 - 에이전트 웹 검색)

---

## 사용 방법

### 일반 채팅

메시지를 입력하면 3개 AI가 동시에 답변합니다.

```
안녕하세요!                    → 3개 AI 모두 응답
@GPT 코드 리뷰해줘             → GPT만 응답
@Claude 이 문서 요약해줘        → Claude만 응답
@Gemini 조언 좀 해줘           → Gemini만 응답
```

### 에이전트 명령 (/agent)

`/agent`로 시작하는 메시지는 에이전트 모드로 실행됩니다.

```
/agent 현재 디렉토리의 파일 목록을 보여줘
/agent README.md 파일 내용을 읽어줘
/agent 오늘 AI 뉴스를 검색해줘
```

**에이전트 실행 흐름:**
```
사용자: /agent 파일 목록 보여줘
    ↓
[1단계] AI가 작업 계획 생성 (어떤 도구를 사용할지)
    ↓
[2단계] 3개 AI가 안전성 투표 (APPROVE / REJECT)
    ↓
[3단계] 2/3 이상 동의 → 도구 실행
    ↓
[4단계] 실행 결과를 3개 AI에게 전달 → 최종 응답
```

**투표 결과 표시:**
- 초록 배지: APPROVE (승인)
- 빨간 배지: REJECT (거부)

### 사용 가능한 에이전트 도구

| 도구 | 설명 |
|------|------|
| `read_file` | 파일 내용 읽기 |
| `write_file` | 파일 생성/수정 |
| `list_files` | 디렉토리 파일 목록 조회 |
| `run_command` | 시스템 명령어 실행 (위험 명령 자동 차단) |
| `web_search` | Perplexity API 웹 검색 |

**안전 장치:**
- 위험한 명령어 (`rm -rf /`, `format c:`, `del /f` 등) 자동 차단
- 3개 AI 중 2개 이상이 거부하면 작업 미실행
- 명령 실행 30초 타임아웃
- 프로젝트 디렉토리 내에서만 실행

### 파일 업로드 (RAG)

1. 화면 상단 **프로젝트 파일 업로드** 버튼 클릭
2. PDF, DOCX, TXT 파일 선택
3. 업로드 → 자동으로 청킹, 임베딩, 인덱싱
4. 이후 채팅에서 업로드된 문서 기반 RAG 답변

### 장기 메모리

- 대화 내용이 자동으로 로컬 메모리에 저장
- 세션 간 기억 유지 (서버 재시작 후에도 유지)
- 화면 상단 **메모리** 버튼으로 저장된 메모리 확인/초기화

---

## 프로젝트 구조

```
multiclaw/
├── backend/                      # FastAPI 백엔드
│   ├── main.py                   # 메인 서버
│   ├── ai_manager.py             # 멀티 AI 통합 관리자
│   ├── file_search_manager.py    # Gemini File Search Store 관리자
│   ├── agent_executor.py         # 에이전트 실행 엔진
│   ├── agent_tools.py            # 에이전트 도구 (파일, 명령, 검색)
│   ├── voting_system.py          # 3 AI 다수결 투표 시스템
│   ├── memory_manager.py         # 로컬 장기 메모리 관리
│   ├── data/                     # 데이터 저장소
│   │   ├── memory/               # 장기 메모리
│   │   │   ├── MEMORY.md         # 핵심 메모리 요약
│   │   │   └── daily/            # 일별 대화 로그
│   │   └── file_search_metadata.json
│   └── .env                      # API 키 설정
├── frontend/                     # React + TypeScript
│   ├── src/
│   │   ├── App.tsx               # 메인 UI
│   │   └── App.css               # 스타일
│   └── public/
│       └── ai_image/             # AI 캐릭터 이미지
├── install.bat                   # 설치 스크립트
├── install-simple.bat            # 간단 설치
├── install-admin.bat             # 관리자 권한 설치
├── install-venv.bat              # 가상환경 설치
├── run-all.bat                   # 백엔드+프론트엔드 실행
├── run-all-venv.bat              # 가상환경 실행
├── run-backend.bat               # 백엔드만 실행
├── run-frontend.bat              # 프론트엔드만 실행
├── setup-env.bat                 # API 키 설정
└── Makefile                      # make 명령
```

---

## API 엔드포인트

### 채팅

```http
POST   /api/chat             # 일반 채팅 (JSON 응답)
POST   /api/chat/stream      # 스트리밍 채팅 (SSE)
```

### 에이전트

```http
POST   /api/agent            # 에이전트 명령 실행
```

요청:
```json
{
  "message": "/agent 파일 목록 보여줘",
  "session_id": "optional-session-id"
}
```

응답:
```json
{
  "approved": true,
  "steps": [
    {
      "tool": "list_files",
      "params": {"path": "."},
      "vote_result": {"approved": true, "approve_count": 3},
      "execution_result": {"success": true, "entries": [...]}
    }
  ],
  "ai_responses": {
    "GPT": "파일 목록을 확인했어요...",
    "Claude": "디렉토리 내용을 살펴봤어요!...",
    "Gemini": "파일 구조를 분석해보았네..."
  }
}
```

### 메모리

```http
GET    /api/memory            # 메모리 요약 조회
POST   /api/memory/search     # 메모리 검색
GET    /api/memory/daily      # 일별 로그 조회
DELETE /api/memory            # 메모리 초기화
```

### 파일 관리

```http
POST   /api/upload            # 파일 업로드 (File Search Store)
GET    /api/documents         # 업로드된 문서 목록
DELETE /api/documents/{id}    # 문서 삭제
DELETE /api/documents         # 모든 문서 삭제
```

### 기타

```http
GET    /api/history           # 대화 히스토리
DELETE /api/history           # 히스토리 초기화
GET    /health                # 서버 상태
```

---

## 투표 시스템 상세

### 작동 원리

에이전트 작업 실행 전, 3개 AI에게 다음 기준으로 안전성 평가를 요청합니다:

1. **시스템 피해**: 운영체제, 시스템 파일에 피해를 줄 수 있는가?
2. **데이터 손실**: 중요한 데이터 삭제/손상 위험이 있는가?
3. **보안 취약점**: 악성 코드 실행, 권한 상승, 정보 유출 위험이 있는가?
4. **의도 확인**: 사용자의 의도가 명확하고 합리적인가?

### 투표 규칙

- 3개 AI 중 **2개 이상 APPROVE** → 작업 실행
- **2개 이상 REJECT** → 작업 거부 (거부 이유 표시)
- AI 호출 실패 시 → 안전을 위해 **REJECT** 처리
- 사용 가능한 AI가 2개 미만 → 투표 불가

### 예시

```
✅ 안전한 작업 (대부분 승인):
  /agent 현재 디렉토리 파일 목록 보여줘
  /agent README.md 읽어줘
  /agent 최신 AI 뉴스 검색해줘

❌ 위험한 작업 (대부분 거부):
  /agent 시스템 파일 삭제해줘
  /agent 모든 파일을 지워줘
```

---

## AI 캐릭터

| AI | 모델 | 성격 |
|---|---|---|
| **GPT** | gpt-4o | 젊고 스마트한 남성 말투 |
| **Claude** | claude-sonnet-4 | 활기찬 여성 말투 |
| **Gemini** | gemini-2.5-flash | 지혜로운 노인 말투 |

개성 변경: [backend/ai_manager.py](backend/ai_manager.py)에서 시스템 프롬프트 수정

---

## Gemini File Search Store (RAG)

### 동작 원리

```
파일 업로드 → Gemini File Search Store에 저장
    → 자동 청킹 (문서 분할)
    → 자동 임베딩 (벡터화)
    → 인덱싱 완료

채팅 시 → Gemini가 File Search Store에서 검색
    → 추출된 컨텍스트를 GPT/Claude/Gemini 모두에게 공유
    → 각 AI가 RAG 기반 답변 생성
```

### 비용

| 항목 | 비용 |
|------|------|
| File Search Store 유지 | **무료** |
| 쿼리 시 임베딩 | **무료** |
| 초기 인덱싱 | $0.15 / 1M 토큰 |

### 지원 파일

- PDF (`.pdf`), Word (`.docx`)
- 텍스트 (`.txt`, `.json`)
- 이미지 (`.png`, `.jpg`, `.jpeg`)

---

## 장기 메모리 시스템

### 저장 구조

```
backend/data/memory/
├── MEMORY.md              # 핵심 장기 메모리 요약 (200줄 제한)
├── daily/
│   ├── 2026-02-17.md     # 일별 대화 로그
│   └── ...
└── metadata.json          # 메모리 메타데이터
```

### 기능

- 대화 내용 자동 저장 (일별 로그)
- 에이전트 실행 결과 자동 기록
- 키워드 기반 메모리 검색
- 채팅 시 메모리 컨텍스트 자동 주입
- 서버 재시작 후에도 유지

---

## 트러블슈팅

### Google GenAI SDK 버전

```bash
# File Search Store 사용 시 1.50.0 이상 필수
pip show google-genai
pip install --upgrade google-genai
```

### Gemini 모델 호환성

File Search 지원 모델만 사용:
- gemini-2.5-flash (권장)
- gemini-2.5-pro
- gemini-1.5-pro
- gemini-1.5-flash

### API 키 오류

```bash
# .env 파일에서 공백/따옴표 제거
GEMINI_API_KEY=AIzaSy...     # 올바름
GEMINI_API_KEY= AIzaSy...    # 앞에 공백 - 오류
GEMINI_API_KEY="AIzaSy..."   # 따옴표 - 오류
```

### 에러별 진단

| 에러 | 원인 | 해결 |
|------|------|------|
| `'Client' object has no attribute 'file_search_stores'` | google-genai < 1.50.0 | `pip install --upgrade google-genai` |
| `tools[0].tool_type: required one_of...` | Gemini 모델 File Search 미지원 | `gemini-2.5-flash`로 변경 |
| `INVALID_ARGUMENT` | Tool 파라미터 명명 오류 | `file_search`, `file_search_store_names` 사용 |

---

## 기술 스택

### 백엔드
- **FastAPI** (비동기 웹 서버)
- **Google Gemini API** (`google-genai>=1.50.0`) - File Search Store
- **OpenAI API** (`openai>=1.58.0`) - GPT-4o
- **Anthropic API** (`anthropic>=0.42.0`) - Claude Sonnet 4
- **Perplexity API** - 웹 검색 (에이전트)
- Python 3.11+

### 프론트엔드
- **React 18** + TypeScript
- **Vite** (빌드 도구)
- **Axios** (HTTP 클라이언트)
- **React Markdown** (마크다운 렌더링)

---

## 라이선스

Apache-2.0 license






