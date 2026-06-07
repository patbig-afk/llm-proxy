import os
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY", "")

ROUTING = {
    "SIMPLE": "gemini-2.5-flash",
    "MEDIUM": "claude-3-5-haiku-20241022",
    "COMPLEX": "claude-3-5-sonnet-20241022",
}


async def route_to_model(complexity: str, body: dict) -> dict:
    model = ROUTING.get(complexity, "claude-haiku-4-5-20251001")

    if model.startswith("gemini"):
        result = await call_gemini(model, body)
    else:
        result = await call_anthropic(model, body)

    result["_routed_model"] = model
    return result


async def call_anthropic(model: str, body: dict) -> dict:
    messages = body.get("messages", [])
    system_msgs = [m["content"] for m in messages if m.get("role") == "system"]
    user_msgs = [m for m in messages if m.get("role") != "system"]

    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": body.get("max_tokens", 1024),
        "messages": user_msgs,
    }
    if system_msgs:
        payload["system"] = " ".join(system_msgs)

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        )
        data = resp.json()

    if "error" in data:
        logger.error(f"Anthropic error: {data['error']}")
        raise ValueError(f"Anthropic API error: {data['error'].get('message', data['error'])}")

    content = data.get("content", [])
    text = content[0].get("text", "") if content else ""

    # Convert Anthropic response to OpenAI format
    return {
        "id": data.get("id", ""),
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": text,
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
            "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
        },
    }


async def call_gemini(model: str, body: dict) -> dict:
    messages = body.get("messages", [])
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m.get("content", "")}]}
        for m in messages if m.get("role") != "system"
    ]

    system_parts = [m.get("content", "") for m in messages if m.get("role") == "system"]
    payload: dict[str, Any] = {"contents": contents}
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": " ".join(system_parts)}]}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_KEY}"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload)
        data = resp.json()

    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    usage = data.get("usageMetadata", {})

    # Convert Gemini response to OpenAI format
    return {
        "id": "gemini-resp",
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "completion_tokens": usage.get("candidatesTokenCount", 0),
        },
    }
