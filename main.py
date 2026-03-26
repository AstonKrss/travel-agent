import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from backend.state import TravelState
from backend.graph import travel_graph
from backend.config import settings
from tools.tmc_api import TMCApiTool

from langgraph.checkpoint.memory import MemorySaver

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


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Try to get existing state
    existing_state = None
    try:
        existing = travel_graph.get_state(config)
        if existing and existing.values:
            existing_state = existing.values
    except Exception as e:
        print(f"获取历史状态失败: {e}")

    if existing_state:
        # Continue existing conversation
        new_messages = existing_state.get("messages", []) + [
            {"role": "user", "content": request.message}
        ]

        # Build updated state
        from backend.state import TripInfo, OrderInfo

        trip_data = existing_state.get("trip", {})
        if isinstance(trip_data, dict):
            trip = TripInfo(**trip_data)
        else:
            trip = trip_data or TripInfo()

        order_data = existing_state.get("order", {})
        if isinstance(order_data, dict):
            order = OrderInfo(**order_data)
        else:
            order = order_data or OrderInfo()

        state = TravelState(
            user_id=request.user_id,
            thread_id=thread_id,
            messages=new_messages,
            last_message=request.message,
            trip=trip,
            order=order,
            extracted=existing_state.get("extracted", False),
            need_recommendation=existing_state.get("need_recommendation", False),
            current_step=existing_state.get("current_step", "initial"),
            recommendations=existing_state.get("recommendations", []),
        )
    else:
        # New conversation
        state = TravelState(
            user_id=request.user_id,
            thread_id=thread_id,
            messages=[{"role": "user", "content": request.message}],
            last_message=request.message,
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
    """Handle booking submission from frontend and update LangGraph state"""

    # Extract item ID based on type
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

    # 1. Use TMC API to book (company direct payment)
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

    # 2. Update LangGraph state with booking information
    config = {"configurable": {"thread_id": request.thread_id}}

    # Get current state
    current_state = travel_graph.get_state(config).values

    # Update state with booking info
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

    # Continue the graph execution
    travel_graph.invoke(update, config)

    # Get final state after update
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
