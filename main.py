import uuid
from typing import Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
import json
import asyncio

from backend.schemas.state import TravelState
from backend.graph import travel_graph
from backend.config import settings
from tools.tmc_api import TMCApiTool
from backend.schemas.events import SSEEvent, ProcessingStatus
from backend.utils.state import (
    create_state_from_existing,
    create_initial_state,
    convert_state_to_dict,
)

app = FastAPI(title="Enterprise Travel Intelligent Agent")

# CORS setup
allow_origins = [settings.allowed_origin] if settings.allowed_origin != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    user_id: str
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    messages: list
    recommendations: list = []
    thread_id: str
    current_step: str


class BookRequest(BaseModel):
    action: str
    type: str
    train_no: Optional[str] = None
    flight_no: Optional[str] = None
    hotel_id: Optional[str] = None
    departure: Optional[str] = None
    destination: Optional[str] = None
    date: Optional[str] = None
    user_id: str
    thread_id: str


@app.get("/")
async def root():
    return {"message": "Enterprise Travel Agent System API"}


async def generate_chat_response(
    request: ChatRequest, thread_id: str
) -> AsyncGenerator[str, None]:
    """Generate streaming response"""
    config = {"configurable": {"thread_id": thread_id}}

    # Send start event
    yield f"data: {SSEEvent.start(thread_id, ProcessingStatus.CONNECTING)}\n\n"
    await asyncio.sleep(0.1)

    # Get existing state
    existing_state = None
    try:
        existing = travel_graph.get_state(config)
        if existing and existing.values:
            existing_state = existing.values
    except Exception as e:
        print(f"获取历史状态失败: {e}")

    # Send status
    yield f"data: {SSEEvent.status(ProcessingStatus.CONNECTING)}\n\n"
    await asyncio.sleep(0.1)

    # Build state
    if existing_state:
        new_messages = existing_state.get("messages", []) + [
            {"role": "user", "content": request.message}
        ]
        state = create_state_from_existing(
            existing_state=existing_state,
            new_messages=new_messages,
            last_message=request.message,
            user_id=request.user_id,
            thread_id=thread_id,
        )
    else:
        state = create_initial_state(
            message=request.message,
            user_id=request.user_id,
            thread_id=thread_id,
        )

    # Stream processing status
    yield f"data: {SSEEvent.status(ProcessingStatus.UNDERSTANDING)}\n\n"
    await asyncio.sleep(0.2)

    yield f"data: {SSEEvent.status(ProcessingStatus.EXTRACTING)}\n\n"
    await asyncio.sleep(0.2)

    try:
        final_state = travel_graph.invoke(state.model_dump(), config)
        final_state_dict = convert_state_to_dict(final_state)

        # Check if need date parsing
        trip_info = final_state_dict.get("trip", {})
        if isinstance(trip_info, dict) and not trip_info.get("date"):
            yield f"data: {SSEEvent.status(ProcessingStatus.PARSING_DATE)}\n\n"
            await asyncio.sleep(0.2)

        # Check if need recommendations
        if final_state_dict.get("need_recommendation") and not final_state_dict.get(
            "recommendations"
        ):
            yield f"data: {SSEEvent.status(ProcessingStatus.SEARCHING_TRAIN)}\n\n"
            await asyncio.sleep(0.3)

            yield f"data: {SSEEvent.status(ProcessingStatus.SEARCHING_FLIGHT)}\n\n"
            await asyncio.sleep(0.3)

            yield f"data: {SSEEvent.status(ProcessingStatus.SEARCHING_HOTEL)}\n\n"
            await asyncio.sleep(0.3)

            yield f"data: {SSEEvent.status(ProcessingStatus.AI_RECOMMENDING)}\n\n"
            await asyncio.sleep(0.3)

            yield f"data: {SSEEvent.status(ProcessingStatus.GENERATING_REASONS)}\n\n"
            await asyncio.sleep(0.2)

        # Check trip date again
        trip_data = final_state_dict.get("trip")
        if trip_data and isinstance(trip_data, dict) and not trip_data.get("date"):
            yield f"data: {SSEEvent.status(ProcessingStatus.PARSING_DATE)}\n\n"
            await asyncio.sleep(0.2)

        # Clear and output message
        yield f"data: {SSEEvent.clear()}\n\n"

        # Get latest assistant message
        all_messages = final_state_dict.get("messages", [])
        latest_response = None
        for msg in reversed(all_messages):
            if msg.get("role") == "assistant":
                latest_response = msg.get("content", "")
                break

        if latest_response:
            for i in range(0, len(latest_response), 20):
                chunk = latest_response[i : i + 20]
                yield f"data: {SSEEvent.message(chunk)}\n\n"
                await asyncio.sleep(0.03)

        # Stream recommendations
        recommendations = final_state_dict.get("recommendations", [])
        if recommendations:
            trains = [r for r in recommendations if r.get("type") == "train"]
            flights = [r for r in recommendations if r.get("type") == "flight"]
            hotels = [r for r in recommendations if r.get("type") == "hotel"]

            if trains:
                yield f"data: {SSEEvent.recommendation_category('train', '🚄 高铁/动车')}\n\n"
                await asyncio.sleep(0.1)
                for rec in trains:
                    yield f"data: {SSEEvent.recommendation(rec)}\n\n"
                    await asyncio.sleep(0.15)

            if flights:
                yield f"data: {SSEEvent.recommendation_category('flight', '✈️ 航班')}\n\n"
                await asyncio.sleep(0.1)
                for rec in flights:
                    yield f"data: {SSEEvent.recommendation(rec)}\n\n"
                    await asyncio.sleep(0.15)

            if hotels:
                yield f"data: {SSEEvent.recommendation_category('hotel', '🏨 酒店')}\n\n"
                await asyncio.sleep(0.1)
                for rec in hotels:
                    yield f"data: {SSEEvent.recommendation(rec)}\n\n"
                    await asyncio.sleep(0.15)

            yield f"data: {SSEEvent.recommendations_done()}\n\n"

        yield f"data: {SSEEvent.done(final_state_dict.get('current_step', 'initial'))}\n\n"

    except Exception as e:
        yield f"data: {SSEEvent.error(str(e))}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint"""
    thread_id = request.thread_id or str(uuid.uuid4())

    return StreamingResponse(
        generate_chat_response(request, thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Thread-Id": thread_id,
        },
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    existing_state = None
    try:
        existing = travel_graph.get_state(config)
        if existing and existing.values:
            existing_state = existing.values
    except Exception as e:
        print(f"获取历史状态失败: {e}")

    if existing_state:
        new_messages = existing_state.get("messages", []) + [
            {"role": "user", "content": request.message}
        ]
        state = create_state_from_existing(
            existing_state=existing_state,
            new_messages=new_messages,
            last_message=request.message,
            user_id=request.user_id,
            thread_id=thread_id,
        )
    else:
        state = create_initial_state(
            message=request.message,
            user_id=request.user_id,
            thread_id=thread_id,
        )

    final_state = travel_graph.invoke(state.model_dump(), config)

    return ChatResponse(
        messages=final_state["messages"],
        recommendations=final_state.get("recommendations", []),
        thread_id=thread_id,
        current_step=final_state.get("current_step", "initial"),
    )


@app.post("/api/order/submit")
async def submit_order(request: BookRequest):
    """Handle booking submission"""

    item_id_map = {
        "train": request.train_no,
        "flight": request.flight_no,
        "hotel": request.hotel_id,
    }

    item_id = item_id_map.get(request.type)
    if not item_id:
        raise HTTPException(
            status_code=400, detail=f"Missing ID for type {request.type}"
        )

    tmc_tool = TMCApiTool()
    booking_result = tmc_tool._run(
        user_id=request.user_id,
        item_type=request.type,
        item_id=item_id,
        details={
            "departure": request.departure,
            "destination": request.destination,
            "date": request.date,
        },
    )

    if not booking_result.success:
        raise HTTPException(status_code=500, detail=booking_result.message)

    config = {"configurable": {"thread_id": request.thread_id}}
    current_state = travel_graph.get_state(config).values

    update = {}

    if request.type in ["train", "flight"]:
        update["order"] = {
            "order_id": booking_result.order_id,
            "status": "booked",
            "ticket_booked": True,
            "hotel_booked": current_state["order"]["hotel_booked"],
            "total_amount": booking_result.amount_charged,
        }
    elif request.type == "hotel":
        update["order"] = {
            "order_id": booking_result.order_id,
            "status": "booked",
            "ticket_booked": current_state["order"]["ticket_booked"],
            "hotel_booked": True,
            "total_amount": booking_result.amount_charged,
        }

    update["current_step"] = "booking"

    travel_graph.invoke(update, config)

    final_state = travel_graph.get_state(config).values

    return {
        "success": True,
        "message": booking_result.message,
        "order_id": booking_result.order_id,
        "amount_charged": booking_result.amount_charged,
        "final_state": {
            "ticket_booked": final_state["order"]["ticket_booked"],
            "hotel_booked": final_state["order"]["hotel_booked"],
            "current_step": final_state["current_step"],
        },
    }


@app.get("/api/state/{thread_id}")
async def get_state(thread_id: str):
    """Get current state for a thread"""
    config = {"configurable": {"thread_id": thread_id}}
    state = travel_graph.get_state(config).values
    return state


if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
