from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.exceptions import AIEngineError
from backend.models.chat import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat(request: Request, body: ChatRequest):
    services = request.app.state.services
    ai_engine = getattr(services, "ai_engine", None)
    if ai_engine is None:
        raise HTTPException(status_code=503, detail="AI engine not available. Set ANTHROPIC_API_KEY.")

    conversation_id = body.conversation_id or str(uuid.uuid4())

    async def event_stream():
        try:
            async for chunk in ai_engine.stream_response(body.message, conversation_id):
                data = json.dumps({"content": chunk, "conversation_id": conversation_id})
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"
        except AIEngineError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
