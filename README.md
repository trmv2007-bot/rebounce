# ReBounce

ReBounce is a persistent personal AI companion project.

The long-term goal is one durable companion identity that can evolve from conversation into memory, relationship continuity, voice, presence, proactive behavior, curiosity, tools, vision, multi-device continuity and richer digital/physical embodiment.

## Stage 0 — Foundation

Stage 0 establishes the engineering contracts before feature-heavy work begins.

Current foundation:

- OS-agnostic Python core targeting Python 3.13+
- Windows, Linux and macOS as first-class desktop targets
- Android, iOS/iPadOS and Web as later clients
- SQLite-first durable storage
- user-named companion identity
- provider-neutral model interface
- event model
- deterministic permission policy
- minimal companion runtime
- zero third-party runtime dependencies in the core
- automated Stage 0 tests

The architecture is designed so companion identity and memory can survive model/provider changes.

## Project layout

- src/rebounce_core/ — domain/runtime foundation
- tests/ — Stage 0 tests
- REBOUNCE_MASTER_PLAN.md — single living product/research source of truth

## Run

Create a virtual environment and install the package in editable mode:

    python -m venv .venv
    # Windows: .venv\Scripts\activate
    # Linux/macOS: source .venv/bin/activate
    python -m pip install -e .

Run tests:

    python -m unittest discover -s tests -v

## Current Stage 0 behavior

The repository currently wires:

    user message
        -> conversation persistence
        -> USER_MESSAGE event
        -> provider abstraction
        -> assistant persistence
        -> ASSISTANT_MESSAGE event

The included stub provider is deliberately not an AI model. It exists only to prove the runtime contract before Stage 1 connects real providers.

## Planning rule

REBOUNCE_MASTER_PLAN.md is the single living product/research source of truth.

Future ideas belong in that file first. Build stages should only absorb an idea after we decide it is ready.
