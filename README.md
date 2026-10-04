# ReBounce

ReBounce is a persistent personal AI companion.

## Current state

Stages 0–4 are implemented as a headless companion core plus a polished web dashboard.

### Stage 2 — Real memory
- structured facts, preferences, projects, goals and episodic memories
- deterministic extraction plus model-ready memory contract
- relevance retrieval
- contradiction handling through superseded history
- provenance, confidence and importance
- user correction and deletion
- portable JSON export

### Stage 3 — Identity + relationship
- stable user-named identity
- interaction continuity
- active-day and interaction tracking
- recurring-topic tracking
- lightweight preference adaptation
- milestones
- goals
- commitments
- relationship context injected into the model

### Stage 4 — Dashboard
- Chat
- conversation history
- Memory viewer/search/filter
- Relationship/timeline
- Goals and commitments
- Activity/audit history
- Model/provider settings
- Trust Center
- Companion identity settings
- Data export

The dashboard is intentionally avatar-free for now. Voice and desktop presence remain later stages.

## Run locally

    python -m venv .venv
    # Windows: .venv\Scripts\activate
    # Linux/macOS: source .venv/bin/activate
    python -m pip install -e .

Start:

    python -m rebounce_core.api

Open:

    http://127.0.0.1:4100/

The default provider is the deterministic stub, so the UI can be explored without an API key.

## Use a real model

Any OpenAI-compatible chat-completions server can be used:

    python -m rebounce_core.api \
      --model-url http://127.0.0.1:8080/v1 \
      --model your-model

For a provider requiring a key:

    python -m rebounce_core.api \
      --model-url https://api.example.com/v1 \
      --model your-model \
      --api-key YOUR_KEY

The dashboard also exposes Model settings. API keys are held by the running process/provider adapter and are not written into companion memory or SQLite.

Environment variables:

    REBOUNCE_DB
    REBOUNCE_HOST
    REBOUNCE_PORT
    REBOUNCE_MODEL_URL
    REBOUNCE_MODEL
    REBOUNCE_MODEL_API_KEY

## API

    GET  /health
    GET  /v1/companions?user_id=...
    POST /v1/companions
    GET  /v1/companions/{id}
    GET  /v1/companions/{id}/dashboard
    GET  /v1/companions/{id}/conversations/{conversation_id}
    POST /v1/companions/{id}/chat
    GET  /v1/companions/{id}/memories
    POST /v1/companions/{id}/memories
    PATCH /v1/companions/{id}/memories/{memory_id}
    DELETE /v1/companions/{id}/memories/{memory_id}
    GET  /v1/companions/{id}/relationship
    POST /v1/companions/{id}/milestones
    POST /v1/companions/{id}/goals
    PATCH /v1/companions/{id}/goals/{goal_id}
    POST /v1/companions/{id}/commitments
    GET  /v1/companions/{id}/events
    GET  /v1/companions/{id}/export
    PATCH /v1/companions/{id}/settings
    GET/POST /v1/config/provider
    POST /v1/config/provider/test

## Verification

Run:

    python -m unittest discover -s tests -v

GitHub Actions validates the suite on Windows, Linux and macOS with Python 3.13 and 3.14.

`REBOUNCE_MASTER_PLAN.md` remains the single living product/research source of truth.