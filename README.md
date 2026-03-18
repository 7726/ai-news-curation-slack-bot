# 📡 AI 뉴스 큐레이션 파이프라인

> Slack Slash Command 한 번으로 최신 AI 트렌드 뉴스를 수집·분석·요약까지 자동화하는 서버리스 백엔드 파이프라인

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-FF9900?logo=awslambda&logoColor=white)](https://aws.amazon.com/lambda/)
[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-7C3AED?logo=anthropic&logoColor=white)](https://claude.ai/code)

---

## 프로젝트 개요

슬랙에서 `/뉴스` 커맨드를 입력하면 다음이 자동으로 실행됩니다.

1. **Tavily API**로 최신 AI 뉴스 수집
2. **Gemini API**로 6가지 관점 분석 (요약 / 신빙성 / 난이도 / 비용 / 실현 가능성 등)
3. **Slack Block Kit** 포맷으로 결과를 채널에 전송

전통적인 웹 크롤링 없이 AI 기반 검색 API만 사용하며, 슬랙의 3초 응답 제한을 Two-Lambda 비동기 패턴으로 해결합니다.

---

## 주요 기술 스택

| 구분 | 기술 |
|------|------|
| Language / Framework | Python 3.12, FastAPI, Uvicorn |
| Cloud | AWS Lambda, API Gateway, DynamoDB, EventBridge |
| AI - 검색 | Tavily API |
| AI - 분석 | Gemini API (google-genai SDK) |
| 슬랙 연동 | Slack Slash Command, Block Kit |
| 인프라 어댑터 | Mangum (FastAPI → Lambda) |
| 설정 관리 | pydantic-settings, python-dotenv |
| 개발 도구 | Claude Code (AI-assisted development) |

---

## 시스템 아키텍처

```
Slack Slash Command
        │
        ▼
[API Gateway] ──▶ [Lambda A: Receiver]
                        │  즉시 HTTP 200 반환 (< 1초)
                        │
                        ▼ 비동기 호출
                  [Lambda B: Processor]
                        │
                  ┌─────┴──────┐
                  ▼            ▼
            [Tavily API]  [DynamoDB]
            (뉴스 수집)   (중복 체크)
                  │
                  ▼
            [Gemini API]
            (6항목 분석)
                  │
                  ▼
          [Slack response_url]
          (Block Kit 메시지 전송)
```

### Slack 3초 룰 대응 — Two-Lambda 비동기 패턴

슬랙은 Slash Command에 대해 **3초 내 응답**이 없으면 타임아웃 처리합니다.
AI 파이프라인(검색 → 분석 → 전송)은 수 초~수십 초가 소요되므로, 아래 패턴으로 해결합니다.

- **Lambda A (Receiver)**: 요청 수신 즉시 `"처리 중입니다..."` 메시지와 HTTP 200 반환
- **Lambda B (Processor)**: 실제 AI 파이프라인 실행 후 `response_url`로 결과 전송

---

## AI 분석 항목 (Gemini 프롬프트 출력 스펙)

Gemini API는 아래 6가지 항목을 **JSON 형식**으로 반환하도록 프롬프트 설계되어 있습니다.

| 필드 | 설명 | 분류 기준 |
|------|------|-----------|
| `summary_line` | AI 한 줄 평 | — |
| `summary_detail` | 내용 요약 | — |
| `reliability` | 신빙성 | 상 / 중 / 하 |
| `difficulty` | 난이도·진입장벽 | 최상 / 상 / 중 / 하 / 최하 |
| `cost_level` | 비용 수준 | 상 / 중 / 하 |
| `ai_review` | AI 최종 후기 및 실현 가능성 | — |

---

## 개발 단계 (Phased Roadmap)

- [x] **Phase 1** — 프로젝트 뼈대 및 로컬 환경 세팅
  - FastAPI 보일러플레이트, Mangum 어댑터, 더미 `/news` 엔드포인트
  - `.env` 템플릿, `.gitignore`, `requirements.txt`
- [ ] **Phase 2** — Slack 비동기 연동
  - `/뉴스` Slash Command 수신 및 즉시 200 반환
  - `BackgroundTasks`로 지연 응답 처리
- [ ] **Phase 3** — AI 파이프라인 결합
  - Tavily 뉴스 수집 → Gemini 분석 → Slack Block Kit 전송
- [ ] **Phase 4** — AWS 인프라 및 DynamoDB 연동
  - 기사 URL 해시 기반 중복 방지, Lambda 배포 최종 세팅

---

## 로컬 실행 방법

```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
# Windows PowerShell
./venv/Scripts/Activate.ps1

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 입력

# 4. 서버 실행
uvicorn main:app --reload
```

서버 실행 후 `http://127.0.0.1:8000/docs` 에서 Swagger UI 확인 가능합니다.

---

## 환경 변수

`.env.example`을 참고하여 `.env` 파일을 생성하세요.
`.env` 파일은 `.gitignore`에 포함되어 있으며 **절대 커밋되지 않습니다.**

```
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
TAVILY_API_KEY=
GEMINI_API_KEY=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=ap-northeast-2
DYNAMODB_TABLE_NAME=ai-news-curation
```

---

## 개발 방식

이 프로젝트는 **[Claude Code](https://claude.ai/code)**(Anthropic의 AI 코딩 CLI 도구)를 활용하여 개발되고 있습니다.
아키텍처 설계, 코드 생성, 리뷰, 리팩토링 전 과정에 AI를 적극적으로 도입하여
"AI 도구를 실제 개발 워크플로우에 녹여내는 것" 자체를 하나의 학습 목표로 삼고 있습니다.

---

## 디렉토리 구조

```
ai_news_curation/
├── main.py              # FastAPI 앱 진입점 + Mangum Lambda 핸들러
├── config.py            # pydantic-settings 환경변수 관리
├── requirements.txt     # 의존성 목록
├── .env.example         # 환경변수 템플릿
├── .gitignore
└── venv/                # 로컬 가상환경 (git 제외)
```
