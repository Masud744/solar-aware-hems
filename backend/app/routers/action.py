# Action router — /action
from fastapi import APIRouter, HTTPException
from app.models.schemas import ActionRequest, ActionResponse
from app.database import get_supabase
from datetime import datetime, timezone

router = APIRouter(tags=["actions"])


@router.post("/action", response_model=ActionResponse)
async def log_action(req: ActionRequest):
    """Log a user action (accept/reject/manual) for a device request.

    This implements the human-in-the-loop confirmation step from §11.
    """
    if req.action not in ("accept", "reject", "manual"):
        raise HTTPException(
            status_code=422,
            detail="action must be 'accept', 'reject', or 'manual'",
        )

    sb = get_supabase()

    # Verify the device_request_id exists
    existing = (
        sb.table("device_requests")
        .select("id")
        .eq("id", req.device_request_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=404,
            detail=f"Device request {req.device_request_id} not found",
        )

    now = datetime.now(timezone.utc)

    result = sb.table("user_actions").insert({
        "device_request_id": req.device_request_id,
        "ts": now.isoformat(),
        "action": req.action,
    }).execute()

    row = result.data[0]
    return ActionResponse(
        id=row["id"],
        device_request_id=req.device_request_id,
        action=req.action,
        ts=now,
    )
