"""Enterprise Travel AI Agent - FastAPI Entry Point"""

import uuid
from typing import Optional, AsyncGenerator, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import asyncio
import os

from backend.config import settings
from backend.agents.graph import travel_graph
from backend.schemas.state import TravelState, TripInfo, IntentType
from backend.schemas.events import SSEEvent, ProcessingStatus
from backend.agents.nodes.booker_node import booker_node

app = FastAPI(
    title="Enterprise Travel AI Agent",
    description="LangGraph-powered corporate travel assistant with multi-node orchestration",
    version="2.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    if settings.allowed_origin == "*"
    else [settings.allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/style.css")
async def serve_css():
    return FileResponse(os.path.join(FRONTEND_DIR, "style.css"))


@app.get("/app.js")
async def serve_js():
    return FileResponse(os.path.join(FRONTEND_DIR, "app.js"))


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    messages: list = []
    recommendations: list = []
    thread_id: str = ""
    current_step: str = "initial"
    intent: Optional[str] = None


class BookRequest(BaseModel):
    action: str = "book"
    rec_id: str
    user_id: str
    thread_id: str


class ApprovalRequest(BaseModel):
    action: str  # "approve" | "reject"
    user_id: str
    thread_id: str


# ---------------------------------------------------------------------------
# State builder
# ---------------------------------------------------------------------------


def build_state(existing: Optional[dict], req: ChatRequest, thread_id: str) -> dict:
    """Build input state for LangGraph invocation."""
    if existing:
        trip_data = existing.get("trip", {})
        if isinstance(trip_data, dict):
            trip = trip_data
        elif hasattr(trip_data, "model_dump"):
            trip = trip_data.model_dump()
        else:
            trip = {}

        order_data = existing.get("order", {})
        if isinstance(order_data, dict):
            order = order_data
        elif hasattr(order_data, "model_dump"):
            order = order_data.model_dump()
        else:
            order = {}

        existing_msgs = existing.get("messages", [])
        return {
            "user_id": req.user_id,
            "thread_id": thread_id,
            "messages": existing_msgs + [{"role": "user", "content": req.message}],
            "last_message": req.message,
            "trip": trip,
            "order": order,
            "current_step": existing.get("current_step", "initial"),
            "intent": existing.get("intent"),
            "booking_status": existing.get("booking_status", "pending"),
            "recommendations": existing.get("recommendations", []),
            "policy_violations": existing.get("policy_violations", []),
            "requires_approval": existing.get("requires_approval", False),
            "policy_approved": existing.get("policy_approved", False),
            "approval_reason": existing.get("approval_reason"),
            "node_timings": existing.get("node_timings", {}),
            "total_tokens": existing.get("total_tokens", 0),
            "errors": existing.get("errors", []),
        }
    else:
        return {
            "user_id": req.user_id,
            "thread_id": thread_id,
            "messages": [{"role": "user", "content": req.message}],
            "last_message": req.message,
            "trip": {},
            "order": {},
            "current_step": "initial",
            "recommendations": [],
            "policy_violations": [],
            "requires_approval": False,
            "policy_approved": False,
            "node_timings": {},
            "total_tokens": 0,
            "errors": [],
        }


# ---------------------------------------------------------------------------
# Streaming generator
# ---------------------------------------------------------------------------


async def stream_chat(req: ChatRequest, thread_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE streaming response using LangGraph astream."""
    config = {"configurable": {"thread_id": thread_id}}

    yield f"data: {SSEEvent.start(thread_id)}\n\n"
    await asyncio.sleep(0.05)

    # Get existing state
    existing = None
    try:
        state_snapshot = travel_graph.get_state(config)
        if state_snapshot and state_snapshot.values:
            existing = state_snapshot.values
    except Exception:
        pass

    input_state = build_state(existing, req, thread_id)

    # Node status map for UX
    node_status_map = {
        "intent": "🧠 正在识别意图...",
        "chat": "💬 正在回复...",
        "extractor": "📋 正在提取信息...",
        "tmc_query": "📜 正在查询方案...",
        "recommend": "🎯 正在智能推荐...",
        "booker": "📦 正在执行预订...",
    }

    final_state = None
    try:
        async for event in travel_graph.astream(
            input_state, config, stream_mode="updates"
        ):
            for node_name, node_output in event.items():
                # Send node status
                status_msg = node_status_map.get(node_name, f"正在执行 {node_name}...")
                yield f"data: {SSEEvent.node(node_name)}\n\n"

                # Stream assistant messages character-by-character for chat node
                if node_name == "chat":
                    for msg in msgs:
                        if msg.get("role") == "assistant":
                            content = msg.get("content", "")
                            for i in range(0, len(content), 10):
                                yield f"data: {SSEEvent.message(content[i : i + 10])}\n\n"
                                await asyncio.sleep(0.02)

                # Check for approval request
                if node_output.get("current_step") == "awaiting_approval":
                    reason = node_output.get("approval_reason", "需要审批")
                    yield f"data: {SSEEvent.approval_request(reason)}\n\n"

                # Stream recommendations
                recs = node_output.get("recommendations", [])
                if recs:
                    trains = [r for r in recs if r.get("type") == "train"]
                    flights = [r for r in recs if r.get("type") == "flight"]
                    hotels = [r for r in recs if r.get("type") == "hotel"]

                    if trains:
                        yield f"data: {SSEEvent.recommendation_category('train', '🚄 高铁/动车')}\n\n"
                        await asyncio.sleep(0.1)
                        for r in trains:
                            yield f"data: {SSEEvent.recommendation(r)}\n\n"
                            await asyncio.sleep(0.1)

                    if flights:
                        yield f"data: {SSEEvent.recommendation_category('flight', '✈️ 航班')}\n\n"
                        await asyncio.sleep(0.1)
                        for r in flights:
                            yield f"data: {SSEEvent.recommendation(r)}\n\n"
                            await asyncio.sleep(0.1)

                    if hotels:
                        yield f"data: {SSEEvent.recommendation_category('hotel', '🏨 酒店')}\n\n"
                        await asyncio.sleep(0.1)
                        for r in hotels:
                            yield f"data: {SSEEvent.recommendation(r)}\n\n"
                            await asyncio.sleep(0.1)

                    yield f"data: {SSEEvent.recommendations_done()}\n\n"

                final_state = node_output

        step = (
            final_state.get("current_step", "complete") if final_state else "complete"
        )
        yield f"data: {SSEEvent.done(step)}\n\n"

    except Exception as e:
        yield f"data: {SSEEvent.error(str(e))}\n\n"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api")
async def api_info():
    return {
        "name": "Enterprise Travel AI Agent",
        "version": "2.0.0",
        "architecture": "LangGraph Multi-Node Orchestration",
        "nodes": [
            "intent",
            "chat",
            "extractor",
            "tmc_query",
            "recommend",
            "booker",
        ],
    }


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE streaming chat with real-time node status."""
    thread_id = req.thread_id or str(uuid.uuid4())
    return StreamingResponse(
        stream_chat(req, thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Thread-Id": thread_id,
        },
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Non-streaming chat endpoint."""
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    existing = None
    try:
        snap = travel_graph.get_state(config)
        if snap and snap.values:
            existing = snap.values
    except Exception:
        pass

    input_state = build_state(existing, req, thread_id)
    result = travel_graph.invoke(input_state, config)

    return ChatResponse(
        messages=result.get("messages", []),
        recommendations=result.get("recommendations", []),
        thread_id=thread_id,
        current_step=result.get("current_step", "initial"),
        intent=result.get("intent"),
    )


@app.post("/api/approve")
async def handle_approval(req: ApprovalRequest):
    """Handle approval/rejection from user."""
    config = {"configurable": {"thread_id": req.thread_id}}

    if req.action == "approve":
        travel_graph.update_state(
            config,
            {
                "policy_approved": True,
                "current_step": "approved",
                "requires_approval": False,
            },
        )
        return {"success": True, "message": "已批准，正在继续预订流程"}
    else:
        travel_graph.update_state(
            config,
            {
                "policy_approved": False,
                "current_step": "rejected",
                "requires_approval": False,
            },
        )
        return {"success": True, "message": "已取消，请调整方案后重试"}


@app.post("/api/book", response_model=dict)
async def handle_book(req: BookRequest):
    """Book a specific recommendation."""
    config = {"configurable": {"thread_id": req.thread_id}}

    try:
        snap = travel_graph.get_state(config)
        current = snap.values if snap else {}
    except Exception:
        current = {}

    recs = current.get("recommendations", [])
    target = None
    for r in recs:
        if r.get("id") == req.rec_id:
            target = r
            break

    if not target:
        raise HTTPException(
            status_code=404, detail=f"Recommendation {req.rec_id} not found"
        )

    # Build minimal state for the booker node (preserves checkpoint state)
    booker_state = {
        "user_id": req.user_id,
        "thread_id": req.thread_id,
        "messages": [],
        "last_message": f"Book {req.rec_id}",
        "recommendations": recs,
    }

    # Invoke only the booker node directly — avoids full graph re-run
    try:
        result = travel_graph.invoke_node("booker", booker_state, config)
    except AttributeError:
        # Fallback for older LangGraph versions
        result = travel_graph.invoke(
            {"user_id": req.user_id, "thread_id": req.thread_id, "messages": [], "last_message": f"Book {req.rec_id}"},
            config,
        )

    return {
        "success": True,
        "order": result.get("order", {}),
        "current_step": result.get("current_step"),
    }


@app.get("/")
async def root():
    """Serve frontend index.html"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not found. Run from project root."}


@app.get("/api/state/{thread_id}")
async def get_state(thread_id: str):
    """Get current conversation state."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snap = travel_graph.get_state(config)
        return snap.values if snap else {}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/graph")
async def get_graph_info():
    """Get graph structure info (for visualization)."""
    return {
        "nodes": [
            "intent",
            "chat",
            "extractor",
            "tmc_query",
            "recommend",
            "booker",
        ],
        "entry_point": "intent",
        "conditional_edges": [
            {"from": "intent", "to": ["chat", "extractor", "booker", "end"]},
            {"from": "extractor", "to": ["tmc_query", "chat", "end"]},
            {"from": "tmc_query", "to": ["recommend"]},
            {"from": "recommend", "to": ["end"]},
            {"from": "booker", "to": ["end"]},
        ],
        "checkpointer": "MemorySaver",
    }


if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
