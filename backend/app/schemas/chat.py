from typing import Literal

from pydantic import BaseModel


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


class ChatTraceStep(BaseModel):
    tool: str
    ok: bool
    summary: str


class ChatResponse(BaseModel):
    reply: str
    trace: list[ChatTraceStep] = []
