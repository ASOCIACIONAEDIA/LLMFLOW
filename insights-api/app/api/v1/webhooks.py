from typing import Any, Optional
from fastapi import APIRouter, HTTPException, status, Path, Header
from app.workers.base.webhook_wait import resolve_job_id_from_correlation, push_webhook_result
from app.core.config import settings

router = APIRouter()

def _require_webhook_auth(authorization: Optional[str]):
    expected = f"Bearer {settings.WEBHOOK_SHARED_SECRET}" if settings.WEBHOOK_SHARED_SECRET else None
    if not expected or authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized webhook")

@router.post("/{topic}", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook_topic(
    topic: str = Path(..., min_length=1),
    payload: Any = None,
    authorization: Optional[str] = Header(None),
):
    _require_webhook_auth(authorization)
    if payload is None:
        raise HTTPException(status_code=400, detail="Missing payload")

    # If provider sends a list, wrap it
    body = {"results": payload} if isinstance(payload, list) else payload

    job_id: Optional[str] = body.get("job_id")
    if not job_id:
        corr = body.get("correlation_id") or body.get("snapshot_id")
        job_id = await resolve_job_id_from_correlation(topic, corr) if corr else None
    if not job_id:
        raise HTTPException(status_code=400, detail="Missing job_id/correlation_id")

    await push_webhook_result(topic, job_id, body)
    return {"status": "accepted"}

@router.post("/{topic}/{correlation_id}", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook_with_correlation(
    topic: str = Path(..., min_length=1),
    correlation_id: str = Path(..., min_length=1),
    payload: Any = None,
    authorization: Optional[str] = Header(None),
):
    _require_webhook_auth(authorization)
    if payload is None:
        raise HTTPException(status_code=400, detail="Missing payload")
    body = {"results": payload} if isinstance(payload, list) else payload

    job_id = body.get("job_id") or await resolve_job_id_from_correlation(topic, correlation_id)
    if not job_id:
        raise HTTPException(status_code=400, detail="Missing job_id/correlation_id")

    await push_webhook_result(topic, job_id, body)
    return {"status": "accepted"}