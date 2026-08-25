from typing import Literal

from pydantic import BaseModel, Field


class ChatHistoryTurn(BaseModel):
    role: Literal["astrologer", "assistant"]
    text: str


class ChatRequest(BaseModel):
    message: str
    # Prior turns of this conversation, sent by the client — the backend is
    # stateless across requests, so without this the model would have no
    # memory of anything said earlier (and, e.g., couldn't write a ticket
    # summary that reflects the actual issue rather than just the astrologer's
    # latest message).
    history: list[ChatHistoryTurn] = []
    # Client-generated (one per webview visit) — analytics-only, identifies
    # which ChatSession this turn belongs to. Optional so older clients still
    # work; a turn without one simply isn't logged for analytics.
    session_id: str | None = None


class ChatTraceStep(BaseModel):
    tool: str
    ok: bool
    summary: str


class ChatResponse(BaseModel):
    reply: str
    trace: list[ChatTraceStep] = []
    # Set when this turn's create_support_ticket call raised a new ticket —
    # lets the frontend surface it immediately instead of waiting on the next
    # /api/tickets poll.
    created_ticket_id: int | None = None
    # Set when the bot just confirmed the astrologer's issue is resolved
    # (mark_issue_resolved) — tells the frontend to show the feedback widget.
    show_feedback: bool = False


class SessionFeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    reasons: list[str] = Field(default_factory=list)
    comment: str | None = None
