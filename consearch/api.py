"""Optional HTTP API. Run with: uvicorn consearch.api:app --reload"""

from dataclasses import asdict

from fastapi import FastAPI
from pydantic import BaseModel

from .session import ConversationSession, new_session

app = FastAPI(title="Conversational Search", version="0.1.0")
sessions: dict[str, ConversationSession] = {}  # in-memory; swap for Redis/DB in production


class AskRequest(BaseModel):
    session_id: str
    question: str


class SourceOut(BaseModel):
    id: int
    title: str
    url: str
    kind: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    steps: int
    trace: list[str]


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    if req.session_id not in sessions:
        sessions[req.session_id] = new_session()
    result = sessions[req.session_id].ask(req.question)
    return AskResponse(
        answer=result.text,
        sources=[SourceOut(**asdict(s)) for s in result.sources],
        steps=result.steps,
        trace=result.trace,
    )


@app.delete("/sessions/{session_id}")
def reset(session_id: str) -> dict:
    sessions.pop(session_id, None)
    return {"status": "reset"}
