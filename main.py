from fastapi import FastAPI
from mangum import Mangum

from config import settings

app = FastAPI(
    title="AI 뉴스 큐레이션 API",
    version="0.1.0",
    description="Slack Slash Command로 최신 AI 뉴스를 큐레이션하는 서버리스 파이프라인",
)


@app.get("/health")
async def health_check():
    """Lambda / API Gateway 헬스체크용 엔드포인트"""
    return {"status": "ok", "version": app.version}


@app.get("/news")
async def get_news():
    """
    [Phase 1] 더미 엔드포인트 - 추후 AI 파이프라인으로 교체 예정
    """
    return {
        "status": "ok",
        "message": "AI 뉴스 큐레이션 파이프라인이 곧 여기에 연결됩니다.",
        "phase": 1,
    }


# AWS Lambda 핸들러 (Mangum 어댑터)
handler = Mangum(app, lifespan="off")
