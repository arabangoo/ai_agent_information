# MultiClaw (멀티클로) - AI 다수결 투표 에이전트 시스템

**3개 AI가 투표로 안전성을 검증하는 AI Agent + RAG Chat 시스템**

GPT, Claude, Gemini가 동시에 답변하며, 파괴적 에이전트 작업은 3개 AI의 다수결 투표(2/3 이상 동의)를 거쳐 안전하게 실행됩니다.

## 핵심 특징

- **AI 다수결 투표**: 파일 쓰기·명령 실행·프로세스 종료 등 파괴적 작업 전 GPT, Claude, Gemini가 안전성을 평가하여 2/3 이상 동의 시 실행
- **멀티 AI 동시 응답**: 3개 AI가 각자의 개성 있는 말투로 동시 답변
- **항시 활성화 에이전트 모드**: 별도의 `/agent` 접두사 없이도 모든 대화가 기본적으로 에이전트 파이프라인(계획 → 검증 → 투표(필요시) → 실행 → 최종 응답) 안에서 처리
- **21종 내장 시스템 도구**: 파일 읽기/쓰기, 명령 실행, 시스템 정보, 프로세스 목록, 클립보드, 네트워크, Python 실행, git, 웹 검색 등
- **MCP Tool Manager**: MCP(Model Context Protocol) 서버를 동적으로 등록하여 에이전트 도구를 무제한 확장
- **로컬 시스템 파일 접근**: Windows 절대 경로를 포함한 로컬 파일 시스템 읽기/쓰기/목록 조회 가능
- **로컬 장기 메모리**: 대화 내용을 로컬 파일에 저장하여 세션 간 기억 유지
- **세션별 메모리/히스토리 분리**: 세션 ID별로 대화 기록, 장기 메모리, 에이전트 감사 로그를 분리 저장
- **Gemini File Search Store RAG**: 파일 업로드만으로 자동 청킹, 임베딩, 인덱싱
- **실행 중단 가능**: 프론트의 `Stop` 버튼과 백엔드 취소 API를 통해 진행 중인 작업을 중간에 중단 가능
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

`install.bat`, `install-simple.bat`, `install-admin.bat`, `install-venv.bat`는 Playwright Chromium 브라우저까지 함께 설치합니다.
수동으로 별도 설치해야 하는 경우에만 아래 명령 사용:
```bash
python -m playwright install chromium
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

---

## 사용 방법

### 일반 채팅

메시지를 입력하면 3개 AI가 동시에 답변합니다.
또한 현재 버전의 MultiClaw는 **일반 채팅 자체가 항상 에이전트 상태**입니다.
즉, 사용자가 단순 질문을 하든 로컬 파일 작업을 지시하든, 시스템은 내부적으로 아래 흐름을 자동 판단합니다.

- 일반 설명만 필요한 경우: 3개 AI가 일반 답변 생성
- 파일/폴더/경로/명령/검색 요청이 포함된 경우: 에이전트 계획 수립 후 도구 실행 (파괴적 작업은 다수결 투표 후 실행)
- 사용자가 특정 AI만 지목한 경우(`@GPT`, `@Claude`, `@Gemini`): 최종 응답 표시 대상을 해당 AI로 제한 가능

즉, **사용자는 별도 모드를 기억할 필요 없이 그냥 자연어로 지시하면 됩니다.**

```
안녕하세요!                    → 3개 AI 모두 응답
@GPT 코드 리뷰해줘             → GPT만 응답
@Claude 이 문서 요약해줘        → Claude만 응답
@Gemini 조언 좀 해줘           → Gemini만 응답
C:\work\test.txt 파일 만들어줘   → 에이전트 계획 → 투표 → 실제 파일 생성
현재 CPU/메모리 사용량 보여줘    → 에이전트 계획 → 즉시 실행 (투표 불필요)
```

**에이전트 실행 흐름:**
```
사용자: 파일 목록 보여줘
    ↓
[1단계] AI가 작업 계획 생성 (어떤 도구를 사용할지)
    ↓
