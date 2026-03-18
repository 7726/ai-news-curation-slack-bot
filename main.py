from fastapi import FastAPI
from mangum import Mangum

from config import settings
from routers import news

app = FastAPI(
    title="AI 뉴스 큐레이션 API",
    version="0.1.0",
    description="Slack Slash Command로 최신 AI 뉴스를 큐레이션하는 서버리스 파이프라인",
)

app.include_router(news.router)


@app.get("/health")
async def health_check():
    """Lambda / API Gateway 헬스체크용 엔드포인트"""
    return {"status": "ok", "version": app.version}


# AWS Lambda 핸들러 (Mangum 어댑터)
handler = Mangum(app, lifespan="off")
