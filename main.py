from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import logging
from classifier import classify_prompt
from router import route_to_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Proxy", version="1.0.0")

API_KEY = os.getenv("PROXY_API_KEY", "")


def check_auth(request: Request):
    if not API_KEY:
        return
    key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").removeprefix("Bearer ")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.post("/v1/chat/completions")
async def proxy_completions(request: Request):
    check_auth(request)
    body = await request.json()

    messages = body.get("messages", [])
    full_text = " ".join(
        m.get("content", "") if isinstance(m.get("content"), str) else ""
        for m in messages
    )

    complexity = await classify_prompt(full_text)
    result = await route_to_model(complexity, body)

    logger.info(f"complexity={complexity} model={result.get('_routed_model')} tokens={result.get('usage', {})}")
    result.pop("_routed_model", None)

    return JSONResponse(content=result)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug")
async def debug(request: Request):
    check_auth(request)
    import httpx, os
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    google_key = os.getenv("GOOGLE_API_KEY", "")
    results = {}

    # Test Anthropic
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-3-5-haiku-20241022", "max_tokens": 10, "messages": [{"role": "user", "content": "Say OK"}]},
            )
            results["anthropic"] = r.json()
    except Exception as e:
        results["anthropic"] = {"error": str(e)}

    # Test Gemini
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={google_key}",
                json={"contents": [{"role": "user", "parts": [{"text": "Say OK"}]}]},
            )
            results["gemini"] = r.json()
    except Exception as e:
        results["gemini"] = {"error": str(e)}

    return results
