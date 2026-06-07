import os
import httpx
import json

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

CLASSIFIER_PROMPT = """Classifie la tâche demandée dans ce prompt en une seule catégorie :

- SIMPLE : extraction de données, formatage, parsing, classification, vérification de format
- MEDIUM : rédaction d'email, résumé, reformulation, génération de contenu simple
- COMPLEX : analyse approfondie, raisonnement multi-étapes, stratégie, comparaison critique, code complexe

Réponds UNIQUEMENT avec un mot : SIMPLE, MEDIUM ou COMPLEX.

Prompt à classifier :
"""


async def classify_prompt(text: str) -> str:
    if not text.strip():
        return "MEDIUM"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": CLASSIFIER_PROMPT + text[:1000]}],
                },
            )
            data = resp.json()
            category = data["content"][0]["text"].strip().upper()
            if category in ("SIMPLE", "MEDIUM", "COMPLEX"):
                return category
    except Exception:
        pass

    return "MEDIUM"
