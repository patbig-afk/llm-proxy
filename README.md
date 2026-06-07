# LLM Proxy

Proxy de routage intelligent entre Make/n8n et les APIs LLM. Compatible avec le format OpenAI — aucun changement dans vos workflows existants.

## Comment ça marche

Chaque requête entrante est analysée par un classificateur (Claude Haiku) qui évalue la complexité de la tâche, puis route vers le modèle le moins cher capable de la gérer :

| Complexité | Modèle | Usage typique |
|---|---|---|
| SIMPLE | `gemini-2.5-flash` | Extraction, formatage, parsing, classification |
| MEDIUM | `claude-haiku-4-5-20251001` | Rédaction d'email, résumé, reformulation |
| COMPLEX | `claude-sonnet-4-6` | Analyse approfondie, raisonnement, code |

**Économies typiques : 60-80%** par rapport à GPT-4o utilisé par défaut.

---

## Déploiement (Cloud Run)

### Prérequis

- Projet Google Cloud avec Cloud Run activé
- Clés API : Anthropic + Google AI Studio
- Secrets créés dans Secret Manager : `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `PROXY_API_KEY`

### Étapes

1. Créer un dépôt Artifact Registry `llm-proxy` (Docker, région `europe-west9`)

2. Dans Cloud Run → Créer un service :
   - Source : dépôt GitHub `patbig-afk/llm-proxy`, branche `main`
   - Build : Dockerfile
   - Région : `europe-west9`
   - Authentification : autoriser les appels non authentifiés
   - Mémoire : 512 Mo / Timeout : 120s

3. Variables d'environnement (secrets exposés) :

   | Nom de la variable | Secret |
   |---|---|
   | `ANTHROPIC_API_KEY` | `ANTHROPIC_API_KEY:latest` |
   | `GOOGLE_API_KEY` | `GOOGLE_API_KEY:latest` |
   | `PROXY_API_KEY` | `PROXY_API_KEY:latest` |

4. Déployer

---

## Intégration Make / n8n

Dans votre module HTTP, remplacez simplement l'URL OpenAI par l'URL du proxy.

**URL :** `https://llm-proxy-701907145552.europe-west1.run.app/v1/chat/completions`

**Headers :**
```
Content-Type: application/json
X-API-Key: <votre PROXY_API_KEY>
```

**Body (identique à l'API OpenAI) :**
```json
{
  "messages": [
    {"role": "system", "content": "Tu es un assistant..."},
    {"role": "user", "content": "{{votre_variable_make}}"}
  ]
}
```

**Réponse** : même format qu'OpenAI — la valeur de la réponse est dans `choices[0].message.content`.

---

## API

### `POST /v1/chat/completions`

Endpoint principal. Reçoit une requête au format OpenAI, classe la tâche, appelle le bon LLM, retourne la réponse au format OpenAI.

**Auth :** header `X-API-Key: <PROXY_API_KEY>` ou `Authorization: Bearer <PROXY_API_KEY>`

### `GET /debug`

Teste la connexion à chaque provider et retourne les réponses brutes. Utile pour diagnostiquer des problèmes de clés API.

**Auth requise.**

### `GET /health`

Retourne `{"status": "ok"}`. Pas d'auth requise.

---

## Variables d'environnement

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Clé API Anthropic |
| `GOOGLE_API_KEY` | Clé API Google AI Studio |
| `PROXY_API_KEY` | Token d'authentification du proxy (à définir librement) |

---

## Test rapide

```bash
curl -X POST https://llm-proxy-701907145552.europe-west1.run.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: votre_proxy_key" \
  -d '{"messages": [{"role": "user", "content": "Extrais le nom : Patrick Le Grand, 1500€"}]}'
```
