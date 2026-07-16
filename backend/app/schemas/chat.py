from __future__ import annotations

from pydantic import BaseModel, Field

from backend.app.schemas.mistake import CitationOut


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class ChatResponseOut(BaseModel):
    answer_markdown: str
    citations: list[CitationOut]
