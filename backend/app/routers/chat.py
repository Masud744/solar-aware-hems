# Chat Router — /chat (AI-Powered HEMS Conversational Assistant with User Isolation)
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatMessageRecord,
)
from app.services import assistant
from app.services.auth_service import get_token_from_header, get_current_user, AuthUser

logger = logging.getLogger(__name__)
router = APIRouter(tags=["assistant"])


async def get_optional_auth_user(authorization: Optional[str] = Header(None)) -> Optional[AuthUser]:
    """Optionally resolve authenticated user from Bearer token."""
    if not authorization:
        return None
    try:
        token = get_token_from_header(authorization)
        return await get_current_user(token)
    except Exception as e:
        logger.debug(f"Optional auth token error: {e}")
        return None


@router.post("/chat", response_model=ChatResponse)
async def post_chat_message(
    req: ChatRequest,
    auth_user: Optional[AuthUser] = Depends(get_optional_auth_user),
):
    """Process natural-language conversation query through Groq LLM with per-user data isolation."""
    try:
        user_id = auth_user.id if auth_user else None
        history_dicts = (
            [{"role": h.role, "content": h.content} for h in req.history]
            if req.history
            else []
        )
        res = await assistant.process_chat_message(
            user_message=req.message,
            session_id=req.session_id,
            user_id=user_id,
            conversation_history=history_dicts,
        )
        return ChatResponse(**res)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat assistant processing error: {str(e)}",
        )


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str = Query(..., description="Unique conversation session ID"),
    limit: int = Query(50, ge=1, le=100),
    auth_user: Optional[AuthUser] = Depends(get_optional_auth_user),
):
    """Fetch persistent chronological chat messages for a session and user from Supabase."""
    try:
        user_id = auth_user.id if auth_user else None
        records = assistant.load_chat_history(session_id, user_id=user_id, limit=limit)
        msg_models = [
            ChatMessageRecord(
                id=r.get("id"),
                session_id=r.get("session_id", session_id),
                role=r.get("role", "assistant"),
                content=r.get("content", ""),
                data_sources=r.get("data_sources") or [],
                tool_calls=r.get("tool_calls") or [],
                created_at=r.get("created_at"),
            )
            for r in records
        ]
        return ChatHistoryResponse(
            session_id=session_id,
            messages=msg_models,
            count=len(msg_models),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load chat history: {str(e)}",
        )


@router.delete("/chat/history")
async def delete_chat_history_endpoint(
    session_id: str = Query(..., description="Unique conversation session ID to clear"),
    auth_user: Optional[AuthUser] = Depends(get_optional_auth_user),
):
    """Clear chat messages for a session and user from Supabase."""
    try:
        user_id = auth_user.id if auth_user else None
        success = assistant.delete_chat_history(session_id, user_id=user_id)
        return {"status": "cleared" if success else "empty", "session_id": session_id}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear chat history: {str(e)}",
        )
