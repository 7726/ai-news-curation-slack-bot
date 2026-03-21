import hashlib
import hmac
import time
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Form, Header, HTTPException, Request

from config import settings

router = APIRouter(prefix="/news", tags=["news"])


# ---------------------------------------------------------------------------
# Slack 서명 검증 의존성
# ---------------------------------------------------------------------------

async def verify_slack_signature(
    request: Request,
    x_slack_timestamp: Annotated[str, Header()],
    x_slack_signature: Annotated[str, Header()],
) -> None:
    """
    Slack Signing Secret으로 요청 위변조를 검증한다.
    5분 이상 지난 타임스탬프는 재전송 공격 방지를 위해 거부한다.
    """
    # 5분(300초) 이상 지난 요청 거부 (Replay Attack 방어)
    if abs(time.time() - float(x_slack_timestamp)) > 300:
        raise HTTPException(status_code=403, detail="Request timestamp expired")

    raw_body = await request.body()
    sig_basestring = f"v0:{x_slack_timestamp}:{raw_body.decode('utf-8')}"
    computed = "v0=" + hmac.new(
        key=settings.slack_signing_secret.encode(),
        msg=sig_basestring.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed, x_slack_signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")


# ---------------------------------------------------------------------------
# Background Task: 슬랙 response_url로 지연 응답 전송
# ---------------------------------------------------------------------------

async def send_delayed_response(response_url: str, user_name: str, text: str) -> None:
    """
    슬랙 3초 룰 방어용 BackgroundTask.
    실제 AI 파이프라인(Phase 3)으로 교체 예정.
    """
    # [Phase 2] Mock 응답 — Phase 3에서 Tavily + Gemini 결과로 교체
    payload = {
        "response_type": "in_channel",
        "text": (
            f"*[AI 뉴스 큐레이션 - Phase 2 Mock]* 🤖\n"
            f"<@{user_name}>님, 파이프라인이 곧 완성됩니다!\n"
            f"입력 키워드: `{text or '없음'}`"
        ),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(response_url, json=payload)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def get_news():
    """[Phase 1] 더미 엔드포인트 - 추후 AI 파이프라인으로 교체 예정"""
    return {
        "status": "ok",
        "message": "AI 뉴스 큐레이션 파이프라인이 곧 여기에 연결됩니다.",
        "phase": 1,
    }


@router.post("/slack")
async def slack_slash_command(
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(verify_slack_signature)],
    command: Annotated[str, Form()],
    response_url: Annotated[str, Form()],
    user_name: Annotated[str, Form()] = "",
    text: Annotated[str, Form()] = "",
):
    """
    [Phase 2] 슬랙 /ai-news Slash Command 수신 엔드포인트.

    - Slack Signing Secret으로 요청 위변조 검증
    - 즉시 HTTP 200 + ephemeral 메시지 반환 (슬랙 3초 룰 방어)
    - 실제 처리는 BackgroundTasks로 비동기 위임
    """
    background_tasks.add_task(send_delayed_response, response_url, user_name, text)

    return {
        "response_type": "ephemeral",
        "text": "⏳ AI 뉴스를 불러오는 중입니다. 잠시만 기다려 주세요...",
    }
