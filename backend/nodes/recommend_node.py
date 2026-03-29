# backend/nodes/recommend_node.py
"""Recommendation node"""

from typing import Dict, Any, List

from backend.schemas.state import TravelState
from backend.schemas.recommendation import RecommendationItem


def recommend_node(state: TravelState) -> Dict[str, Any]:
    """Generate travel recommendations"""
    from tools.travel_recommendation import TravelRecommendationTool

    rec_tool = TravelRecommendationTool()

    # Get recommendations
    recommendations, reasons = rec_tool._run(
        departure=state.trip.departure,
        destination=state.trip.destination,
        travel_date=state.trip.date,
        passengers=state.trip.passengers,
    )

    # Build response text with reasons
    if reasons:
        reason_texts = []
        for item in recommendations[:3]:
            if item.id in reasons:
                reason_texts.append(f"• {item.name}: {reasons[item.id]}")

        response_text = (
            f"为您找到了从 {state.trip.departure} 到 {state.trip.destination} 的出行方案：\n"
            + "\n".join(reason_texts)
        )
    else:
        response_text = f"为您找到了从 {state.trip.departure} 到 {state.trip.destination} 的出行方案。请选择以下选项："

    # Convert to dict
    rec_list = []
    for item in recommendations:
        if hasattr(item, "model_dump"):
            rec_list.append(item.model_dump())
        else:
            rec_list.append(
                {
                    "id": item.id,
                    "type": item.type,
                    "name": item.name,
                    "departure": item.departure,
                    "destination": item.destination,
                    "date": item.date,
                    "departure_time": item.departure_time,
                    "arrival_time": item.arrival_time,
                    "price": item.price,
                    "duration": item.duration,
                    "available": item.available,
                    "details": item.details,
                }
            )

    return {
        "recommendations": rec_list,
        "current_step": "recommended",
        "messages": state.messages + [{"role": "assistant", "content": response_text}],
    }
