# MultiClaw (멀티클로) - AI 다수결 투표 에이전트 시스템

**3개 AI가 투표로 안전성을 검증하는 AI Agent + RAG Chat 시스템**

GPT, Claude, Gemini가 동시에 답변하며, 에이전트 작업은 3개 AI의 다수결 투표(2/3 이상 동의)를 거쳐 안전하게 실행됩니다.

## 핵심 특징

- **AI 다수결 투표**: 에이전트 작업 실행 전 GPT, Claude, Gemini가 안전성을 평가하여 2/3 이상 동의 시 실행
- **멀티 AI 동시 응답**: 3개 AI가 각자의 개성 있는 말투로 동시 답변
- **항시 활성화 에이전트 모드**: 별도의 `/agent` 접두사 없이도 모든 대화가 기본적으로 에이전트 파이프라인(계획 → 검증 → 3 AI 투표 → 실행 → 최종 응답) 안에서 처리
- **AI 에이전트**: 파일 읽기/쓰기, 명령 실행, 웹 검색 등 도구 실행
- **로컬 시스템 파일 접근**: Windows 절대 경로를 포함한 로컬 파일 시스템 읽기/쓰기/목록 조회 가능
- **로컬 장기 메모리**: 대화 내용을 로컬 파일에 저장하여 세션 간 기억 유지
- **세션별 메모리/히스토리 분리**: 세션 ID별로 대화 기록, 장기 메모리, 에이전트 감사 로그를 분리 저장
- **Gemini File Search Store RAG**: 파일 업로드만으로 자동 청킹, 임베딩, 인덱싱
- **사용자 키 기반 Gemini 스토어 사용**: `GEMINI_API_KEY`로 생성된 Gemini File Search Store를 사용하며, 업로드/검색/삭제 모두 해당 키의 사용량과 리소스를 사용
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

`install.bat`, `install-simple.bat`, `install-admin.bat`, `install-venv.bat`는 이제 Playwright Chromium 브라우저까지 함께 설치합니다.
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
- 파일/폴더/경로/명령/검색 요청이 포함된 경우: 에이전트 계획 수립 후 다수결 투표를 거쳐 실제 도구 실행
- 사용자가 특정 AI만 지목한 경우(`@GPT`, `@Claude`, `@Gemini`): 최종 응답 표시 대상을 해당 AI로 제한 가능

즉, **사용자는 별도 모드를 기억할 필요 없이 그냥 자연어로 지시하면 됩니다.**

```
안녕하세요!                    → 3개 AI 모두 응답
@GPT 코드 리뷰해줘             → GPT만 응답
@Claude 이 문서 요약해줘        → Claude만 응답
@Gemini 조언 좀 해줘           → Gemini만 응답
C:\work\test.txt 파일 만들어줘   → 에이전트 계획/투표 후 실제 파일 생성 시도
현재 폴더 파일 목록 보여줘       → 에이전트 계획/투표 후 실제 목록 조회
```

