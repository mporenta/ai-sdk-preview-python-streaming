import json
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict

from .attachment import ClientAttachment


class ToolInvocationState(str, Enum):
    CALL = 'call'
    PARTIAL_CALL = 'partial-call'
    RESULT = 'result'

class ToolInvocation(BaseModel):
    state: ToolInvocationState
    toolCallId: str
    toolName: str
    args: Any
    result: Any


class ClientMessagePart(BaseModel):
    type: str
    text: Optional[str] = None
    contentType: Optional[str] = None
    url: Optional[str] = None
    data: Optional[Any] = None
    toolCallId: Optional[str] = None
    toolName: Optional[str] = None
    state: Optional[str] = None
    input: Optional[Any] = None
    output: Optional[Any] = None
    args: Optional[Any] = None

    model_config = ConfigDict(extra="allow")


class ClientMessage(BaseModel):
    role: str
    content: Optional[str] = None
    parts: Optional[List[ClientMessagePart]] = None
    experimental_attachments: Optional[List[ClientAttachment]] = None
    toolInvocations: Optional[List[ToolInvocation]] = None


def convert_to_prompt(messages: List[ClientMessage]) -> str:
    """Flatten UI messages into a textual prompt for Claude Agent SDK."""

    prompt_lines: List[str] = []

    for message in messages:
        message_lines: List[str] = []

        if message.parts:
            for part in message.parts:
                if part.type == "text" and part.text is not None:
                    message_lines.append(part.text)
                elif part.type == "file" and part.url:
                    message_lines.append(f"File shared ({part.contentType or 'unknown'}): {part.url}")
                elif part.type.startswith("tool-"):
                    if part.state == "output-available" and part.output is not None:
                        message_lines.append(
                            f"Tool {part.toolName or part.type.replace('tool-', '', 1)} output: {json.dumps(part.output)}"
                        )
                    elif part.state and part.toolCallId:
                        message_lines.append(
                            f"Tool request {part.toolCallId} for {part.toolName or part.type.replace('tool-', '', 1)}"
                        )

        elif message.content is not None:
            message_lines.append(message.content)

        if not message.parts and message.experimental_attachments:
            for attachment in message.experimental_attachments:
                message_lines.append(
                    f"Attachment ({attachment.contentType}): {attachment.url}"
                )

        if message.toolInvocations:
            for tool_invocation in message.toolInvocations:
                invocation_summary = f"Tool {tool_invocation.toolName} called with {json.dumps(tool_invocation.args)}"
                message_lines.append(invocation_summary)
                if tool_invocation.result is not None:
                    message_lines.append(
                        f"Tool result ({tool_invocation.toolName}): {json.dumps(tool_invocation.result)}"
                    )

        if message_lines:
            prompt_lines.append(f"{message.role}:\n" + "\n".join(message_lines))

    if not prompt_lines:
        return "User provided no content."

    return "\n\n".join(prompt_lines)
