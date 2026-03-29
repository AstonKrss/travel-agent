# backend/nodes/extract_node.py
"""Information extraction node"""

from typing import Dict, Any

from backend.schemas.state import TravelState
from tools.information_extraction import InformationExtractionTool


def extract_node(state: TravelState) -> Dict[str, Any]:
    """Extract trip information from user input"""
    user_input = state.last_message or ""

    # Extract information using the tool
    ie_tool = InformationExtractionTool()
    extracted = ie_tool._run(user_input)

    # Merge with existing trip info
    new_trip = state.trip.model_copy()
    has_new_info = False

    if extracted.departure:
        new_trip.departure = extracted.departure
        has_new_info = True
    if extracted.destination:
        new_trip.destination = extracted.destination
        has_new_info = True
    if extracted.date:
        new_trip.date = extracted.date
        has_new_info = True
    if extracted.passengers > 1:
        new_trip.passengers = extracted.passengers
        has_new_info = True

    if has_new_info:
        new_trip.user_input = user_input

    # Determine if we have complete info
    has_complete_info = bool(
        new_trip.departure and new_trip.destination and new_trip.date
    )

    return {
        "trip": new_trip,
        "extracted": True,
        "need_recommendation": has_complete_info and not state.recommendations,
    }
