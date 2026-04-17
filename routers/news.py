import asyncio
import httpx
from typing import Annotated
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from core.security import verify_slack_signature
from services.ai_service import ai_service
from utils.slack_builder import SlackBuilder

router = APIRouter(prefix="/news", tags=["news"])

async def process_ai_pipeline(response_url: str, keyword: str):
    """비동기적으로 AI 검색 및 분석을 수행하고 결과를 전송합니다."""
    try:
        # 1. 검색 및 분석 (동기 함수를 스레드에서 실행)
        news_results = await asyncio.to_thread(ai_service.search_news, keyword)
        analysis_data = await asyncio.to_thread(ai_service.analyze_content, news_results)
        
        # 2. UI 구성
        payload = SlackBuilder.build_news_blocks(analysis_data, keyword)
    except Exception as e:
        payload = {"text": f"⚠️ 처리 중 오류가 발생했습니다: {str(e)}"}

    # 3. Slack response_url로 전송
    async with httpx.AsyncClient() as client:
        await client.post(response_url, json=payload)

@router.post("/slack")
async def slack_command(
    request: Request,
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(verify_slack_signature)]
):
    form = await request.form()
    response_url = str(form.get("response_url"))
    keyword = str(form.get("text", ""))

    # 3초 룰 방어를 위해 즉시 응답하고 작업을 백그라운드로 넘김
    background_tasks.add_task(process_ai_pipeline, response_url, keyword)

    return {
        "response_type": "ephemeral",
        "text": "🔎 최신 뉴스를 수집하여 분석 중입니다. 잠시만 기다려 주세요!"
    }
