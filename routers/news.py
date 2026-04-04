import asyncio
import hashlib
import hmac
import time
import json
import time
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from tavily import TavilyClient
from google import genai
from google.genai import types

from config import settings

router = APIRouter(prefix="/news", tags=["news"])

# API 클라이언트 초기화
tavily_client = TavilyClient(api_key=settings.tavily_api_key)
gemini_client = genai.Client(api_key=settings.gemini_api_key)

# ---------------------------------------------------------------------------
# Slack 서명 검증 의존성
# ---------------------------------------------------------------------------
async def verify_slack_signature(
    request: Request,
    x_slack_request_timestamp: Annotated[str, Header()],
    x_slack_signature: Annotated[str, Header()],
) -> None:
    """
    Slack Signing Secret으로 요청 위변조를 검증한다.
    5분 이상 지난 타임스탬프는 재전송 공격 방지를 위해 거부한다.
    """
    # 5분(300초) 이상 지난 요청 거부 (Replay Attack 방어)
    if abs(time.time() - float(x_slack_request_timestamp)) > 300:
        raise HTTPException(status_code=403, detail="Request timestamp expired")

    raw_body = await request.body()
    sig_basestring = f"v0:{x_slack_request_timestamp}:{raw_body.decode('utf-8')}"
    computed = "v0=" + hmac.new(
        key=settings.slack_signing_secret.encode(),
        msg=sig_basestring.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed, x_slack_signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")

# ---------------------------------------------------------------------------
# 외부 API 동기 호출 래퍼 (비동기 Event Loop 블로킹 방지)
# ---------------------------------------------------------------------------
def fetch_news_from_tavily(query: str) -> dict:
    """Tavily API를 사용하여 뉴스 검색 (동기 함수)"""
    search_query = query if query else "최신 AI 기술 트렌드"
    return tavily_client.search(
        query=search_query,
        search_depth="advanced",
        max_results=3
    )

def analyze_news_with_gemini(news_data: dict) -> dict:
    """Gemini API를 사용하여 뉴스 분석 및 JSON 추출 (동기 함수)"""
    context_str = "\n".join(
        [f"- 제목: {result['title']}\n  내용: {result['content']}" for result in news_data.get('results', [])]
    )

    prompt = f"""
너는 시니어 AI 뉴스 큐레이터야. 다음 최신 AI 뉴스 데이터를 분석하여 반드시 정해진 JSON 포맷으로만 응답해.

[뉴스 데이터]
{context_str}

[분석 기준 및 요구사항]
1. summary_line: AI 한 줄 평
2. summary_detail: 내용 요약
3. reliability: 신빙성 분류 (상/중/하) 중 택 1
4. difficulty: 난이도/진입장벽 (최상/상/중/하/최하) 중 택 1
5. cost_level: 비용 분류 (상/중/하) 중 택 1
6. ai_review: AI 최종 후기 및 실현 가능성 체크

[출력 포맷 (반드시 아래 JSON 형태를 유지할 것)]
{{
  "summary_line": "한 줄 평",
  "summary_detail": "요약 내용",
  "reliability": "상",
  "difficulty": "중",
  "cost_level": "하",
  "ai_review": "최종 리뷰 내용"
}}
"""
    # JSON 출력을 강제하는 config 설정
    response = gemini_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2, # 분석의 일관성을 위해 낮은 온도 설정
        ),
    )

    # response.text가 None인지 검증하는 로직
    if not response.text:
        # Pylance 타입 에러 해결 및 실제 None 반환 시의 안정성 확보
        raise ValueError("Gemini API로부터 유효한 텍스트 응답을 받지 못했습니다. (Safety 필터 제한 또는 API 오류)")
    
    return json.loads(response.text)

# ---------------------------------------------------------------------------
# [Phase 3] Slack Block Kit 렌더러
# ---------------------------------------------------------------------------
def build_slack_block_kit(parsed_data: dict, keyword: str) -> dict:
    """분석된 JSON 데이터를 Slack Block Kit 형태로 변환"""
    search_keyword = keyword if keyword else "최신 AI 기술 트렌드"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📰 큐레이션 완료: {parsed_data.get('summary_line', 'AI 뉴스 업데이트')}",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*검색 키워드*: `{search_keyword}`"
                }
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{parsed_data.get('summary_detail', '내용 요약이 없습니다.')}*"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*🔍 신빙성*\n{parsed_data.get('reliability', '알 수 없음')}"},
                {"type": "mrkdwn", "text": f"*🎓 난이도*\n{parsed_data.get('difficulty', '알 수 없음')}"},
                {"type": "mrkdwn", "text": f"*💸 예상 비용*\n{parsed_data.get('cost_level', '알 수 없음')}"}
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"💡 *AI 큐레이터의 한마디*\n{parsed_data.get('ai_review', '')}"
            }
        }
    ]
    return {"response_type": "in_channel", "blocks": blocks}

# ---------------------------------------------------------------------------
# Background Task: 슬랙 response_url로 지연 응답 전송
# ---------------------------------------------------------------------------
async def send_delayed_response(response_url: str, user_name: str, text: str) -> None:
    """
    슬랙 3초 룰 방어용 BackgroundTask.
    실제 AI 파이프라인(Phase 3)으로 교체 예정.
    """
    try:
        # 1. Tavily 검색 (동기 함수이므로 to_thread를 사용하여 비동기 논블로킹 처리)
        news_data = await asyncio.to_thread(fetch_news_from_tavily, text)

        # 2. Gemini 분석
        parsed_data = await asyncio.to_thread(analyze_news_with_gemini, news_data)

        # 3. Block Kit 메시지 생성
        payload = build_slack_block_kit(parsed_data, text)
    
    except Exception as e:
        # 에러 발생 시 사용자에게 알림
        payload = {
            "response_type": "ephemeral",
            "text": f"❌ 뉴스 큐레이션 중 오류가 발생했습니다: {str(e)}"
        }
    
    # 4. Slack으로 결과 전송
    async with httpx.AsyncClient(timeout=15.0) as client:
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
        "phase": 3,
    }

@router.post("/slack")
async def slack_slash_command(
    request: Request,
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(verify_slack_signature)],
):
    """
    [Phase 2] 슬랙 /ai-news Slash Command 수신 엔드포인트.

    - Slack Signing Secret으로 요청 위변조 검증
    - 즉시 HTTP 200 + ephemeral 메시지 반환 (슬랙 3초 룰 방어)
    - 실제 처리는 BackgroundTasks로 비동기 위임
    """
    form = await request.form()
    response_url = form.get("response_url", "")
    user_name = str(form.get("user_name", ""))
    text = str(form.get("text", ""))

    if not response_url:
        raise HTTPException(status_code=400, detail="response_url is required")

    background_tasks.add_task(send_delayed_response, str(response_url), user_name, text)

    return {
        "response_type": "ephemeral",
        "text": "⏳ AI 뉴스를 불러오는 중입니다. 잠시만 기다려 주세요...",
    }