[2단계] 파괴적 도구인 경우에만 3개 AI 안전성 투표 (APPROVE / REJECT)
    │    조회/분석 도구는 자동 승인 (투표 생략)
    ↓
[3단계] 도구 실행
    ↓
[4단계] 실행 결과를 3개 AI에게 전달 → 최종 응답
```

### 사용 가능한 에이전트 도구

#### 시스템 정보 (자동 승인 - 투표 불필요)

| 도구 | 설명 |
|------|------|
| `get_datetime` | 현재 날짜/시간/요일 즉시 반환 |
| `get_system_info` | OS, CPU 사용률, RAM, 디스크, 호스트명 |
| `get_network_info` | 네트워크 인터페이스, IP, 송수신 통계 |
| `get_env` | 환경 변수 조회 (민감 키 자동 필터) |
| `list_processes` | 실행 중인 프로세스 목록 |
| `get_clipboard` | 클립보드 내용 읽기 |

#### 파일 시스템 (자동 승인 - 투표 불필요)

| 도구 | 설명 |
|------|------|
| `read_file` | 파일 내용 읽기 |
| `list_files` | 디렉토리 파일 목록 조회 |
| `open_file` | 파일/폴더/URL을 기본 프로그램으로 열기 |

#### 웹 (자동 승인 - 투표 불필요)

| 도구 | 설명 |
|------|------|
| `web_search` | Python 기반 실시간 웹 검색 (`ddgs`) |
| `fetch_url` | 웹 페이지 URL 직접 읽기 |
| `browser_extract` | Playwright로 동적 웹 페이지 렌더링 후 본문 추출 |
| `browser_collect_links` | Playwright로 페이지 링크 수집 |
| `browser_screenshot` | Playwright로 페이지 스크린샷 저장 |

#### 코드/명령 실행 (자동 승인 - 투표 불필요)

| 도구 | 설명 |
|------|------|
| `run_python` | Python 코드 실행 및 결과 반환 |

#### 파괴적/위험 작업 (3 AI 다수결 투표 필요)

| 도구 | 설명 |
|------|------|
| `write_file` | 파일 생성/수정 |
| `run_command` | 시스템 명령어 실행 (위험 명령 자동 차단) |
| `kill_process` | 프로세스 강제 종료 |
| `git_run` | git 명령 실행 (위험 명령 자동 차단) |

#### 기타 (자동 승인 - 투표 불필요)

| 도구 | 설명 |
|------|------|
| `set_clipboard` | 텍스트를 클립보드에 복사 |

`web_search`는 별도 Perplexity API Key 없이 동작하며, Python 검색 결과를 가져온 뒤 MultiClaw의 GPT, Claude, Gemini가 그 결과를 바탕으로 최종 응답을 합성합니다.
최신 정보, 오늘 뉴스, 최근 변경사항처럼 실시간성이 필요한 요청은 시스템이 자동으로 웹 검색 단계를 우선 계획하도록 보강되어 있습니다.

**안전 장치:**
- 위험한 명령어 (`rm -rf /`, `format c:`, `del /f` 등) 자동 차단
- `git_run`: `push --force`, `reset --hard`, `clean -f` 등 파괴적 git 명령 자동 차단
- 파괴적 도구는 3개 AI 중 2개 이상이 거부하면 미실행
- 명령 실행 30초 타임아웃
- `get_env`: KEY, SECRET, PASSWORD, TOKEN 등 민감 환경 변수 자동 필터

### MCP Tool Manager

MCP(Model Context Protocol) 서버를 등록하면 에이전트가 사용하는 도구로 자동 통합됩니다.

**등록 방법:**
1. 화면 상단 **Tool Manager** 버튼 클릭
2. 서버 이름, 실행 명령(npx, node 등), 인수 입력 후 **Register**
3. 등록 즉시 에이전트 도구로 활성화

**MCP 도구 명명 규칙:**
- 등록된 도구는 `서버이름__도구이름` 형식으로 자동 등록됩니다 (예: `playwright__browser_navigate`)
- 에이전트 계획 단계에서 일반 도구와 동일하게 사용됩니다

**예시 (Playwright MCP):**
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

MCP 서버 설정은 `tool_manager_config.json`에 저장되며, 서버 재시작 시 자동으로 로드됩니다.

### 실행 중단 / 취소

- 프론트 입력 영역에 **Stop** 버튼이 존재합니다.
- 사용자가 Stop을 누르면 브라우저 요청이 먼저 중단됩니다.
- 동시에 백엔드의 현재 세션 작업에 대해 취소 요청이 전송됩니다.
- 백엔드에서는 계획/투표/실행/최종 응답 단계 사이마다 취소 여부를 확인합니다.
- `run_command`가 실행 중인 경우에는 하위 subprocess도 종료합니다.

즉, 단순히 "화면만 멈추는 버튼"이 아니라, **실제로 서버 쪽 작업을 취소하는 중단 기능**입니다.

### 파일 업로드 (RAG)

1. 화면 상단 **프로젝트 파일 업로드** 버튼 클릭
2. PDF, DOCX, TXT 파일 선택
3. 업로드 → 자동으로 청킹, 임베딩, 인덱싱
4. 이후 채팅에서 업로드된 문서 기반 RAG 답변

**현재 File Search Store 동작 방식:**
- 업로드된 문서는 Google Gemini의 **File Search Store**에 저장됩니다.
- 이 스토어는 현재 설정된 `GEMINI_API_KEY` 기준으로 생성/조회/삭제됩니다.
- 업로드, 검색, 삭제 모두 해당 Gemini 키의 사용량과 연결됩니다.
- 로컬에는 문서 메타데이터와 스토어 참조 정보만 유지하고, RAG 검색은 Gemini File Search Store에서 수행합니다.

### 장기 메모리

- 대화 내용이 자동으로 로컬 메모리에 저장
- 세션 간 기억 유지 (서버 재시작 후에도 유지)
- 화면 상단 **메모리** 버튼으로 저장된 메모리 확인/초기화

**세션 분리:**
- 장기 메모리와 히스토리가 세션 단위로 분리됩니다.
- 프론트 상단의 Session 입력창에서 세션 ID를 바꿀 수 있습니다.
- 세션을 바꾸면 해당 세션의 대화 기록, 메모리, 에이전트 감사 로그가 별도로 관리됩니다.
- 브라우저 새로고침 이후에도 마지막 세션 ID는 `localStorage`에 유지됩니다.

---

## 프로젝트 구조

```
multiclaw/
├── backend/                      # FastAPI 백엔드
│   ├── main.py                   # 메인 서버
│   ├── ai_manager.py             # 멀티 AI 통합 관리자
│   ├── agent_executor.py         # 에이전트 실행 엔진 (계획 → 투표 → 실행)
│   ├── agent_tools.py            # 21종 내장 에이전트 도구
│   ├── voting_system.py          # 3 AI 다수결 투표 시스템
│   ├── tool_policy.py            # 도구 실행 정책 (위험 명령 차단 등)
│   ├── tool_registry.py          # 확장형 도구 레지스트리
│   ├── mcp_tool_wrapper.py       # MCP 도구를 에이전트 도구로 래핑
│   ├── mcp_runtime_service.py    # MCP 서버 실행/호출 관리
│   ├── tool_manager_service.py   # Tool Manager 설정 관리
│   ├── tool_manager_models.py    # Tool Manager Pydantic 모델
│   ├── mcp_bridge/               # Node.js MCP 프로토콜 브리지
│   │   ├── mcp_bridge.mjs        # MCP stdio/HTTP 브리지
│   │   └── package.json
│   ├── file_search_manager.py    # Gemini File Search Store 관리자
│   ├── memory_manager.py         # 로컬 장기 메모리 관리
│   ├── session_context.py        # 세션 컨텍스트/히스토리 관리
│   ├── cancellation_manager.py   # 실행 중단/취소 관리
│   ├── runtime_config.py         # 런타임 공통 설정
│   ├── stream_events.py          # 스트리밍 이벤트 포맷
│   ├── data/                     # 데이터 저장소
│   │   ├── memory/
│   │   │   └── sessions/
│   │   │       └── {session_id}/
│   │   │           ├── MEMORY.md
│   │   │           ├── daily/
│   │   │           └── metadata.json
│   │   └── file_search_metadata.json
│   └── .env                      # API 키 설정
├── frontend/                     # React + TypeScript
│   ├── src/
│   │   ├── App.tsx               # 메인 UI
│   │   ├── App.css               # 스타일
│   │   └── components/           # 보조 UI 컴포넌트
│   └── public/
│       └── ai_image/             # AI 캐릭터 이미지
├── tool_manager_config.json      # MCP 서버 설정
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
POST   /api/chat             # 항시 에이전트 모드 채팅 (JSON 응답)
POST   /api/chat/stream      # 스트리밍 채팅 (SSE)
POST   /api/chat/cancel      # 현재 세션의 실행 중 작업 중단 요청
```

현재 `/api/chat`은 단순 LLM 응답 엔드포인트가 아니라,
**항상 에이전트 파이프라인을 통과하는 기본 대화 엔드포인트**입니다.

### 에이전트

```http
POST   /api/agent            # 에이전트 명령 실행 (/api/chat와 동일한 파이프라인)
```

응답 예시:
```json
{
  "approved": true,
  "steps": [
    {
      "tool": "get_system_info",
      "vote": {"approved": true, "summary": "auto-approved"},
      "result": {"success": true, "cpu_percent": 12.5, "ram_used_gb": 8.2}
    }
  ],
  "ai_responses": {
    "GPT": "현재 CPU 사용률은 12.5%이고...",
    "Claude": "시스템 상태를 확인해봤어요!...",
    "Gemini": "시스템 정보를 살펴보았네..."
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

### Tool Manager (MCP)

```http
GET    /api/tool-manager/config          # 등록된 MCP 서버 목록
POST   /api/tool-manager/register        # MCP 서버 등록
POST   /api/tool-manager/check           # 서버 연결 확인
DELETE /api/tool-manager/{name}          # MCP 서버 삭제
GET    /api/tool-manager/{name}/tools    # 서버 제공 도구 목록
POST   /api/tool-manager/{name}/call     # 도구 직접 호출
```

### 기타

```http
GET    /api/history           # 대화 히스토리
DELETE /api/history           # 히스토리 초기화
GET    /health                # 서버 상태 (등록된 도구 목록 포함)
```

모든 엔드포인트는 `session_id` 파라미터로 세션별 상태를 분리할 수 있습니다. 생략 시 기본 세션(`default`) 사용.

---

## 투표 시스템 상세

### 투표 대상

모든 도구가 투표를 거치는 것이 아니라, **파괴적/위험 작업만** 투표합니다.

| 구분 | 도구 | 처리 방식 |
|------|------|----------|
| 조회/분석 | 시스템 정보, 파일 읽기, 웹 검색, Python 실행 등 | 즉시 자동 승인 |
| 파괴적 작업 | `write_file`, `run_command`, `kill_process`, `git_run` | 3 AI 다수결 투표 |

### 투표 규칙

- 3개 AI 중 **2개 이상 APPROVE** → 작업 실행
- **2개 이상 REJECT** → 작업 거부 (거부 이유 표시)
- AI 호출 실패 시 → 안전을 위해 **REJECT** 처리
- 사용 가능한 AI가 2개 미만 → 투표 불가

### 투표 평가 기준

1. **시스템 피해**: 운영체제, 시스템 파일에 피해를 줄 수 있는가?
2. **데이터 손실**: 중요한 데이터 삭제/손상 위험이 있는가?
3. **보안 취약점**: 악성 코드 실행, 권한 상승, 정보 유출 위험이 있는가?
4. **의도 확인**: 사용자의 의도가 명확하고 합리적인가?

### 예시

```
⚡ 자동 승인 (투표 없이 즉시 실행):
  현재 CPU/메모리 사용량 보여줘
  README.md 읽어줘
  최신 AI 뉴스 검색해줘
  Python으로 1+1 계산해봐

🗳️ 투표 후 실행:
  C:\work\notes.txt 파일 만들어줘
  현재 디렉토리 파일 삭제해줘
  git status 확인해줘

❌ 위험한 작업 (대부분 거부):
  시스템 파일 삭제해줘
  format c: 실행해줘
```

---

## AI 캐릭터

| AI | 모델 | 성격 |
|---|---|---|
| **GPT** | gpt-5-mini | 젊고 스마트한 남성 말투 |
| **Claude** | claude-haiku-4-5-20251001 | 활기찬 여성 말투 |
| **Gemini** | gemini-2.5-flash-lite | 지혜로운 노인 말투 |

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

### 지원 파일

- PDF (`.pdf`), Word (`.docx`)
- 텍스트 (`.txt`, `.json`)
- 이미지 (`.png`, `.jpg`, `.jpeg`)

### 비용

| 항목 | 비용 |
|------|------|
| File Search Store 유지 | **무료** |
| 쿼리 시 임베딩 | **무료** |
| 초기 인덱싱 | $0.15 / 1M 토큰 |

---

## 장기 메모리 시스템

### 저장 구조

```
backend/data/memory/
└── sessions/
    ├── default/
    │   ├── MEMORY.md
    │   ├── daily/
    │   │   ├── 2026-02-17.md
    │   │   └── ...
    │   └── metadata.json
    └── another-session/
        ├── MEMORY.md
        ├── daily/
        └── metadata.json
```

### 기능

- 대화 내용 자동 저장 (일별 로그)
- 에이전트 실행 결과 자동 기록
- 에이전트 감사 로그 자동 기록
- 키워드 기반 메모리 검색
- 채팅 시 메모리 컨텍스트 자동 주입
- 서버 재시작 후에도 유지
- 세션 ID별 메모리 완전 분리

---

## 트러블슈팅

### psutil / pyperclip 미설치

```bash
pip install psutil pyperclip
```

`get_system_info`, `list_processes`, `get_network_info` 도구는 psutil이,
`get_clipboard`, `set_clipboard` 도구는 pyperclip이 필요합니다.

### Google GenAI SDK 버전

```bash
# File Search Store 사용 시 1.50.0 이상 필수
pip show google-genai
pip install --upgrade google-genai
```

### Gemini 모델 호환성

File Search 지원 모델만 사용:
- gemini-2.5-flash-lite (현재 사용)
- gemini-2.5-flash
- gemini-2.5-pro
- gemini-1.5-pro / gemini-1.5-flash

### MCP 서버 연결 오류

```bash
# Node.js mcp_bridge 의존성 설치 확인
cd backend/mcp_bridge
npm install
```

서버 최초 실행 시 자동으로 `npm install`이 수행됩니다.

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
| `tools[0].tool_type: required one_of...` | Gemini 모델 File Search 미지원 | `gemini-2.5-flash-lite`로 변경 |
| `psutil not installed` | psutil 미설치 | `pip install psutil` |
| `pyperclip not installed` | pyperclip 미설치 | `pip install pyperclip` |
| `GPT error: 400 Unsupported parameter` | max_tokens 파라미터 문제 | ai_manager.py에서 `max_completion_tokens` 사용 확인 |

---

## 기술 스택

### 백엔드
- **FastAPI** (비동기 웹 서버)
- **Google Gemini API** (`google-genai>=1.50.0`) - File Search Store, gemini-2.5-flash-lite
- **OpenAI API** (`openai>=1.58.0`) - gpt-5-mini
- **Anthropic API** (`anthropic>=0.42.0`) - claude-haiku-4-5-20251001
- **DDGS (`ddgs`)** - Python 기반 웹 검색
- **Playwright** - 브라우저 렌더링, 동적 페이지 읽기, 링크 수집, 스크린샷
- **psutil** - 시스템 정보, 프로세스 관리, 네트워크 정보
- **pyperclip** - 클립보드 읽기/쓰기
- **MCP SDK (`@modelcontextprotocol/sdk`)** - Node.js MCP 브리지
- Python 3.11+

### 프론트엔드
- **React 18** + TypeScript
- **Vite** (빌드 도구)
- **Axios** (HTTP 클라이언트)
- **React Markdown** (마크다운 렌더링)

---

## 라이선스

Apache-2.0 license
