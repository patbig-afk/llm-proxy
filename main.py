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
