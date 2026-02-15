# 🦞 OpenClaw — 나만의 24시간 AI 개인 비서 종합 가이드

<p align="center">
    <picture>
        <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/openclaw/openclaw/main/docs/assets/openclaw-logo-text-dark.png">
        <img src="https://raw.githubusercontent.com/openclaw/openclaw/main/docs/assets/openclaw-logo-text.png" alt="OpenClaw" width="500">
    </picture>
</p>

<p align="center">
  <strong>EXFOLIATE! EXFOLIATE!</strong>
</p>

<p align="center">
  <a href="https://github.com/openclaw/openclaw/actions/workflows/ci.yml?branch=main"><img src="https://img.shields.io/github/actions/workflow/status/openclaw/openclaw/ci.yml?branch=main&style=for-the-badge" alt="CI status"></a>
  <a href="https://github.com/openclaw/openclaw/releases"><img src="https://img.shields.io/github/v/release/openclaw/openclaw?include_prereleases&style=for-the-badge" alt="GitHub release"></a>
  <a href="https://discord.gg/clawd"><img src="https://img.shields.io/discord/1456350064065904867?label=Discord&logo=discord&logoColor=white&color=5865F2&style=for-the-badge" alt="Discord"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="MIT License"></a>
</p>

---

## 목차

- [OpenClaw이란 무엇인가?](#openclaw이란-무엇인가)
- [왜 OpenClaw인가? — 다른 AI 비서와의 차이점](#왜-openclaw인가--다른-ai-비서와의-차이점)
- [핵심 기능 한눈에 보기](#핵심-기능-한눈에-보기)
- [프로젝트의 역사](#프로젝트의-역사)
- [설치 가이드](#설치-가이드)
  - [사전 준비사항](#사전-준비사항)
  - [방법 1: npm 설치 (권장)](#방법-1-npm-설치-권장)
  - [방법 2: Docker 설치](#방법-2-docker-설치)
  - [방법 3: 소스 코드에서 빌드 (개발자용)](#방법-3-소스-코드에서-빌드-개발자용)
  - [방법 4: 관리형 클라우드 호스팅](#방법-4-관리형-클라우드-호스팅)
- [빠른 시작 (5분 안에 시작하기)](#빠른-시작-5분-안에-시작하기)
- [메시징 채널 연결하기](#메시징-채널-연결하기)
  - [WhatsApp 연결](#whatsapp-연결)
  - [Telegram 연결 (입문자 추천)](#telegram-연결-입문자-추천)
  - [Slack 연결](#slack-연결)
  - [Discord 연결](#discord-연결)
  - [기타 채널](#기타-채널)
- [음성 기능](#음성-기능)
- [캔버스 (시각적 작업공간)](#캔버스-시각적-작업공간)
- [스킬(Skills) 시스템과 ClawHub](#스킬skills-시스템과-clawhub)
- [AI 모델 설정](#ai-모델-설정)
- [설정 파일 가이드](#설정-파일-가이드)
- [채팅 명령어 모음](#채팅-명령어-모음)
- [동반 앱 (macOS / iOS / Android)](#동반-앱-macos--ios--android)
- [보안 가이드 — 반드시 읽으세요](#보안-가이드--반드시-읽으세요)
- [비용 안내](#비용-안내)
- [아키텍처 개요](#아키텍처-개요)
- [문제 해결 (FAQ)](#문제-해결-faq)
- [핵심 기능 상세 목록](#핵심-기능-상세-목록)
- [문서 및 참고자료](#문서-및-참고자료)
- [커뮤니티 및 기여](#커뮤니티-및-기여)
- [Star History](#star-history)

---

## OpenClaw이란 무엇인가?

**OpenClaw**은 **무료 오픈소스 셀프호스팅 AI 개인 비서**입니다. ChatGPT나 Siri처럼 브라우저나 특정 기기에서만 작동하는 AI와 달리, OpenClaw은 **여러분의 컴퓨터(또는 서버)에서 24시간 365일** 돌아가며, 여러분이 이미 쓰고 있는 메신저(WhatsApp, Telegram, Slack, Discord 등)를 통해 소통합니다.

쉽게 비유하자면, **컴퓨터 앞에 앉아 24시간 일해주는 똑똑한 비서**를 한 명 고용한 것과 같습니다. 이 비서는:

- 여러분의 메시지에 답변하고
- 웹을 검색하고
- 이메일을 보내고
- 파일을 읽고 쓰고
- 일정을 관리하고
- 스마트홈 기기를 제어하고
- 코드를 실행하고
- 그리고 훨씬 더 많은 일을 할 수 있습니다

**가장 중요한 점:** 여러분의 데이터는 여러분의 기기에 머물러 있습니다. API 호출만이 외부로 나갑니다. 어떤 AI 모델을 사용할지도 여러분이 직접 선택합니다.

> **한 줄 요약:** OpenClaw은 ChatGPT가 "대화하는 AI"라면, 실제로 "행동하는 AI 에이전트"입니다.

[공식 웹사이트](https://openclaw.ai) · [공식 문서](https://docs.openclaw.ai) · [DeepWiki](https://deepwiki.com/openclaw/openclaw) · [시작하기](https://docs.openclaw.ai/start/getting-started) · [FAQ](https://docs.openclaw.ai/start/faq) · [Discord](https://discord.gg/clawd)

---

## 왜 OpenClaw인가? — 다른 AI 비서와의 차이점

| 구분 | OpenClaw | ChatGPT | Siri / Alexa |
|------|----------|---------|--------------|
| **작동 방식** | 내 기기에서 직접 실행 (셀프호스팅) | OpenAI 클라우드 서버 | Apple/Amazon 클라우드 서버 |
| **자율 행동** | 파일 조작, 셸 명령, 웹 브라우징 등 실제 작업 수행 | 답변과 제안만 (실행은 사용자가) | 사전 정의된 통합만 가능 |
| **기억력** | 디스크에 영구 저장, 직접 검사 가능 | 제한적 대화 기억 | 거의 없음 |
| **개인정보** | 데이터가 내 기기에 보관 | 벤더 서버를 거침 | 벤더가 처리 |
| **AI 모델 선택** | Anthropic, OpenAI, xAI, 로컬 모델 등 자유 선택 | OpenAI 모델만 | 자체 모델만 |
| **확장성** | 누구나 만드는 오픈소스 스킬 | 제한된 플러그인 | 벤더 통제 |
| **비용** | 소프트웨어 무료 + API 비용 $5-30/월 | 구독 $20/월 | 기기 포함 무료 |
| **상시 가동** | 24/7 데몬으로 상시 실행 | 브라우저 세션 한정 | 음성만 상시 |

---

## 핵심 기능 한눈에 보기

### 🗨️ 멀티채널 메시징
WhatsApp에서 시작한 대화를 Telegram에서 이어가세요. 모든 채널의 대화가 하나의 메모리로 통합됩니다.

**지원 채널:** WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, BlueBubbles, Microsoft Teams, Matrix, Zalo, WebChat 등

### 🎤 음성 기능
"Hey OpenClaw"으로 깨우고, 손을 쓰지 않고도 대화하세요. ElevenLabs 기반의 자연스러운 음성 합성을 지원합니다.

### 🖼️ 캔버스 (라이브 시각적 작업공간)
AI가 직접 HTML/CSS/JS 콘텐츠를 생성하여 보여주는 인터랙티브 화면입니다. A2UI (Agent-to-User Interface)라고도 불립니다.

### 🧠 영구 기억
대화 내용이 디스크에 파일로 저장되어, 재시작해도 여러분을 기억합니다. 시간이 지날수록 더 개인화됩니다.

### 🤖 자율 에이전트
파일 읽기/쓰기, 셸 명령 실행, 웹 브라우징, 크론 작업, 이메일 연동 등을 자율적으로 수행합니다.

### 🔀 AI 모델 자유 선택
Anthropic(Claude), OpenAI(GPT), xAI(Grok), 로컬 모델(Ollama) 등 원하는 AI를 선택하세요. 하나가 다운되면 자동으로 다른 모델로 전환됩니다.

### 🧩 50+ 통합 서비스
Apple Notes, Google Workspace(Gmail/Calendar/Drive), 스마트홈(Philips Hue, Home Assistant), Notion, Obsidian, Trello 등

---

## 프로젝트의 역사

OpenClaw은 오스트리아 개발자 **Peter Steinberger**(@steipete)가 2025년 11월에 처음 공개했습니다. 처음에는 **Clawdbot**이라는 이름이었으나, Anthropic의 상표권 이슈로 **Moltbot**으로 개명했다가, 최종적으로 **OpenClaw**이 되었습니다. "바닷가재(lobster)"를 모티프로 한 정체성은 처음부터 지금까지 유지되고 있습니다.

- **GitHub 스타 180,000+개** — 역대 가장 빠르게 성장한 GitHub 저장소 중 하나 (60일 만에 9K → 179K)
- **376+ 기여자**, **9,100+ 커밋**
- **MIT 라이선스** — 완전 무료, 오픈소스
- Lex Fridman Podcast #491에 출연, Meta와 OpenAI로부터 인수 제안을 받음

---

## 설치 가이드

### 사전 준비사항

| 항목 | 요구 사항 |
|------|-----------|
| **Node.js** | 22.12.0 이상 (LTS) |
| **운영체제** | macOS, Linux, Windows (WSL2 강력 권장) |
| **AI API 키** | Anthropic, OpenAI 등 최소 1개 |
| **패키지 매니저** | npm, pnpm, 또는 bun |

> **Windows 사용자 주의:** 반드시 **WSL2**(Windows Subsystem for Linux)를 통해 설치하세요. 네이티브 Windows 환경은 지원이 제한됩니다.
>
> WSL2 설치: PowerShell을 관리자 권한으로 열고 `wsl --install` 실행

#### Node.js 버전 확인

```bash
node --version  # v22.12.0 이상이어야 합니다
```

Node.js가 없다면 [nodejs.org](https://nodejs.org/)에서 설치하세요.

### 방법 1: npm 설치 (권장)

대부분의 사용자에게 가장 쉬운 방법입니다.

```bash
# 1. OpenClaw 설치
npm install -g openclaw@latest
# 또는: pnpm add -g openclaw@latest

# 2. 온보딩 마법사 실행 (대화형으로 모든 설정을 안내)
openclaw onboard --install-daemon
```

온보딩 마법사가 다음을 단계별로 안내합니다:
1. AI 모델 제공자 선택 및 API 키 입력
2. Gateway 설정
3. 메시징 채널 연결
4. 스킬 설치
5. 데몬 서비스 등록 (시스템 재부팅 후에도 자동 실행)

### 방법 2: Docker 설치

서버에서 실행하거나 환경 격리가 필요할 때 적합합니다.

```bash
# Docker Compose로 실행
docker compose up -d

# 또는 직접 Docker 실행
docker run --read-only --cap-drop=ALL \
  -v openclaw-data:/app/data \
  openclaw/openclaw:latest
```

자세한 내용: [Docker 설치 가이드](https://docs.openclaw.ai/install/docker)

### 방법 3: 소스 코드에서 빌드 (개발자용)

OpenClaw을 수정하거나 개발에 참여하고 싶은 경우:

```bash
git clone https://github.com/openclaw/openclaw.git
cd openclaw

pnpm install
pnpm ui:build   # UI 의존성 자동 설치
pnpm build

pnpm openclaw onboard --install-daemon

# 개발 모드 (TS 변경 시 자동 리로드)
pnpm gateway:watch
```

> `pnpm openclaw ...`은 TypeScript를 직접 실행(tsx)합니다.
> `pnpm build`는 Node/패키지 바이너리용 `dist/`를 생성합니다.

### 방법 4: 관리형 클라우드 호스팅

직접 서버를 관리하고 싶지 않다면, 관리형 호스팅 서비스를 이용하세요 (API 키 설정 불필요, 월 $39부터):
- xCloud
- DigitalOcean
- Zeabur

---

## 빠른 시작 (5분 안에 시작하기)

설치가 완료되었다면, 바로 사용해 보세요:

```bash
# 1. Gateway 시작
openclaw gateway --port 18789 --verbose

# 2. 메시지 보내기
openclaw message send --to +821012345678 --message "안녕, OpenClaw에서 보낸 메시지야"

# 3. AI 에이전트에게 작업 요청
openclaw agent --message "오늘 할일 목록 만들어줘" --thinking high
```

**가장 빠른 체험 방법:** 채널 설정 없이 브라우저에서 바로 사용하려면 **Control UI**를 열면 됩니다. Gateway를 시작한 후 웹 브라우저에서 `http://127.0.0.1:18789`에 접속하세요.

업그레이드가 필요하면: [업데이트 가이드](https://docs.openclaw.ai/install/updating) 참고, `openclaw doctor` 실행으로 상태 점검

### 업데이트 채널

| 채널 | 설명 | npm 태그 |
|------|------|----------|
| **stable** | 정식 릴리스 (`vYYYY.M.D`) | `latest` |
| **beta** | 프리릴리스 (`vYYYY.M.D-beta.N`) | `beta` |
| **dev** | `main` 브랜치 최신 | `dev` |

```bash
# 채널 변경
openclaw update --channel stable|beta|dev
```

---

## 메시징 채널 연결하기

OpenClaw의 핵심은 **이미 사용하는 메신저**를 통해 AI와 소통하는 것입니다. 여러 채널을 동시에 연결할 수 있으며, 모든 채널의 대화 맥락이 공유됩니다.

### WhatsApp 연결

1. 디바이스 연결:
   ```bash
   openclaw channels login
   # QR 코드가 표시됩니다 — 휴대폰으로 스캔하세요
   ```
2. 설정 파일에서 허용 목록 지정:
   ```json5
   {
     channels: {
       whatsapp: {
         allowFrom: ["+821012345678"]  // 본인 번호
       }
     }
   }
   ```
3. 그룹 허용: `channels.whatsapp.groups`에 `"*"` 포함 시 모든 그룹 허용

자세한 설정: [WhatsApp 가이드](https://docs.openclaw.ai/channels/whatsapp)

### Telegram 연결 (입문자 추천)

Telegram은 공식 Bot API가 있어 **가장 쉽게 연결**할 수 있어, 처음 시작하는 분께 추천합니다.

1. [@BotFather](https://t.me/BotFather)에서 봇 생성 후 토큰 발급
2. 환경변수 또는 설정 파일에 토큰 추가:
   ```bash
   # 방법 A: 환경변수
   export TELEGRAM_BOT_TOKEN="123456:ABCDEF"
   ```
   ```json5
   // 방법 B: 설정 파일 (~/.openclaw/openclaw.json)
   {
     channels: {
       telegram: {
         botToken: "123456:ABCDEF"
       }
     }
   }
   ```
3. Gateway 재시작 후 Telegram에서 봇에게 메시지 전송

자세한 설정: [Telegram 가이드](https://docs.openclaw.ai/channels/telegram)

### Slack 연결

1. Slack 앱 생성 및 봇 토큰 발급
2. 환경변수 설정:
   ```bash
   export SLACK_BOT_TOKEN="xoxb-..."
   export SLACK_APP_TOKEN="xapp-..."
   ```

자세한 설정: [Slack 가이드](https://docs.openclaw.ai/channels/slack)

### Discord 연결

1. Discord 개발자 포털에서 봇 생성
2. 설정:
   ```json5
   {
     channels: {
       discord: {
         token: "봇_토큰_여기에"
       }
     }
   }
   ```

자세한 설정: [Discord 가이드](https://docs.openclaw.ai/channels/discord)

### 기타 채널

| 채널 | 가이드 |
|------|--------|
| Google Chat | [설정 가이드](https://docs.openclaw.ai/channels/googlechat) |
| Signal | [설정 가이드](https://docs.openclaw.ai/channels/signal) — `signal-cli` 필요 |
| BlueBubbles (iMessage) | [설정 가이드](https://docs.openclaw.ai/channels/bluebubbles) — 권장 iMessage 통합 |
| iMessage (레거시) | [설정 가이드](https://docs.openclaw.ai/channels/imessage) — macOS 전용 |
| Microsoft Teams | [설정 가이드](https://docs.openclaw.ai/channels/msteams) |
| Matrix | [설정 가이드](https://docs.openclaw.ai/channels/matrix) — 확장 채널 |
| Zalo | [설정 가이드](https://docs.openclaw.ai/channels/zalo) — 확장 채널 |
| WebChat | [설정 가이드](https://docs.openclaw.ai/web/webchat) — Gateway WebSocket 사용, 별도 설정 불필요 |

---

## 음성 기능

OpenClaw은 단순한 텍스트 채팅을 넘어 **음성으로 AI와 대화**할 수 있습니다.

### Voice Wake (음성 깨우기)
- **"Hey OpenClaw"** 호출어로 언제든 AI를 깨울 수 있습니다
- macOS, iOS, Android에서 지원
- 항상 대기 상태로 음성을 감지

### Talk Mode (대화 모드)
- 연속 대화가 가능한 핸즈프리 모드
- AI가 말하는 도중에 끼어들기(인터럽션) 가능
- 자연스러운 양방향 대화 경험

### 음성 합성 (TTS)
- **ElevenLabs** 기반의 자연스러운 음성 출력
- 설정: 환경변수 `ELEVENLABS_API_KEY` 추가

자세한 설정: [Voice Wake 가이드](https://docs.openclaw.ai/nodes/voicewake) · [Talk Mode 가이드](https://docs.openclaw.ai/nodes/talk)

---

## 캔버스 (시각적 작업공간)

**Canvas**는 AI가 직접 제어하는 시각적 작업공간입니다. AI가 HTML/CSS/JS 콘텐츠를 실시간으로 생성하여 보여줍니다.

**A2UI (Agent-to-User Interface)** 라고도 불리며, AI가 사용자에게 보여줄 인터랙티브 UI를 즉석에서 만들어냅니다.

**플랫폼별 구현:**
- macOS: 네이티브 WebKit (WKWebView)
- iOS: SwiftUI 래핑
- Android: WebView

사용 예시:
- 데이터 시각화 차트 생성
- 인터랙티브 폼 제공
- 실시간 대시보드 표시

자세한 설정: [Canvas 가이드](https://docs.openclaw.ai/platforms/mac/canvas)

---

## 스킬(Skills) 시스템과 ClawHub

**스킬(Skills)** 은 OpenClaw의 핵심 확장 메커니즘입니다. AI에게 특정 작업 수행 방법을 가르치는 파일 묶음으로, 누구나 만들고 공유할 수 있습니다.

### 스킬의 구조

각 스킬은 `SKILL.md` 파일을 포함한 디렉토리입니다:

```yaml
name: hello_world
description: 인사하는 간단한 스킬
emoji: 👋
---
# Hello World 스킬
사용자가 인사를 요청하면, "안녕하세요!"라고 답해주세요.
```

- 스킬 위치: `~/.openclaw/workspace/skills/<스킬이름>/SKILL.md`
- Gateway 시작 시 자동으로 발견되어 로드됩니다
- TypeScript로 더 복잡한 로직도 작성 가능

### ClawHub — 스킬 마켓플레이스

[**ClawHub**](https://clawhub.com)은 커뮤니티가 만든 스킬을 검색하고 설치할 수 있는 공개 레지스트리입니다.

- **5,700+ 커뮤니티 스킬** 등록됨
- 벡터 임베딩 기반 의미 검색 지원
- 버전 관리(semver), 별점, 댓글
- AI가 자동으로 필요한 스킬을 검색하여 설치 가능

> **보안 주의:** ClawHub의 스킬을 설치하기 전에 반드시 소스 코드를 확인하세요. 일부 스킬에서 API 키 노출 등의 보안 결함이 발견된 바 있습니다. 버전을 고정하고, 게시자를 확인하며, `openclaw security audit`를 정기적으로 실행하세요.

---

## AI 모델 설정

OpenClaw은 **특정 AI 모델에 종속되지 않습니다.** 원하는 모델을 자유롭게 선택하세요.

### 지원 제공자

| 제공자 | 모델 예시 | 인증 방식 |
|--------|-----------|-----------|
| **Anthropic** | Claude Opus 4.6, Sonnet 4.5 | API 키 또는 OAuth (Pro/Max 구독) |
| **OpenAI** | GPT-5.2, Codex | API 키 또는 OAuth |
| **xAI** | Grok | API 키 |
| **Google** | Gemini | API 키 |
| **로컬 모델** | Ollama, llama.cpp 등 | 없음 (로컬 실행) |
| **OpenRouter** | 여러 모델 중개 | API 키 |

### 권장 설정

개발자의 공식 권장 사항: **Anthropic Pro/Max (100/200) + Opus 4.6** — 긴 문맥 처리 능력과 프롬프트 인젝션 방어가 뛰어남

### 모델 설정 방법

```json5
// ~/.openclaw/openclaw.json
{
  agent: {
    model: "anthropic/claude-opus-4-6"
  }
}
```

### 모델 자동 전환 (Failover)

하나의 API가 다운되면 자동으로 다른 모델로 전환됩니다.

자세한 설정: [모델 가이드](https://docs.openclaw.ai/concepts/models) · [모델 Failover](https://docs.openclaw.ai/concepts/model-failover)

---

## 설정 파일 가이드

OpenClaw의 모든 설정은 `~/.openclaw/openclaw.json` 파일 하나에서 관리됩니다.

### 최소 설정 (시작용)

```json5
{
  agent: {
    model: "anthropic/claude-opus-4-6"
  }
}
```

### 환경변수 (.env 파일)

API 키 등 민감한 정보는 `.env` 파일로 관리합니다.

```bash
# ~/.openclaw/.env 또는 프로젝트 루트의 .env

# Gateway 인증 (loopback 이외 바인딩 시 필수)
OPENCLAW_GATEWAY_TOKEN=change-me-to-a-long-random-token

# AI 모델 제공자 API 키 (최소 1개 필요)
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# 채널 토큰 (사용하는 채널만)
# TELEGRAM_BOT_TOKEN=123456:ABCDEF...
# DISCORD_BOT_TOKEN=...
# SLACK_BOT_TOKEN=xoxb-...
# SLACK_APP_TOKEN=xapp-...

# 음성/도구 (선택)
# ELEVENLABS_API_KEY=...
# BRAVE_API_KEY=...
```

### 환경변수 우선순위

프로세스 환경 > `./.env` > `~/.openclaw/.env` > `openclaw.json`의 `env` 블록

### 전체 설정 레퍼런스

[전체 설정 키 및 예시 보기](https://docs.openclaw.ai/gateway/configuration)

---

## 채팅 명령어 모음

WhatsApp, Telegram, Slack, Discord, Google Chat, Microsoft Teams, WebChat에서 사용 가능한 명령어입니다:

| 명령어 | 설명 |
|--------|------|
| `/status` | 현재 세션 상태 (모델, 토큰 수, 비용) |
| `/new` 또는 `/reset` | 세션 초기화 (새 대화 시작) |
| `/compact` | 세션 컨텍스트 압축 (요약) |
| `/think <레벨>` | 사고 깊이 설정: off, minimal, low, medium, high, xhigh |
| `/verbose on\|off` | 상세 출력 토글 |
| `/usage off\|tokens\|full` | 응답마다 사용량 표시 |
| `/restart` | Gateway 재시작 (그룹에서는 소유자만) |
| `/activation mention\|always` | 그룹 활성화 모드 전환 |
| `/elevated on\|off` | 호스트 권한 확장 토글 (허용된 경우) |

---

## 동반 앱 (macOS / iOS / Android)

Gateway만으로도 충분히 잘 작동하지만, 동반 앱을 통해 더 풍부한 경험을 할 수 있습니다. 모든 앱은 **선택 사항**입니다.

### macOS (OpenClaw.app)

- 메뉴 바에서 Gateway 상태 확인 및 제어
- Voice Wake + 푸시-투-토크 오버레이
- WebChat + 디버그 도구
- SSH를 통한 원격 Gateway 제어

자세한 설정: [macOS 가이드](https://docs.openclaw.ai/platforms/macos)

### iOS 노드

- Bridge를 통해 노드로 페어링
- 음성 트리거, Canvas 표면
- `openclaw nodes …` 명령으로 제어

자세한 설정: [iOS 가이드](https://docs.openclaw.ai/platforms/ios)

### Android 노드

- iOS와 동일한 Bridge/페어링 방식
- Canvas, 카메라, 화면 캡처 지원

자세한 설정: [Android 가이드](https://docs.openclaw.ai/platforms/android)

---

## 보안 가이드 — 반드시 읽으세요

OpenClaw은 실제 메시징 채널과 시스템 리소스에 접근합니다. **보안 설정을 소홀히 하면 심각한 위험**이 발생할 수 있습니다.

### 절대 하지 말아야 할 것

1. **Gateway를 공개 인터넷에 노출하지 마세요.** 기본값인 loopback(127.0.0.1) 바인딩을 유지하세요.
2. 원격 접근이 필요하면 **SSH 터널** 또는 **Tailscale Serve/Funnel**을 사용하세요.

### 반드시 해야 할 것

1. **모든 비밀 키를 환경변수로 관리하세요.** 설정 파일에 직접 넣지 마세요.
2. **API 키에 지출 한도를 설정하세요.**
3. **DM 보안 정책을 설정하세요:**
   - 기본값 `dmPolicy="pairing"`: 모르는 발신자는 페어링 코드를 받고, 승인 전까지 메시지가 처리되지 않음
   - 승인: `openclaw pairing approve <채널> <코드>`
   - **절대로** `dmPolicy="open"` + `allowFrom: ["*"]`로 설정하지 마세요 (모든 사람이 AI에 접근 가능)
4. **ClawHub 스킬은 설치 전에 소스를 검토하세요.**
5. **`openclaw security audit`를 정기적으로 실행하세요.**
6. **`openclaw doctor`로 잘못된 설정을 점검하세요.**

### 보안 모델 요약

| 세션 유형 | 기본 동작 | 권장 설정 |
|-----------|-----------|-----------|
| **main** (1:1 DM) | 호스트에서 직접 실행, 전체 접근 | 본인만 사용하므로 기본값 유지 |
| **non-main** (그룹/채널) | 호스트에서 실행 | `sandbox.mode: "non-main"` 설정으로 Docker 격리 |

### 프롬프트 인젝션 주의

이메일이나 웹 콘텐츠를 읽는 AI 에이전트는 숨겨진 악성 텍스트에 의해 조작될 수 있습니다. 외부 데이터를 처리하는 스킬 사용 시 주의하세요.

### Docker 보안 강화

```bash
docker run --read-only --cap-drop=ALL \
  -v openclaw-data:/app/data \
  openclaw/openclaw:latest
```

자세한 보안 가이드: [보안 문서](https://docs.openclaw.ai/gateway/security) · [SECURITY.md](SECURITY.md)

### 취약점 보고

보안 취약점을 발견하셨다면:
- 이메일: **security@openclaw.ai**
- 또는 해당 GitHub 저장소에서 비공개 보고

---

## 비용 안내

### 소프트웨어 비용

**완전 무료.** MIT 라이선스 오픈소스입니다. 구독도, 프리미엄 티어도, 광고도 없습니다.

### API 사용료 (실제 비용)

여러분이 선택한 AI 모델 제공자(Anthropic, OpenAI 등)에 지불하는 API 호출 비용입니다:

| 사용 패턴 | 월 예상 비용 |
|-----------|-------------|
| 가벼운 사용 (간단한 질답) | $1 이하 |
| 일반적 개인 사용 | $5 ~ $30 |
| 파워 유저 / 팀 사용 | $50 ~ $200 |
| 헤비 자동화 | $200 ~ $500+ |

### 비용을 높이는 요인

- 스크린샷을 활용한 브라우저 자동화 (비전 모델 API 호출)
- 복잡한 다단계 추론
- 높은 메시지 볼륨

### 비용 절약 팁

- 단순한 작업은 저렴한 모델(예: Haiku)로 라우팅하세요
- `thinking` 레벨을 작업 복잡도에 맞게 조절하세요
- `/compact` 명령으로 긴 대화의 컨텍스트를 압축하세요

---

## 아키텍처 개요

OpenClaw이 어떻게 작동하는지 한눈에 보여주는 구조입니다:

```
메시징 채널 (WhatsApp, Telegram, Slack, Discord, Signal ...)
    ↓
Gateway (ws://127.0.0.1:18789)
    ├── 세션 관리
    ├── 채널 라우팅
    ├── 도구 실행
    └── 크론 / 웹훅
    ↓
    ├── Pi 에이전트 (RPC)
    ├── CLI (openclaw)
    ├── WebChat UI
    └── macOS / iOS / Android 노드
```

### 핵심 서브시스템

- **[Gateway WebSocket 네트워크](https://docs.openclaw.ai/concepts/architecture)** — 클라이언트, 도구, 이벤트를 위한 단일 WS 제어 플레인
- **[Tailscale 통합](https://docs.openclaw.ai/gateway/tailscale)** — Serve/Funnel을 통한 원격 접근
- **[브라우저 제어](https://docs.openclaw.ai/tools/browser)** — OpenClaw 전용 Chrome/Chromium CDP 제어
- **[Canvas + A2UI](https://docs.openclaw.ai/platforms/mac/canvas)** — AI가 구동하는 시각적 작업공간
- **[Voice Wake](https://docs.openclaw.ai/nodes/voicewake) + [Talk Mode](https://docs.openclaw.ai/nodes/talk)** — 상시 음성 인식 및 대화
- **[노드 시스템](https://docs.openclaw.ai/nodes)** — 카메라, 화면 녹화, 위치, 알림 등

### 원격 Gateway (서버에서 실행하기)

Gateway를 소형 Linux 서버에서 실행하면서, macOS/iOS/Android 디바이스 노드를 페어링하여 디바이스별 기능(카메라, 화면 녹화 등)을 활용할 수 있습니다.

- **Gateway 호스트:** exec 도구와 채널 연결 실행
- **디바이스 노드:** `system.run`, 카메라, 화면 녹화, 알림 등 디바이스 로컬 작업 실행

자세한 설정: [원격 접근 가이드](https://docs.openclaw.ai/gateway/remote) · [노드 가이드](https://docs.openclaw.ai/nodes)

### Tailscale 연동

OpenClaw은 **Tailscale Serve** (tailnet 전용) 또는 **Funnel** (공개)을 자동 설정하면서 Gateway는 loopback에 바인딩된 상태를 유지합니다.

| 모드 | 설명 |
|------|------|
| `off` | Tailscale 자동화 없음 (기본값) |
| `serve` | tailnet 전용 HTTPS (`tailscale serve`) |
| `funnel` | 공개 HTTPS (`tailscale funnel`) — 비밀번호 인증 필수 |

자세한 설정: [Tailscale 가이드](https://docs.openclaw.ai/gateway/tailscale)

---

## 문제 해결 (FAQ)

### Q: Gateway가 시작되지 않아요

```bash
# 상태 점검
openclaw doctor

# 로그 확인
openclaw gateway --verbose
```

### Q: WhatsApp/Telegram 연결이 끊어져요

```bash
# 채널 문제 진단
openclaw doctor

# WhatsApp 재로그인
openclaw channels login
```

### Q: API 비용이 예상보다 많이 나와요

- `/usage full` 명령으로 응답별 비용을 확인하세요
- `/compact`로 긴 대화 압축
- 더 저렴한 모델로 전환 검토
- API 제공자 대시보드에서 지출 한도 설정

### Q: Windows에서 설치가 안 돼요

- **WSL2를 반드시 사용하세요.** 네이티브 Windows는 제한적으로 지원됩니다.
- PowerShell 관리자: `wsl --install`
- WSL2 Ubuntu에서 Node.js 설치 후 OpenClaw 설치

### Q: 그룹 채팅에서 AI가 모든 메시지에 반응해요

- `/activation mention`으로 멘션 시에만 반응하도록 설정하세요
- 그룹 허용 목록으로 특정 그룹만 활성화하세요

더 많은 문제 해결: [트러블슈팅 가이드](https://docs.openclaw.ai/channels/troubleshooting)

---

## 핵심 기능 상세 목록

### 코어 플랫폼

- [Gateway WS 제어 플레인](https://docs.openclaw.ai/gateway): 세션, 프레즌스, 설정, 크론, 웹훅, [Control UI](https://docs.openclaw.ai/web), [Canvas 호스트](https://docs.openclaw.ai/platforms/mac/canvas#canvas-a2ui)
- [CLI 인터페이스](https://docs.openclaw.ai/tools/agent-send): gateway, agent, send, [wizard](https://docs.openclaw.ai/start/wizard), [doctor](https://docs.openclaw.ai/gateway/doctor)
- [Pi 에이전트 런타임](https://docs.openclaw.ai/concepts/agent): RPC 모드, 도구 스트리밍, 블록 스트리밍
- [세션 모델](https://docs.openclaw.ai/concepts/session): `main` 직접 채팅, 그룹 격리, 활성화 모드, 큐 모드, 리플라이백
- [미디어 파이프라인](https://docs.openclaw.ai/nodes/images): 이미지/오디오/비디오, 트랜스크립션, 크기 제한

### 채널

[WhatsApp](https://docs.openclaw.ai/channels/whatsapp) (Baileys) · [Telegram](https://docs.openclaw.ai/channels/telegram) (grammY) · [Slack](https://docs.openclaw.ai/channels/slack) (Bolt) · [Discord](https://docs.openclaw.ai/channels/discord) (discord.js) · [Google Chat](https://docs.openclaw.ai/channels/googlechat) · [Signal](https://docs.openclaw.ai/channels/signal) (signal-cli) · [BlueBubbles](https://docs.openclaw.ai/channels/bluebubbles) (iMessage) · [iMessage Legacy](https://docs.openclaw.ai/channels/imessage) · [Microsoft Teams](https://docs.openclaw.ai/channels/msteams) · [Matrix](https://docs.openclaw.ai/channels/matrix) · [Zalo](https://docs.openclaw.ai/channels/zalo) · [WebChat](https://docs.openclaw.ai/web/webchat)

### 앱 및 노드

- [macOS 앱](https://docs.openclaw.ai/platforms/macos): 메뉴 바, Voice Wake/PTT, Talk Mode, WebChat, 원격 제어
- [iOS 노드](https://docs.openclaw.ai/platforms/ios): Canvas, Voice Wake, Talk Mode, 카메라, 화면 녹화
- [Android 노드](https://docs.openclaw.ai/platforms/android): Canvas, Talk Mode, 카메라, 화면 녹화, SMS

### 도구 및 자동화

- [브라우저 제어](https://docs.openclaw.ai/tools/browser): Chrome/Chromium CDP 제어, 스냅샷, 프로필
- [Canvas](https://docs.openclaw.ai/platforms/mac/canvas): A2UI push/reset, eval, 스냅샷
- [노드](https://docs.openclaw.ai/nodes): 카메라, 화면 녹화, 위치, 알림
- [크론 + 웨이크업](https://docs.openclaw.ai/automation/cron-jobs) · [웹훅](https://docs.openclaw.ai/automation/webhook) · [Gmail Pub/Sub](https://docs.openclaw.ai/automation/gmail-pubsub)
- [스킬 플랫폼](https://docs.openclaw.ai/tools/skills): 번들, 관리형, 워크스페이스 스킬

### 런타임 및 안전

- [채널 라우팅](https://docs.openclaw.ai/concepts/channel-routing), [재시도 정책](https://docs.openclaw.ai/concepts/retry), [스트리밍/청킹](https://docs.openclaw.ai/concepts/streaming)
- [프레즌스](https://docs.openclaw.ai/concepts/presence), [타이핑 인디케이터](https://docs.openclaw.ai/concepts/typing-indicators), [사용량 추적](https://docs.openclaw.ai/concepts/usage-tracking)
- [모델 관리](https://docs.openclaw.ai/concepts/models), [모델 Failover](https://docs.openclaw.ai/concepts/model-failover), [세션 프루닝](https://docs.openclaw.ai/concepts/session-pruning)
- [보안](https://docs.openclaw.ai/gateway/security), [트러블슈팅](https://docs.openclaw.ai/channels/troubleshooting)

### 에이전트 간 통신 (sessions_* 도구)

여러 에이전트(세션) 간의 협업이 가능합니다:
- `sessions_list` — 활성 세션(에이전트) 목록 조회
- `sessions_history` — 세션의 대화 로그 조회
- `sessions_send` — 다른 세션에 메시지 전송

자세한 설정: [세션 도구 가이드](https://docs.openclaw.ai/concepts/session-tool)

---

## 문서 및 참고자료

### 시작하기

| 문서 | 설명 |
|------|------|
| [공식 문서 인덱스](https://docs.openclaw.ai) | 전체 문서 탐색 |
| [시작 가이드](https://docs.openclaw.ai/start/getting-started) | 처음 시작하는 분을 위한 가이드 |
| [온보딩 마법사](https://docs.openclaw.ai/start/wizard) | 대화형 설정 안내 |
| [쇼케이스](https://docs.openclaw.ai/start/showcase) | 활용 사례 모음 |
| [FAQ](https://docs.openclaw.ai/start/faq) | 자주 묻는 질문 |

### 아키텍처 및 설정

| 문서 | 설명 |
|------|------|
| [아키텍처 개요](https://docs.openclaw.ai/concepts/architecture) | Gateway + 프로토콜 구조 |
| [전체 설정 레퍼런스](https://docs.openclaw.ai/gateway/configuration) | 모든 설정 키와 예시 |
| [Gateway 운영 가이드](https://docs.openclaw.ai/gateway) | Gateway 실행 및 관리 |
| [웹 인터페이스](https://docs.openclaw.ai/web) | Control UI / WebChat |
| [원격 접근](https://docs.openclaw.ai/gateway/remote) | SSH 터널 / Tailscale |

### 플랫폼별 가이드

| 플랫폼 | 가이드 |
|--------|--------|
| [macOS](https://docs.openclaw.ai/platforms/macos) | 메뉴 바 앱, Voice Wake |
| [iOS](https://docs.openclaw.ai/platforms/ios) | 노드 페어링, Canvas |
| [Android](https://docs.openclaw.ai/platforms/android) | 노드 페어링, Canvas |
| [Windows (WSL2)](https://docs.openclaw.ai/platforms/windows) | WSL2 설치 가이드 |
| [Linux](https://docs.openclaw.ai/platforms/linux) | 서버 배포 가이드 |

### 고급 문서

- [Discovery + transports](https://docs.openclaw.ai/gateway/discovery) · [Bonjour/mDNS](https://docs.openclaw.ai/gateway/bonjour)
- [Gateway 페어링](https://docs.openclaw.ai/gateway/pairing) · [Control UI](https://docs.openclaw.ai/web/control-ui)
- [헬스 체크](https://docs.openclaw.ai/gateway/health) · [로깅](https://docs.openclaw.ai/logging)
- [에이전트 루프](https://docs.openclaw.ai/concepts/agent-loop) · [큐](https://docs.openclaw.ai/concepts/queue)
- [TypeBox 스키마](https://docs.openclaw.ai/concepts/typebox) · [RPC 어댑터](https://docs.openclaw.ai/reference/rpc)

### 워크스페이스 및 스킬

- [스킬 설정](https://docs.openclaw.ai/tools/skills-config) · [기본 AGENTS](https://docs.openclaw.ai/reference/AGENTS.default)
- 템플릿: [AGENTS](https://docs.openclaw.ai/reference/templates/AGENTS) · [BOOTSTRAP](https://docs.openclaw.ai/reference/templates/BOOTSTRAP) · [IDENTITY](https://docs.openclaw.ai/reference/templates/IDENTITY) · [SOUL](https://docs.openclaw.ai/reference/templates/SOUL) · [TOOLS](https://docs.openclaw.ai/reference/templates/TOOLS) · [USER](https://docs.openclaw.ai/reference/templates/USER)

### 외부 튜토리얼 및 리소스

- [Codecademy: OpenClaw 튜토리얼](https://www.codecademy.com/article/open-claw-tutorial-installation-to-first-chat-setup) — 설치부터 첫 대화까지
- [DigitalOcean: OpenClaw 실행 가이드](https://www.digitalocean.com/community/tutorials/how-to-run-openclaw) — 서버 배포
- [awesome-openclaw](https://github.com/rohitg00/awesome-openclaw) — 커뮤니티 리소스 모음
- [Nix 모드](https://github.com/openclaw/nix-openclaw) — 선언적 설정

---

## 커뮤니티 및 기여

OpenClaw은 **Peter Steinberger**(@steipete)와 활발한 커뮤니티가 함께 만들어가는 프로젝트입니다.

### 참여 방법

| 기여 유형 | 방법 |
|-----------|------|
| 버그 수정, 작은 개선 | GitHub에 PR 제출 |
| 새 기능, 아키텍처 변경 | [GitHub Discussions](https://github.com/openclaw/openclaw/discussions) 또는 Discord에서 먼저 논의 |
| 질문 | Discord #setup-help 채널 |
| 스킬 기여 | [ClawHub](https://clawhub.com)에 등록 |
| 보안 취약점 | security@openclaw.ai |

### PR 제출 전 체크리스트

```bash
pnpm build && pnpm check && pnpm test
```

AI/바이브 코딩으로 만든 PR도 환영합니다! AI 도움을 받았다면 PR에 표시해 주세요.

### 핵심 메인테이너

- **Peter Steinberger** — 프로젝트 창시자 ([GitHub](https://github.com/steipete) · [X](https://x.com/steipete))
- **Shadow** — Discord + Slack ([GitHub](https://github.com/thewilloftheshadow))
- **Vignesh** — 메모리, TUI ([GitHub](https://github.com/vignesh07))
- **Jos** — Telegram, API, Nix ([GitHub](https://github.com/joshp123))
- **Christoph Nakazawa** — JS 인프라 ([GitHub](https://github.com/cpojer))
- **Gustavo Madeira Santana** — 멀티에이전트, CLI, 웹 UI ([GitHub](https://github.com/gumadeiras))
- **Maximilian Nussbaumer** — DevOps, CI ([GitHub](https://github.com/quotentiroler))

### 연락처

- [공식 웹사이트](https://openclaw.ai)
- [Discord](https://discord.gg/clawd)
- [X/Twitter @openclaw](https://x.com/openclaw)
- [X/Twitter @steipete](https://x.com/steipete)
- [steipete.me](https://steipete.me)

기여 가이드라인 상세: [CONTRIBUTING.md](CONTRIBUTING.md) · 보안 정책: [SECURITY.md](SECURITY.md)

### 감사의 말

Special thanks to [Mario Zechner](https://mariozechner.at/) for his support and for
[pi-mono](https://github.com/badlogic/pi-mono).
Special thanks to Adam Doppelt for lobster.bot.

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=openclaw/openclaw&type=date&legend=top-left)](https://www.star-history.com/#openclaw/openclaw&type=date&legend=top-left)

---

## Molty

OpenClaw was built for **Molty**, a space lobster AI assistant. 🦞
by Peter Steinberger and the community.

---

<p align="center">
  <strong>MIT License</strong> · Copyright (c) 2025 Peter Steinberger
</p>
<p align="center">
  <a href="https://openclaw.ai">openclaw.ai</a> · <a href="https://docs.openclaw.ai">docs.openclaw.ai</a> · <a href="https://clawhub.com">clawhub.com</a>
</p>
