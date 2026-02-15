<p align="center">
  <img src="assets/nanoclaw-logo.png" alt="NanoClaw" width="400">
</p>

<p align="center">
  My personal Claude assistant that runs securely in containers. Lightweight and built to be understood and customized for your own needs.
</p>

<p align="center">
  <a href="README_zh.md">中文</a>&nbsp; • &nbsp;
  <a href="https://discord.gg/VGWXrf8x"><img src="https://img.shields.io/discord/1470188214710046894?label=Discord&logo=discord&v=2" alt="Discord" valign="middle"></a>&nbsp; • &nbsp;
  <a href="repo-tokens"><img src="repo-tokens/badge.svg" alt="34.9k tokens, 17% of context window" valign="middle"></a>
</p>

**New:** First AI assistant to support [Agent Swarms](https://code.claude.com/docs/en/agent-teams). Spin up teams of agents that collaborate in your chat.

---

## 목차

- [NanoClaw이란 무엇인가?](#nanoclaw이란-무엇인가)
- [OpenClaw vs NanoClaw — 어떤 걸 선택해야 할까?](#openclaw-vs-nanoclaw--어떤-걸-선택해야-할까)
- [Why I Built This](#why-i-built-this)
- [Philosophy](#philosophy)
- [핵심 기능](#핵심-기능)
- [Quick Start (설치 가이드)](#quick-start-설치-가이드)
- [Usage (사용 방법)](#usage-사용-방법)
- [Customizing (커스터마이징)](#customizing-커스터마이징)
- [Skills 시스템](#skills-시스템)
- [Architecture (아키텍처)](#architecture-아키텍처)
- [보안 모델](#보안-모델)
- [비용 안내](#비용-안내)
- [FAQ (자주 묻는 질문)](#faq-자주-묻는-질문)
- [문서 및 참고자료](#문서-및-참고자료)
- [Contributing](#contributing)
- [Community](#community)
- [License](#license)

---

## NanoClaw이란 무엇인가?

**NanoClaw**은 **경량 오픈소스 개인 AI 비서**입니다. Anthropic의 Claude Agent SDK 위에 구축되어, WhatsApp을 통해 Claude AI와 대화하고 실제 작업을 시킬 수 있습니다.

쉽게 말하면:

- 휴대폰 WhatsApp에서 AI 비서에게 메시지를 보내면
- AI가 컨테이너(격리된 안전한 환경) 안에서 작업을 수행하고
- 결과를 WhatsApp으로 돌려보내줍니다

**핵심 특징은 "단순함"과 "보안"입니다.** 전체 코드가 약 2,000줄, 핵심 파일 5개로 구성되어 있어 **8분이면 전체 코드를 읽고 이해**할 수 있습니다. AI 에이전트는 OS 수준의 컨테이너 안에서 격리되어 실행되므로, 여러분의 시스템을 안전하게 보호합니다.

> **한 줄 요약:** NanoClaw은 "읽고, 이해하고, 믿을 수 있는" 미니멀한 AI 개인 비서입니다.

[공식 웹사이트](https://nanoclaw.net/) · [GitHub](https://github.com/gavrielc/nanoclaw) · [DeepWiki 문서](https://deepwiki.com/gavrielc/nanoclaw) · [Discord](https://discord.gg/VGWXrf8x)

---

## OpenClaw vs NanoClaw — 어떤 걸 선택해야 할까?

NanoClaw은 [OpenClaw](https://github.com/openclaw/openclaw)의 포크(fork)가 아닙니다. OpenClaw의 비전에서 영감을 받되, 보안과 코드 복잡도 문제를 해결하기 위해 **처음부터 완전히 새로 작성**한 독립 프로젝트입니다.

| 구분 | NanoClaw | OpenClaw |
|------|----------|----------|
| **철학** | "하나의 프로세스, 완전한 통제" | "배터리 포함, 모든 기능 내장" |
| **코드 규모** | ~2,000줄 / 5개 핵심 모듈 | ~400,000줄 / 52+ 모듈 |
| **의존성** | 최소화 (7개) | 45+ 패키지 |
| **보안 방식** | OS 수준 컨테이너 격리 | 앱 수준 (허용 목록, 페어링 코드) |
| **메시징 채널** | WhatsApp 기본 (스킬로 추가 가능) | 12+ 채널 기본 내장 |
| **AI 모델** | Claude 전용 (Agent SDK) | 멀티 모델 (Anthropic, OpenAI, xAI 등) |
| **설정 방식** | 코드를 직접 수정 (설정 파일 없음) | 설정 파일 기반 (openclaw.json) |
| **에이전트 스웜** | 지원 (iSwarms, 최초 지원) | 미지원 |
| **라이선스** | MIT | MIT |
| **대상 사용자** | 보안 중시 개발자, 코드를 이해하고 싶은 사용자 | 다양한 채널과 기능이 필요한 일반 사용자 |
| **플랫폼** | macOS (Apple Container), Linux (Docker) | macOS, Linux, Windows (WSL2) |
| **GitHub 스타** | 7,000+ (출시 1주일) | 180,000+ |

### NanoClaw을 선택해야 할 때

- 전체 코드를 직접 읽고 감사(audit)할 수 있는 수준의 투명성을 원할 때
- OS 수준 컨테이너 격리로 확실한 보안을 원할 때
- WhatsApp을 주력 메신저로 사용할 때
- Claude AI만 사용해도 충분할 때
- 미니멀한 코드를 직접 수정하여 맞춤화하고 싶을 때

### OpenClaw을 선택해야 할 때

- WhatsApp 외에 Telegram, Slack, Discord 등 다양한 채널이 기본으로 필요할 때
- Claude 외에 OpenAI, Grok 등 여러 AI 모델을 사용하고 싶을 때
- 5,700+개의 ClawHub 스킬 생태계를 활용하고 싶을 때
- Windows 환경에서 사용해야 할 때
- 코드를 직접 수정하지 않고 설정 파일만으로 관리하고 싶을 때

---

## Why I Built This

[OpenClaw](https://github.com/openclaw/openclaw) is an impressive project with a great vision. But I can't sleep well running software I don't understand with access to my life. OpenClaw has 52+ modules, 8 config management files, 45+ dependencies, and abstractions for 15 channel providers. Security is application-level (allowlists, pairing codes) rather than OS isolation. Everything runs in one Node process with shared memory.

NanoClaw gives you the same core functionality in a codebase you can understand in 8 minutes. One process. A handful of files. Agents run in actual Linux containers with filesystem isolation, not behind permission checks.

> *"The security issues of OpenClaw are real and severe. There's just no way to secure a project built in 8 weeks with +350k lines of code. The attack surface is too big and the architecture is too complicated. I built NanoClaw to be dead simple so you can review all the code."* — Gavriel Cohen, 창시자

---

## Philosophy

**Small enough to understand.** One process, a few source files. No microservices, no message queues, no abstraction layers. Have Claude Code walk you through it.

**Secure by isolation.** Agents run in Linux containers (Apple Container on macOS, or Docker). They can only see what's explicitly mounted. Bash access is safe because commands run inside the container, not on your host.

**Built for one user.** This isn't a framework. It's working software that fits my exact needs. You fork it and have Claude Code make it match your exact needs.

**Customization = code changes.** No configuration sprawl. Want different behavior? Modify the code. The codebase is small enough that this is safe.

**AI-native.** No installation wizard; Claude Code guides setup. No monitoring dashboard; ask Claude what's happening. No debugging tools; describe the problem, Claude fixes it.

**Skills over features.** Contributors shouldn't add features (e.g. support for Telegram) to the codebase. Instead, they contribute [claude code skills](https://code.claude.com/docs/en/skills) like `/add-telegram` that transform your fork. You end up with clean code that does exactly what you need, not a bloated system trying to support every use case.

**Best harness, best model.** This runs on Claude Agent SDK, which means you're running Claude Code directly. The harness matters. A bad harness makes even smart models seem dumb, a good harness gives them superpowers. Claude Code is (IMO) the best harness available.

---

## 핵심 기능

### WhatsApp 기반 AI 대화
휴대폰 WhatsApp에서 Claude AI와 자연스럽게 대화합니다. 별도 앱 설치 없이, 이미 쓰고 있는 메신저로 AI 비서를 사용합니다.

### 그룹별 격리된 컨텍스트
각 WhatsApp 그룹마다 독립된 `CLAUDE.md` 메모리와 격리된 파일시스템을 가집니다. A 그룹의 대화 내용이 B 그룹에 절대 노출되지 않습니다.

### 메인 채널 관리
WhatsApp 셀프채팅(나에게 보내기)이 관리자 채널이 됩니다. 모든 그룹의 작업을 관리하고, 전체 프로젝트 파일에 접근할 수 있습니다.

### 예약 작업 (Scheduled Tasks)
크론(cron) 표현식, 간격 반복, 일회성 실행 등 3가지 방식으로 작업을 예약할 수 있습니다. 시간대(timezone) 지원 포함.

### 에이전트 스웜 (Agent Swarms)
**개인 AI 비서 최초 지원.** 여러 전문 에이전트가 팀을 이루어 복잡한 작업을 병렬로 협업 처리합니다.

### 컨테이너 격리 보안
모든 에이전트가 Linux 컨테이너(Apple Container 또는 Docker) 안에서 실행됩니다. 명시적으로 마운트된 디렉토리만 접근 가능하며, Bash 명령도 컨테이너 안에서만 실행됩니다.

### 웹 검색 및 브라우저 자동화
실시간 웹 검색과 콘텐츠 가져오기를 지원합니다. 컨테이너 내 Chromium을 통한 브라우저 자동화도 가능합니다.

### 확장 가능한 스킬 시스템
기본은 WhatsApp이지만, `/add-telegram`, `/add-gmail`, `/add-discord` 등 스킬을 실행하여 기능을 확장할 수 있습니다.

---

## Quick Start (설치 가이드)

### 사전 준비사항

| 항목 | 요구 사항 |
|------|-----------|
| **운영체제** | macOS 또는 Linux |
| **Node.js** | 20 이상 |
| **Claude Code** | [claude.ai/download](https://claude.ai/download)에서 설치 |
| **컨테이너 런타임** | [Apple Container](https://github.com/apple/container) (macOS) 또는 [Docker](https://docker.com/products/docker-desktop) (macOS/Linux) |
| **인터넷** | WhatsApp 연결, Claude API 호출, npm 패키지 설치용 |

> **Windows 사용자:** 현재 네이티브 미지원. WSL2 + Docker를 통한 실행이 가능하며, `/setup-windows` 스킬 개발이 요청 중(RFS)입니다.

### 설치 (4단계)

```bash
# 1. 저장소 클론
git clone https://github.com/gavrielc/nanoclaw.git

# 2. 디렉토리 이동
cd nanoclaw

# 3. Claude Code 실행
claude

# 4. 셋업 스킬 실행
/setup
```

Claude Code가 나머지를 모두 자동으로 처리합니다:

1. npm 의존성 설치
2. Apple Container 또는 Docker 시스템 설정
3. Claude API 인증 (OAuth 또는 API 키)
4. 컨테이너 이미지 빌드 (`./container/build.sh`)
5. WhatsApp QR 코드 인증 (휴대폰으로 스캔)
6. 메인 채널 등록 (채팅 JID 캡처)
7. launchd 서비스 등록 (macOS — 재부팅 후에도 자동 실행)

### 설치 후 생성되는 파일

| 파일/폴더 | 용도 |
|-----------|------|
| `.env` | API 인증 정보 |
| `store/auth_info_baileys/` | WhatsApp 세션 데이터 |
| `data/registered_groups.json` | 등록된 그룹 목록 |
| `data/messages.db` | SQLite 데이터베이스 |
| `~/Library/LaunchAgents/com.nanoclaw.plist` | macOS 서비스 정의 |

---

## Usage (사용 방법)

트리거 워드(기본: `@Andy`)로 AI 비서에게 말을 걸 수 있습니다:

### 일반 그룹에서

```
@Andy 매주 월요일 오전 9시에 AI 뉴스 브리핑 보내줘
@Andy 지난주 git 히스토리 검토해서 README 업데이트해줘
@Andy 영업 파이프라인 현황 매일 아침 9시에 정리해서 보내줘
```

### 메인 채널(셀프채팅)에서 — 관리자 기능

```
@Andy 모든 그룹의 예약 작업 목록 보여줘
@Andy 월요 브리핑 작업 일시 중지해줘
@Andy 가족 채팅 그룹에 참여해줘
```

### 트리거 워드 변경

기본값은 `@Andy`이며, 환경변수 `ASSISTANT_NAME`으로 변경하거나, Claude Code에게 "트리거 워드를 @Bob으로 바꿔줘"라고 요청하면 됩니다.

---

## Customizing (커스터마이징)

NanoClaw에는 설정 파일이 없습니다. 대신 Claude Code에게 직접 말하면 됩니다:

```
"트리거 워드를 @Bob으로 바꿔줘"
"앞으로 응답을 더 짧고 직접적으로 해줘"
"아침 인사하면 커스텀 인사말 해줘"
"매주 대화 요약을 저장해줘"
```

또는 `/customize` 스킬을 실행하면 가이드된 변경을 할 수 있습니다.

코드베이스가 충분히 작아서 Claude가 안전하게 수정할 수 있습니다. 이것이 NanoClaw의 핵심 철학입니다 — **설정 파일을 배우는 것이 아니라, AI에게 원하는 것을 말하는 것.**

---

## Skills 시스템

NanoClaw의 확장은 "기능 추가"가 아니라 **"스킬 추가"** 방식으로 이루어집니다.

### 스킬이란?

`.claude/skills/` 디렉토리에 있는 마크다운 파일로, Claude Code에게 NanoClaw 설치본을 어떻게 변환할지 가르칩니다. 사용자가 스킬을 실행하면 Claude Code가 코드를 자동으로 수정합니다.

### 기본 제공 스킬

| 스킬 | 용도 |
|------|------|
| `/setup` | 최초 설치, 인증, 서비스 설정 |
| `/customize` | 채널 추가, 통합, 동작 변경 |
| `/debug` | 컨테이너 문제, 로그, 트러블슈팅 |

### 커뮤니티 스킬

| 스킬 | 기여자 | 설명 |
|------|--------|------|
| `/convert-to-docker` | @dotsetgreg | Apple Container를 Docker로 전환 (Linux 지원) |
| `/add-telegram` | 커뮤니티 | Telegram 채널 추가 |
| `/add-gmail` | 커뮤니티 | Gmail 통합 추가 |
| `/add-voice-transcription` | 커뮤니티 | 음성 메시지 텍스트 변환 |
| `/x-integration` | 커뮤니티 | X(Twitter) 통합 |

### RFS (Request for Skills) — 기여 요청 중인 스킬

**Communication Channels**
- `/add-telegram` - Telegram 채널 추가. WhatsApp 대체 또는 추가 채널로 선택 가능
- `/add-slack` - Slack 채널 추가
- `/add-discord` - Discord 채널 추가

**Platform Support**
- `/setup-windows` - Windows WSL2 + Docker 환경 설정

**Session Management**
- `/add-clear` - 대화 컨텍스트 압축 명령어 추가

---

## Architecture (아키텍처)

### 전체 구조

```
WhatsApp 메시지 수신 (baileys)
    ↓
SQLite에 메시지 저장
    ↓
폴링 루프 (2초 간격)
    ↓
컨테이너 생성 (Apple Container / Docker)
    ├── Claude Agent SDK 실행
    ├── 마운트된 디렉토리만 접근 가능
    └── MCP 도구 (send_message, schedule_task 등)
    ↓
응답을 WhatsApp으로 전송
```

단일 Node.js 프로세스. 에이전트는 격리된 Linux 컨테이너에서 실행. 그룹별 메시지 큐에 동시성 제어. IPC는 파일시스템 기반.

### 핵심 파일

| 파일 | 역할 |
|------|------|
| `src/index.ts` | 오케스트레이터: 상태 관리, 메시지 루프, 에이전트 호출 |
| `src/channels/whatsapp.ts` | WhatsApp 연결, 인증, 송/수신 |
| `src/ipc.ts` | IPC 감시자 및 작업 처리 |
| `src/router.ts` | 메시지 포맷팅 및 발신 라우팅 |
| `src/group-queue.ts` | 그룹별 큐 + 글로벌 동시 실행 제한 |
| `src/container-runner.ts` | 에이전트 컨테이너 생성 및 볼륨 마운트 |
| `src/task-scheduler.ts` | 예약 작업 실행 (60초 간격 체크) |
| `src/db.ts` | SQLite 작업 (메시지, 그룹, 세션, 상태) |
| `groups/*/CLAUDE.md` | 그룹별 메모리 (격리) |

### 기술 스택

| 레이어 | 기술 |
|--------|------|
| 런타임 | Node.js 20+ |
| 컨테이너 | Apple Container (macOS) / Docker (Linux) |
| 메시징 | @whiskeysockets/baileys (WhatsApp) |
| 데이터베이스 | better-sqlite3 (SQLite) |
| AI 에이전트 | Claude Agent SDK |
| MCP 도구 | @modelcontextprotocol/sdk |
| 로깅 | pino |
| 스케줄링 | cron-parser |

### 3개의 폴링 루프

| 루프 | 간격 | 역할 |
|------|------|------|
| 메시지 폴링 | 2,000ms | WhatsApp 메시지 확인 |
| IPC 감시 | 1,000ms | 그룹 간 메시지 큐 처리 |
| 작업 스케줄러 | 60,000ms | 예약 작업 실행 여부 확인 |

### 2단계 권한 모델

| 권한 | 메인 그룹 (셀프채팅) | 일반 그룹 |
|------|---------------------|-----------|
| 프로젝트 루트 접근 | 읽기/쓰기 | 없음 |
| 자체 그룹 폴더 | 읽기/쓰기 | 읽기/쓰기 |
| 글로벌 메모리 | 읽기/쓰기 | 읽기 전용 |
| 추가 마운트 | 설정 가능 | 읽기 전용 (허용 시) |
| 다른 그룹에 메시지 | 가능 | 불가 |
| 다른 그룹 작업 관리 | 가능 | 자기 그룹만 |

---

## 보안 모델

NanoClaw의 보안은 "앱에서 막는 것"이 아니라 **"OS가 격리하는 것"** 입니다.

### 신뢰 모델

| 주체 | 신뢰 수준 | 이유 |
|------|-----------|------|
| 메인 그룹 | 신뢰됨 | 사적 셀프채팅, 관리자 제어 |
| 일반 그룹 | 비신뢰 | 다른 사용자가 악의적일 수 있음 |
| 컨테이너 에이전트 | 샌드박스 | 격리된 실행 환경 |
| WhatsApp 메시지 | 사용자 입력 | 프롬프트 인젝션 가능성 |

### 보안 경계

**1. 컨테이너 격리 (핵심 보안)**
- 프로세스 격리 — 컨테이너 프로세스가 호스트에 영향을 줄 수 없음
- 파일시스템 격리 — 명시적으로 마운트된 디렉토리만 접근 가능
- 비루트 실행 — 비특권 `node` 사용자(uid 1000)로 실행
- 임시 컨테이너 — 호출마다 새 환경 생성(`--rm`)

**2. 마운트 보안**
- 마운트 허용 목록은 프로젝트 외부(`~/.config/nanoclaw/mount-allowlist.json`)에 저장
- 에이전트가 허용 목록 자체를 수정할 수 없음
- 기본 차단 패턴: `.ssh`, `.gnupg`, `.aws`, `.env`, `credentials`, `private_key` 등
- 심볼릭 링크 해석 후 검증 (경로 탈출 공격 방지)

**3. 자격 증명 필터링**
- 컨테이너에 노출되는 환경변수는 `CLAUDE_CODE_OAUTH_TOKEN`과 `ANTHROPIC_API_KEY`만 허용
- WhatsApp 세션, 마운트 허용 목록 등은 절대 컨테이너에 마운트되지 않음

### 보안 구조 요약

```
비신뢰 영역 (WhatsApp 메시지)
    ↓ 트리거 확인, 입력 이스케이핑
호스트 프로세스 (신뢰됨)
    ├── 메시지 라우팅
    ├── IPC 권한 확인
    ├── 마운트 검증 (외부 허용 목록)
    ├── 컨테이너 생명주기 관리
    └── 자격 증명 필터링
    ↓ 명시적 마운트만 전달
컨테이너 (격리/샌드박스)
    ├── 에이전트 실행
    ├── Bash 명령 (샌드박스 내부)
    ├── 파일 작업 (마운트된 경로만)
    └── 보안 설정 수정 불가
```

자세한 보안 문서: [docs/SECURITY.md](docs/SECURITY.md)

---

## 비용 안내

### 소프트웨어

**완전 무료.** MIT 라이선스 오픈소스입니다.

### API 사용료

Claude API 호출에 따른 비용이 발생합니다. Anthropic에 직접 지불합니다.

| 사용 패턴 | 월 예상 비용 |
|-----------|-------------|
| 가벼운 사용 (간단한 질답) | $5 이하 |
| 일반적 개인 사용 | $10 ~ $50 |
| 에이전트 스웜 + 자동화 | $50 ~ $200+ |

### 비용 주의사항

- 에이전트 스웜 사용 시 토큰 소비가 급증할 수 있습니다
- 한 사용자가 45분 만에 700만 토큰을 소비한 사례가 보고됨
- Anthropic 대시보드에서 **지출 한도를 반드시 설정**하세요

---

## FAQ (자주 묻는 질문)

**Why WhatsApp and not Telegram/Signal/etc?**

Because I use WhatsApp. Fork it and run a skill to change it. That's the whole point.

**Why Apple Container instead of Docker?**

On macOS, Apple Container is lightweight, fast, and optimized for Apple silicon. But Docker is also fully supported—during `/setup`, you can choose which runtime to use. On Linux, Docker is used automatically.

**Can I run this on Linux?**

Yes. Run `/setup` and it will automatically configure Docker as the container runtime. Thanks to [@dotsetgreg](https://github.com/dotsetgreg) for contributing the `/convert-to-docker` skill.

**Windows에서 실행할 수 있나요?**

현재 네이티브 지원은 없습니다. WSL2 + Docker 조합으로 실행 가능하며, `/setup-windows` 스킬 기여를 환영합니다.

**Is this secure?**

Agents run in containers, not behind application-level permission checks. They can only access explicitly mounted directories. You should still review what you're running, but the codebase is small enough that you actually can. See [docs/SECURITY.md](docs/SECURITY.md) for the full security model.

**Why no configuration files?**

We don't want configuration sprawl. Every user should customize it to so that the code matches exactly what they want rather than configuring a generic system. If you like having config files, tell Claude to add them.

**How do I debug issues?**

Ask Claude Code. "Why isn't the scheduler running?" "What's in the recent logs?" "Why did this message not get a response?" That's the AI-native approach.

**Why isn't the setup working for me?**

I don't know. Run `claude`, then run `/debug`. If claude finds an issue that is likely affecting other users, open a PR to modify the setup SKILL.md.

**OpenClaw과 뭐가 다른가요?**

OpenClaw은 12개 이상의 채널, 다중 AI 모델, 5,700+ 스킬 마켓플레이스를 갖춘 "풀스택" AI 비서입니다. NanoClaw은 그 핵심 기능만을 2,000줄의 코드로 구현한 "미니멀" AI 비서입니다. 보안은 앱 수준 대신 OS 수준 컨테이너 격리를 사용합니다. 자세한 비교는 [위의 비교표](#openclaw-vs-nanoclaw--어떤-걸-선택해야-할까)를 참조하세요.

**What changes will be accepted into the codebase?**

Security fixes, bug fixes, and clear improvements to the base configuration. That's it.

Everything else (new capabilities, OS compatibility, hardware support, enhancements) should be contributed as skills.

This keeps the base system minimal and lets every user customize their installation without inheriting features they don't want.

---

## 문서 및 참고자료

### 프로젝트 내 문서

| 문서 | 설명 |
|------|------|
| [docs/SECURITY.md](docs/SECURITY.md) | 전체 보안 모델 |
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | 아키텍처 결정 사항 |
| [docs/SPEC.md](docs/SPEC.md) | 기술 사양 |
| [docs/SDK_DEEP_DIVE.md](docs/SDK_DEEP_DIVE.md) | Claude Agent SDK 상세 |
| [docs/APPLE-CONTAINER-NETWORKING.md](docs/APPLE-CONTAINER-NETWORKING.md) | Apple Container 네트워킹 |
| [docs/DEBUG_CHECKLIST.md](docs/DEBUG_CHECKLIST.md) | 디버그 체크리스트 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 기여 가이드라인 |
| [CLAUDE.md](CLAUDE.md) | Claude Code 컨텍스트 |

### 외부 자료

- [DeepWiki — NanoClaw 종합 문서](https://deepwiki.com/gavrielc/nanoclaw) — 아키텍처, 시작하기, 기능, 보안 상세
- [VentureBeat — NanoClaw이 OpenClaw의 최대 보안 문제를 해결하다](https://venturebeat.com/orchestration/nanoclaw-solves-one-of-openclaws-biggest-security-issues-and-its-already)
- [Medium — NanoClaw: 500줄로 구현한 경량 ClawdBot](https://ai-engineering-trend.medium.com/nanoclaw-a-slimmed-down-version-of-clawdbot-achieved-in-just-500-lines-of-code-c208dc16ee8f)
- [itech4mac — AI 에이전트 초보 가이드: OpenClaw, NanoClaw, Moltbook이란?](https://www.itech4mac.net/2026/02/ai-agents-for-beginners-what-are-openclaw-nanoclaw-moltbook-and-how-to-run-them-on-mac/)
- [ScriptByAI — NanoClaw: 경량 보안 OpenClaw 대안](https://www.scriptbyai.com/nanoclaw-openclaw-alternative/)
- [40가지 팁 & 트릭 가이드](https://mlearning.substack.com/p/40-tips-and-tricks-from-first-install-to-production-nanoclaw-nano-claw-openclaw-open-2026-2-1-self-learning-skill-that-actually-work-vps-docker-security-ai-agent-swarm-readme-md-memory-architecture-cron-hearbeat-sessions-slack-telegram-whatsapp)
- [Hacker News — Show HN: NanoClaw](https://news.ycombinator.com/item?id=46850205)

---

## Contributing

**Don't add features. Add skills.**

If you want to add Telegram support, don't create a PR that adds Telegram alongside WhatsApp. Instead, contribute a skill file (`.claude/skills/add-telegram/SKILL.md`) that teaches Claude Code how to transform a NanoClaw installation to use Telegram.

Users then run `/add-telegram` on their fork and get clean code that does exactly what they need, not a bloated system trying to support every use case.

### 기여 종류별 가이드

| 기여 유형 | 수용 여부 | 방식 |
|-----------|-----------|------|
| 버그 수정 | 수용 | PR 제출 |
| 보안 수정 | 수용 | PR 제출 |
| 코드 단순화 | 수용 | PR 제출 |
| 새 기능/채널/통합 | 스킬로 기여 | `.claude/skills/` 에 SKILL.md 추가 |
| 플랫폼 호환성 | 스킬로 기여 | `/setup-windows` 등 |

스킬 PR은 소스 파일을 수정해서는 안 됩니다. Claude Code가 실행할 **지시사항(instructions)** 만 포함해야 합니다.

---

## License

MIT — Copyright (c) 2026 Gavriel Cohen
