import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: Optional[str] = None

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", v
        ):
            raise ValueError("conversation_id must be a valid UUID")
        return v


class ChatResponse(BaseModel):
    message: str
    conversation_id: str
