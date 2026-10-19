from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .. import chat
from ..auth import current_user

router = APIRouter(prefix="/api", tags=["chat"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class PageContext(BaseModel):
    path: str = Field("/", max_length=200)
    title: str = Field("", max_length=200)
    symbol: str | None = Field(None, max_length=20)
    text: str = Field("", max_length=60_000)


class ChatIn(BaseModel):
    provider: Literal["local", "gemini"] = "local"
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    page: PageContext = PageContext()


@router.get("/chat/providers")
def chat_providers(user: dict = Depends(current_user)):
    return chat.providers()


@router.post("/chat")
def chat_reply(body: ChatIn, user: dict = Depends(current_user)):
    """Streams NDJSON events: tool, text, then done or error."""
    return StreamingResponse(
        chat.reply(user["username"], body.provider, [m.model_dump() for m in body.messages], body.page.model_dump()),
        media_type="application/x-ndjson",
        # Stops proxies from holding the stream back until it ends.
        headers={"X-Accel-Buffering": "no"},
    )
