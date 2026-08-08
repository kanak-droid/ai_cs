from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatTraceStep(BaseModel):
    tool: str
    ok: bool
    summary: str


class ChatResponse(BaseModel):
    reply: str
    trace: list[ChatTraceStep] = []
