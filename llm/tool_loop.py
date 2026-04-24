"""
llm/tool_loop.py

Generic Bedrock Converse tool use loop.
Handles message accumulation, tool dispatch, and termination.
Reusable for any tool use pattern — not specific to GOV.UK retrieval.
"""

from typing import Callable
from config.settings import MODEL_ID, MAX_TOKENS, TEMPERATURE


def run_tool_loop(
    system: str,
    initial_message: str,
    tools: dict[str, Callable],
    tool_specs: list[dict],
    bedrock_client,
    max_iterations: int = 8,
) -> str:
    """
    Runs the Bedrock Converse tool use loop until the model returns
    an end_turn response or max_iterations is reached.

    Args:
        system: System prompt text
        initial_message: The user's first message
        tools: Dict mapping tool name to callable (name -> function(input) -> dict)
        tool_specs: List of toolSpec dicts for the Bedrock toolConfig
        bedrock_client: Boto3 bedrock-runtime client
        max_iterations: Hard cap on tool call iterations

    Returns:
        The model's final text response, or empty string if no response
    """
    messages = [
        {"role": "user", "content": [{"text": initial_message}]}
    ]

    tool_config = {
        "tools": tool_specs,
        "toolChoice": {"auto": {}},
    }

    for _ in range(max_iterations):
        response = bedrock_client.converse(
            modelId=MODEL_ID,
            system=[{"text": system}],
            messages=messages,
            toolConfig=tool_config,
            inferenceConfig={
                "maxTokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
            },
        )

        output_message = response["output"]["message"]
        stop_reason = response["stopReason"]
        messages.append(output_message)

        if stop_reason == "end_turn":
            return _extract_text(output_message)

        if stop_reason == "tool_use":
            tool_results = _execute_tool_calls(
                output_message["content"], tools
            )
            messages.append({
                "role": "user",
                "content": [
                    {"toolResult": r} for r in tool_results
                ],
            })

    return ""  # max iterations reached


def _execute_tool_calls(
    content_blocks: list[dict],
    tools: dict[str, Callable],
) -> list[dict]:
    """Executes all tool calls in a content block and returns results."""
    results = []
    for block in content_blocks:
        if "toolUse" not in block:
            continue
        tool_use = block["toolUse"]
        result = _call_tool(tool_use["name"], tool_use["input"], tools)
        results.append({
            "toolUseId": tool_use["toolUseId"],
            "content": [{"json": result}],
        })
    return results


def _call_tool(
    name: str,
    input_data: dict,
    tools: dict[str, Callable],
) -> dict:
    """Dispatches a single tool call. Returns error dict on failure."""
    if name not in tools:
        return {"error": f"unknown tool: {name}"}
    try:
        return tools[name](input_data)
    except Exception as e:
        return {"error": str(e)}


def _extract_text(message: dict) -> str:
    """Extracts text content from a model response message."""
    for block in message.get("content", []):
        if "text" in block:
            return block["text"]
    return ""