**에이전트 실행 흐름:**
```
사용자: 파일 목록 보여줘
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

### 상시 활성화 에이전트 모드 상세

업데이트 이후 MultiClaw는 "일반 채팅 UI + 별도 에이전트 UI"의 구분이 아니라,
**전체 서비스가 항상 에이전트 프로그램으로 동작하는 구조**로 정리되었습니다.

의미는 다음과 같습니다.

- 사용자가 `/agent`를 붙이지 않아도 모든 요청이 에이전트 관점에서 해석됩니다.
- 시스템은 요청을 보고 "도구 실행이 필요한지 / 그냥 답변하면 되는지"를 자체 판단합니다.
- 파일 생성/수정/읽기/폴더 조회/명령 실행/웹 검색 지시가 오면 도구 계획을 우선 수립합니다.
- 도구 실행 전에는 항상 3개 AI 투표를 거쳐야 합니다.
- 도구가 필요 없다고 판단되는 순수 일반 질문은 바로 3개 AI 최종 응답으로 이어집니다.
- 프론트 UI에서도 별도 `/agent` 모드 분기를 두지 않고, 모든 메시지가 동일한 실행 흐름을 탑니다.

### 사용 가능한 에이전트 도구

| 도구 | 설명 |
|------|------|
| `read_file` | 파일 내용 읽기 |
| `write_file` | 파일 생성/수정 |
| `list_files` | 디렉토리 파일 목록 조회 |
| `run_command` | 시스템 명령어 실행 (위험 명령 자동 차단) |
| `web_search` | Python 기반 실시간 웹 검색 (`ddgs`) |
| `fetch_url` | 웹 페이지 URL 직접 읽기 |
| `browser_extract` | Playwright로 동적 웹 페이지 렌더링 후 본문 추출 |
| `browser_collect_links` | Playwright로 페이지 링크 수집 |
| `browser_screenshot` | Playwright로 페이지 스크린샷 저장 |

`web_search`는 현재 별도 Perplexity API Key 없이 동작하며, Python 검색 결과를 가져온 뒤 MultiClaw의 GPT, Claude, Gemini가 그 결과를 바탕으로 최종 응답을 합성합니다.
또한 최신 정보, 오늘 뉴스, 최근 변경사항처럼 실시간성이 필요한 요청은 시스템이 자동으로 웹 검색 단계를 우선 계획하도록 보강되었습니다.
정적 HTML만으로 읽기 어려운 사이트는 `browser_extract`, `browser_collect_links`, `browser_screenshot`를 통해 실제 브라우저를 열어 읽고 탐색할 수 있습니다.

**안전 장치:**
- 위험한 명령어 (`rm -rf /`, `format c:`, `del /f` 등) 자동 차단
- 3개 AI 중 2개 이상이 거부하면 작업 미실행
- 명령 실행 30초 타임아웃

**로컬 파일/시스템 접근 정책:**
- 현재 버전은 원래 구상안에 맞게 **로컬 시스템 파일 접근을 허용**합니다.
- 절대 경로(`C:\...`)와 상대 경로 모두 사용할 수 있습니다.
- `read_file`, `write_file`, `list_files`는 로컬 파일 시스템에 대해 실제 동작합니다.
- `run_command` 역시 로컬 시스템 명령을 실제 실행하지만, 위험 명령 패턴은 계속 차단합니다.
- 즉, "로컬 파일을 직접 다룰 수 없는 AI"가 아니라, **로컬 시스템을 실제로 다루는 에이전트 프로그램**입니다.

### 실행 중단 / 취소

업데이트로 진행 중인 작업을 중간에 멈출 수 있는 로직이 추가되었습니다.

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
- 즉, 로컬에서 본인 키를 사용하면 본인 Gemini 리소스를 사용하고, 공용 서버 키를 사용하면 공용 Gemini 리소스를 사용합니다.
- 업로드, 검색, 삭제 모두 해당 Gemini 키의 사용량과 연결됩니다.
- 로컬에는 문서 메타데이터와 스토어 참조 정보만 유지하고, RAG 검색은 Gemini File Search Store에서 수행합니다.

### 장기 메모리

- 대화 내용이 자동으로 로컬 메모리에 저장
- 세션 간 기억 유지 (서버 재시작 후에도 유지)
- 화면 상단 **메모리** 버튼으로 저장된 메모리 확인/초기화

**세션 분리 업데이트:**
- 현재 버전에서는 장기 메모리와 히스토리가 세션 단위로 분리됩니다.
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
│   ├── file_search_manager.py    # Gemini File Search Store 관리자
│   ├── agent_executor.py         # 에이전트 실행 엔진
│   ├── agent_tools.py            # 에이전트 도구 (파일, 명령, 검색)
│   ├── voting_system.py          # 3 AI 다수결 투표 시스템
│   ├── tool_policy.py            # 도구 실행 정책 (위험 명령 차단 등)
│   ├── tool_registry.py          # 확장형 도구 레지스트리
│   ├── runtime_config.py         # 런타임 공통 설정
│   ├── session_context.py        # 세션 컨텍스트/세션 히스토리 관리
│   ├── cancellation_manager.py   # 실행 중단/취소 관리
│   ├── stream_events.py          # 스트리밍 이벤트 포맷
│   ├── memory_manager.py         # 로컬 장기 메모리 관리
│   ├── data/                     # 데이터 저장소
│   │   ├── memory/               # 장기 메모리
│   │   │   └── sessions/         # 세션별 메모리 저장소
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
```

현재 `/api/chat`은 단순 LLM 응답 엔드포인트가 아니라,
**항상 에이전트 파이프라인을 통과하는 기본 대화 엔드포인트**입니다.

