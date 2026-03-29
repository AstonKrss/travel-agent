# backend/utils/state.py
"""State conversion utilities for LangGraph"""

from typing import Optional, Dict, Any
from backend.schemas.state import TravelState, TripInfo, OrderInfo


def create_state_from_existing(
    existing_state: Optional[Dict[str, Any]],
    new_messages: list,
    last_message: str,
    user_id: str,
    thread_id: str,
) -> TravelState:
    """Create TravelState from existing state (for continuing conversation)"""

    # Build trip info
    trip_data = existing_state.get("trip", {}) if existing_state else {}
    try:
        if hasattr(trip_data, "model_dump"):
            trip_dict = trip_data.model_dump()
        elif isinstance(trip_data, dict):
            trip_dict = trip_data
        else:
            trip_dict = {}
        trip = TripInfo(**trip_dict)
    except Exception as e:
        print(f"创建 TripInfo 失败: {e}, trip_data: {trip_data}")
        trip = TripInfo()

    # Build order info
    order_data = existing_state.get("order", {}) if existing_state else {}
    try:
        if hasattr(order_data, "model_dump"):
            order = OrderInfo(**order_data.model_dump())
        elif isinstance(order_data, dict):
            order = OrderInfo(**order_data)
        else:
            order = OrderInfo()
    except Exception as e:
        print(f"创建 OrderInfo 失败: {e}")
        order = OrderInfo()

    # Build recommendations
    recommendations = (
        existing_state.get("recommendations", []) if existing_state else []
    )

    return TravelState(
        user_id=user_id,
        thread_id=thread_id,
        messages=new_messages,
        last_message=last_message,
        trip=trip,
        order=order,
        extracted=existing_state.get("extracted", False) if existing_state else False,
        need_recommendation=existing_state.get("need_recommendation", False)
        if existing_state
        else False,
        current_step=existing_state.get("current_step", "initial")
        if existing_state
        else "initial",
        recommendations=recommendations,
        conversation_summary=existing_state.get("conversation_summary")
        if existing_state
        else None,
    )


def create_initial_state(
    message: str,
    user_id: str,
    thread_id: str,
) -> TravelState:
    """Create initial TravelState for new conversation"""
    return TravelState(
        user_id=user_id,
        thread_id=thread_id,
        messages=[{"role": "user", "content": message}],
        last_message=message,
    )


def convert_state_to_dict(state: Any) -> Dict[str, Any]:
    """Convert state to dictionary for further processing"""
    result = {}
    for key, value in state.items():
        if hasattr(value, "model_dump"):
            result[key] = value.model_dump()
        else:
            result[key] = value
    return result


__all__ = [
    "create_state_from_existing",
    "create_initial_state",
    "convert_state_to_dict",
]
