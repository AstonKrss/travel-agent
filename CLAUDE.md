# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Enterprise Travel AI Agent** — a LangGraph-powered system automating the full corporate travel lifecycle: intent recognition → information extraction → policy check (RAG) → itinerary planning → intelligent recommendation → human-in-the-loop approval → booking execution.

## Running the App

```bash
pip install -r requirements.txt
python main.py
```

Then open `frontend/index.html` in a browser (or visit `http://localhost:8000`).

## Key Commands

- **Run server**: `python main.py` (serves on `0.0.0.0:8000`)
- **Environment config**: Copy `.env.example` to `.env` and fill in API keys

## Architecture

### LangGraph State Machine

The core is a `StateGraph` (`backend/agents/graph.py`) with **conditional routing**. The flow:

```
intent → extractor → tmc_query → recommend → END
              ↓                        ↑
            chat                  booker → END
```

- **`intent_node`** — Fast LLM classification into: `greeting`, `chat`, `trip_query`, `book`, `approve`, `cancel`, `expense`
- **`extractor_node`** — Extracts structured trip info (departure, destination, date, passengers)
- **`tmc_query_node`** — Queries TMC/mock API for available trains, flights, hotels; populates `raw_candidates`
- **`recommend_node`** — Scores `raw_candidates` from `tmc_query` algorithmically (price + duration + amenities) then enhances reasons with LLM; stops at END waiting for user selection
- **`booker_node`** — Executes booking via TMC API (company-paid, no employee payment); can be invoked directly via `travel_graph.invoke_node("booker", ...)` without re-running the full graph
- **`chat_node`** — Handles greetings, cancellation, expense queries

### Conditional Routing Logic (`backend/agents/graph.py`)

- After `intent`: routes to `chat` for greetings/cancels/expenses; to `extractor` for trip queries; to `booker` if user confirms existing recommendations
- After `extractor`: routes to `tmc_query` only when `departure` + `destination` + `date` are all present; otherwise falls back to `chat`
- After `recommend`: **always stops at END** — user must send a follow-up message with their selection to trigger `booker`

### State Model (`backend/schemas/state.py`)

`TravelState` is the central state object. Key patterns:
- `messages` uses the `add_messages` **reducer** — appends new messages, replaces last assistant message if new one is also from assistant
- `recommendations` holds LLM-ranked results; `raw_candidates` holds TMC query results pre-ranking
- `requires_approval` / `policy_approved` control the approval interruption flow
- `node_timings` and `errors` track observability per node

### LLM Routing (`backend/llm/__init__.py`)

`get_llm(task)` returns a `ChatOpenAI` instance:
- `task="intent"` / `"extraction"` → low temperature (0.1), smaller/faster model
- `task="reasoning"` → higher temperature (0.3), larger model for complex tasks
- Provider is configured via `LLM_PROVIDER` env var (`openai` or `volcano`)
- Each provider has separate keys and base URLs in `backend/config.py`

### RAG Policy Check (`backend/rag/__init__.py`)

`PolicyRetriever` holds hardcoded corporate travel policy documents. `check_policy()` validates recommendations against budget thresholds (flight ≤2000 CNY, train ≤1000 CNY, hotel ≤600 CNY). In production, replace keyword matching with vector search.

### Checkpointing

The graph uses `MemorySaver` with a `JsonPlusSerializer` allowlist — supports resume for a given `thread_id`. Always pass `thread_id` when invoking the graph to enable state persistence across requests.

### Observability (`backend/observability/__init__.py`)

`NodeTracer` uses context managers to track per-node elapsed time. The global `tracer` instance is available for import.

## Tool Layer (`tools/`)

- `tmc_api.py` — `TMCApiTool` (LangChain `BaseTool`) for querying availability and booking. Falls back to mock data when `TMC_API_BASE_URL` is not set.
- `oa_finance.py` — Finance/OA sync (no-op in current version)
- `travel_recommendation.py` — Alternative recommendation logic
- `information_extraction.py` — Standalone LLM-based extraction utility

## Frontend (`frontend/`)

Serves static files via FastAPI. The UI is dark-themed and communicates with the backend via SSE (`/api/chat/stream`) for real-time node status updates and recommendation card streaming.

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/chat/stream` | POST | SSE streaming chat |
| `/api/chat` | POST | Non-streaming chat |
| `/api/approve` | POST | Handle approval/rejection via `update_state` |
| `/api/book` | POST | Trigger booking on a selected recommendation |
| `/api/state/{thread_id}` | GET | Get current conversation state |
| `/api/graph` | GET | Get graph structure info |

## Important Conventions

- Always check `thread_id` before invoking the graph — use `travel_graph.get_state(config)` to retrieve existing state, then pass it to `build_state()` in `main.py`
- The `recommend` node stops at END and waits for user selection — do not expect auto-continuation
- Use `travel_graph.invoke_node("booker", ...)` for `/api/book` — never re-invoke the full graph with an empty `messages` dict, which discards checkpoint state
- Trip field access: use `get_trip_field(trip, field_name, default)` from `backend.schemas.state` — do not use `isinstance + getattr` inline
- Date/route/passenger extraction utilities live in `tools/information_extraction.py` — import from there, don't duplicate patterns
