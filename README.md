# ReBounce

ReBounce is a persistent personal AI companion project.

The long-term goal is one durable companion identity that can evolve from conversation into memory, relationship continuity, voice, presence, proactive behavior, curiosity, tools, vision, multi-device continuity and richer digital/physical embodiment.

## Stage 1 — Minimal Companion Brain

Stage 1 turns the Stage 0 foundation into a usable headless companion runtime.

Included:

- persistent, user-named companion identity
- conversation persistence and replay
- provider-neutral model adapter
- OpenAI-compatible adapter for local or remote `/v1/chat/completions` servers
- streaming responses
- runtime current state
- model-unavailable events
- localhost HTTP API
- cross-platform automated tests

The API defaults to `127.0.0.1`; it is intentionally a local development surface rather than an internet-facing service.

## Project layout

- `src/rebounce_core/` — domain/runtime/API foundation
- `tests/` — automated tests
- `REBOUNCE_MASTER_PLAN.md` — single living product/research source of truth

## Run

Create a virtual environment and install the package:

    python -m venv .venv
    # Windows: .venv\\Scripts\\activate
    # Linux/macOS: source .venv/bin/activate
    python -m pip install -e .

Run all tests:

    python -m unittest discover -s tests -v

## Start the local API

The Stage 1 API can run immediately with the deterministic stub:

    python -m rebounce_core.api

For an actual local model, point it at an OpenAI-compatible server:

    python -m rebounce_core.api \
      --model-url http://127.0.0.1:8080/v1 \
      --model your-model

The following environment variables are also supported:

    REBOUNCE_DB
    REBOUNCE_HOST
    REBOUNCE_PORT
    REBOUNCE_MODEL_URL
    REBOUNCE_MODEL
    REBOUNCE_MODEL_API_KEY

The default bind address is localhost only.

## Connect a local model from Python

    from rebounce_core.provider import OpenAICompatibleProvider

    provider = OpenAICompatibleProvider(
        "http://127.0.0.1:8080/v1",
        default_model="your-model",
    )

The companion runtime remains independent of the provider, so the model can be replaced without replacing the companion identity or SQLite data.

## Local API

Endpoints:

    GET  /health
    POST /v1/companions
    GET  /v1/companions/{companion_id}
    POST /v1/companions/{companion_id}/chat

Create a companion:

    {
      "user_id": "user-1",
      "name": "Nova",
      "personality": "calm and direct"
    }

Chat:

    {
      "content": "Hello",
      "conversation_id": "optional-existing-conversation-id",
      "model": "optional-model-name",
      "stream": false
    }

Set `stream` to `true` for Server-Sent Events. Conversation history is loaded from SQLite and sent through the provider adapter on every turn.

## Stage 2 next

Stage 2 adds the real memory engine: facts, episodes, entities, preferences, projects, retrieval, consolidation, provenance, contradiction handling, correction, deletion and export.

## Planning rule

`REBOUNCE_MASTER_PLAN.md` is the single living product/research source of truth.

Future ideas belong in that file first. Build stages should only absorb an idea after we decide it is ready.
