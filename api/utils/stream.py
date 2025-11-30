import json
import traceback
import uuid
from typing import Any, Callable, Dict, Mapping

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)
from fastapi.responses import StreamingResponse


async def stream_text(
    prompt: str,
    available_tools: Mapping[str, Callable[..., Any]],
    protocol: str = "data",
):
    """Yield Server-Sent Events for a streaming chat completion."""
    try:
        def format_sse(payload: dict) -> str:
            return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"

        message_id = f"msg-{uuid.uuid4().hex}"
        text_stream_id = "text-1"
        text_started = False
        finish_reason = "stop"
        usage_data = None

        yield format_sse({"type": "start", "messageId": message_id})

        async for message in query(prompt=prompt):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        if not text_started:
                            yield format_sse({"type": "text-start", "id": text_stream_id})
                            text_started = True
                        yield format_sse(
                            {"type": "text-delta", "id": text_stream_id, "delta": block.text}
                        )

                    elif isinstance(block, ToolUseBlock):
                        tool_name = block.name
                        tool_call_id = block.id
                        tool_input = block.input or {}

                        yield format_sse(
                            {
                                "type": "tool-input-start",
                                "toolCallId": tool_call_id,
                                "toolName": tool_name,
                            }
                        )

                        yield format_sse(
                            {
                                "type": "tool-input-available",
                                "toolCallId": tool_call_id,
                                "toolName": tool_name,
                                "input": tool_input,
                            }
                        )

                        tool_function = available_tools.get(tool_name)
                        if tool_function is None:
                            yield format_sse(
                                {
                                    "type": "tool-output-error",
                                    "toolCallId": tool_call_id,
                                    "errorText": f"Tool '{tool_name}' not found.",
                                }
                            )
                            continue

                        try:
                            tool_result = tool_function(**tool_input)
                        except Exception as error:
                            yield format_sse(
                                {
                                    "type": "tool-output-error",
                                    "toolCallId": tool_call_id,
                                    "errorText": str(error),
                                }
                            )
                        else:
                            yield format_sse(
                                {
                                    "type": "tool-output-available",
                                    "toolCallId": tool_call_id,
                                    "output": tool_result,
                                }
                            )

            elif isinstance(message, ResultMessage):
                usage_data = message.usage
                finish_reason = "error" if message.is_error else "stop"
                break

        if text_started:
            yield format_sse({"type": "text-end", "id": text_stream_id})

        finish_metadata: Dict[str, Any] = {}
        if finish_reason is not None:
            finish_metadata["finishReason"] = finish_reason

        if usage_data is not None:
            finish_metadata["usage"] = usage_data

        if finish_metadata:
            yield format_sse({"type": "finish", "messageMetadata": finish_metadata})
        else:
            yield format_sse({"type": "finish"})

        yield "data: [DONE]\n\n"
    except Exception:
        traceback.print_exc()
        raise


def patch_response_with_headers(
    response: StreamingResponse,
    protocol: str = "data",
) -> StreamingResponse:
    """Apply the standard streaming headers expected by the Vercel AI SDK."""

    response.headers["x-vercel-ai-ui-message-stream"] = "v1"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"

    if protocol:
        response.headers.setdefault("x-vercel-ai-protocol", protocol)

    return response
