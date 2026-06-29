from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import (
    ChatMessageResponse,
    ChatSessionResponse,
    SendChatRequest,
    SendChatResponse,
)
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()


def _to_message(msg) -> ChatMessageResponse:
    citations = msg.citations
    return ChatMessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role.value,
        content=msg.content,
        citations=citations,
        tokens_used=msg.tokens_used,
        created_at=msg.created_at,
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Pull AI chat sessions stored on Railway PostgreSQL."""
    rows = chat_service.list_sessions(db, user.id)
    return [
        ChatSessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=count,
        )
        for session, count in rows
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
def get_session_messages(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Pull full message history for a chat session."""
    messages = chat_service.get_messages(db, user.id, session_id)
    if not messages:
        session_exists = any(s.id == session_id for s, _ in chat_service.list_sessions(db, user.id))
        if not session_exists:
            raise HTTPException(status_code=404, detail="Chat session not found")
    return [_to_message(m) for m in messages]


@router.post("/send", response_model=SendChatResponse)
async def send_chat_message(
    body: SendChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.services.subscription_limits import require_chat_quota

    require_chat_quota(db, user)
    try:
        session, user_msg, assistant_msg, balance = await chat_service.send_message(
            db, user, body.message, body.session_id
        )
    except ValueError as exc:
        status = 402 if "Insufficient" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc

    return SendChatResponse(
        session_id=session.id,
        user_message=_to_message(user_msg),
        assistant_message=_to_message(assistant_msg),
        token_balance=balance,
    )


@router.get("/cost")
def chat_cost():
    return {"cost_per_message": settings.tokens_per_chat_message}
