import hashlib
import hmac
import time
from typing import Annotated
from fastapi import Header, HTTPException, Request
from config import settings

async def verify_slack_signature(
    request: Request,
    x_slack_request_timestamp: Annotated[str, Header()],
    x_slack_signature: Annotated[str, Header()],
) -> None:
    """Slack에서 보낸 요청인지 서명을 통해 검증합니다."""
    # 재전송 공격 방지 (5분 초과 시 거부)
    if abs(time.time() - float(x_slack_request_timestamp)) > 300:
        raise HTTPException(status_code=403, detail="Request timestamp expired")

    raw_body = await request.body()
    sig_basestring = f"v0:{x_slack_request_timestamp}:{raw_body.decode('utf-8')}"
    
    computed_signature = "v0=" + hmac.new(
        key=settings.slack_signing_secret.encode(),
        msg=sig_basestring.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed_signature, x_slack_signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")
