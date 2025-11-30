from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request as FastAPIRequest
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .utils.prompt import ClientMessage, convert_to_prompt
from .utils.stream import patch_response_with_headers, stream_text
from .utils.tools import AVAILABLE_TOOLS
from vercel.headers import set_headers


load_dotenv(".env.local")

app = FastAPI()


@app.middleware("http")
async def _vercel_set_headers(request: FastAPIRequest, call_next):
    set_headers(dict(request.headers))
    return await call_next(request)


class Request(BaseModel):
    messages: List[ClientMessage]


@app.post("/api/chat")
async def handle_chat_data(request: Request, protocol: str = Query('data')):
    messages = request.messages
    prompt = convert_to_prompt(messages)

    response = StreamingResponse(
        stream_text(prompt, AVAILABLE_TOOLS, protocol),
        media_type="text/event-stream",
    )
    return patch_response_with_headers(response, protocol)