즉:
- 파일/경로/명령/검색 요청이면 계획/투표/실행 포함
- 일반 질문이면 도구 없이 최종 응답 생성
- 응답에는 `responses`뿐 아니라 `agent_result`도 함께 포함될 수 있습니다

### 에이전트

```http
POST   /api/agent            # 에이전트 명령 실행 (호환용 별칭 성격)
```

요청:
```json
{
  "message": "파일 목록 보여줘",
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

참고:
- `/api/agent`는 여전히 사용할 수 있지만, 현재 시스템에서는 `/api/chat`도 동일한 에이전트 실행 흐름을 탑니다.
- 즉, 프론트 기본 사용 경로는 `/api/chat`이며, `/api/agent`는 호환 유지 목적이 큽니다.

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
POST   /api/chat/cancel       # 현재 세션의 실행 중 작업 중단 요청
GET    /health                # 서버 상태
```

### 세션 ID 사용

다음 엔드포인트들은 `session_id`를 통해 세션별 상태를 분리할 수 있습니다.

- `/api/chat`
- `/api/agent`
- `/api/upload`
- `/api/memory`
- `/api/history`
- `/api/chat/cancel`

세션 ID를 주지 않으면 기본 세션(`default`)을 사용합니다.

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
  현재 디렉토리 파일 목록 보여줘
  README.md 읽어줘
  최신 AI 뉴스 검색해줘
  C:\work\notes.txt 파일 만들어줘

❌ 위험한 작업 (대부분 거부):
  시스템 파일 삭제해줘
  모든 파일을 지워줘
  format c: 실행해줘
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

### 현재 구현 기준 주의사항

- File Search Store는 현재 설정된 `GEMINI_API_KEY` 기준으로 생성 및 사용됩니다.
- 업로드된 문서는 Google Gemini 쪽 스토어에 저장됩니다.
- 로컬에는 `file_search_metadata.json` 형태의 메타데이터만 유지됩니다.
- 문서 삭제 요청 시 Google 쪽 삭제도 함께 시도합니다.
- 다만 네트워크/API 오류가 발생하면 Google 쪽 삭제와 로컬 메타데이터 삭제가 완전히 동기화되지 않을 가능성은 있습니다.

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

### 세션별 메모리 동작

- 각 세션은 자기만의 `MEMORY.md`, `daily/`, `metadata.json`을 가집니다.
- 서로 다른 세션끼리는 기본적으로 메모리와 히스토리를 공유하지 않습니다.
- 프론트 상단 Session 입력창으로 세션을 전환하면 해당 세션 컨텍스트가 로드됩니다.
- 특정 작업용 세션, 테스트용 세션, 프로젝트별 세션을 병렬로 운영할 수 있습니다.

---

## 추가 반영된 구조 업데이트

### 1. 상시 활성화 에이전트 프로그램화

- `/agent`를 붙여야만 에이전트가 되는 구조를 폐기
- 일반 채팅 자체가 항상 에이전트 파이프라인으로 동작
- 사용자는 "그냥 말하면" 되고, 시스템이 도구 실행 필요 여부를 판단

### 2. 세션별 상태 관리 도입

- 세션별 히스토리
- 세션별 장기 메모리
- 세션별 에이전트 감사 로그
- 프론트 Session UI + `localStorage` 저장

### 3. 실행 중단 기능 추가

- 프론트 `Stop` 버튼 추가
- 브라우저 요청 AbortController 적용
- 백엔드 `POST /api/chat/cancel` 추가
- 진행 중 subprocess 강제 종료 처리

### 4. 확장형 내부 구조 도입

- `RuntimeConfig`
- `SessionContext`
- `ToolPolicy`
- `ToolRegistry`
- `CancellationManager`

위 구조는 기존 서비스 형태를 바꾸기 위한 것이 아니라,
원래 MultiClaw의 "로컬 에이전트 + 3 AI 승인 + RAG + 메모리" 구상을 더 안정적으로 유지하기 위한 내부 정비입니다.

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
- **DDGS (`ddgs`)** - Python 기반 웹 검색 (에이전트)
- **Playwright** - 브라우저 렌더링, 동적 페이지 읽기, 링크 수집, 스크린샷
- Python 3.11+

### 프론트엔드
- **React 18** + TypeScript
- **Vite** (빌드 도구)
- **Axios** (HTTP 클라이언트)
- **React Markdown** (마크다운 렌더링)

---

## 라이선스

Apache-2.0 license
