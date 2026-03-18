from fastapi import APIRouter

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
async def get_news():
    """
    [Phase 1] 더미 엔드포인트 - 추후 AI 파이프라인으로 교체 예정
    """
    return {
        "status": "ok",
        "message": "AI 뉴스 큐레이션 파이프라인이 곧 여기에 연결됩니다.",
        "phase": 1,
    }
