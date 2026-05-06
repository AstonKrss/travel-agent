"""Information Extraction Node - Structured extraction using LLM + regex"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from backend.llm import get_llm
from backend.schemas.state import TravelState, TripInfo, get_trip_field


# Re-exported so existing callers don't break
from tools.information_extraction import (
    DAY_MAP,
    resolve_date,
    extract_route,
    extract_passengers,
    extract_budget,
    parse_date_with_llm,
)


def extractor_node(state: TravelState) -> Dict:
    """Extract structured trip information from user input."""
    # Prefer last_message; fall back to last user message in history
    last_msg = state.last_message
    if not last_msg:
        for msg in reversed(state.messages):
            if msg.get("role") == "user":
                last_msg = msg.get("content", "")
                break
    last_msg = last_msg or ""

    # Rule-based extraction first
    departure, destination = extract_route(last_msg)
    passengers = extract_passengers(last_msg)
    budget = extract_budget(last_msg)
    date_str = resolve_date(last_msg)

    # Use LLM to fill gaps
    if not departure or not destination or not date_str:
        llm = get_llm(task="extraction", timeout=15)
        if llm:
            try:
                today_str = datetime.now().date().isoformat()
                system_msg = (
                    "Extract travel information from user input. "
                    "Return ONLY JSON with these keys: departure, destination, date (YYYY-MM-DD), "
                    "return_date (YYYY-MM-DD), passengers (integer), budget (number). "
                    f"Today is {today_str}. Resolve relative dates."
                )
                resp = llm.invoke(
                    [
                        SystemMessage(content=system_msg),
                        HumanMessage(content="User input: " + last_msg),
                    ]
                )
                content = resp.content if hasattr(resp, "content") else str(resp)
                match = re.search(r"\{[\s\S]*\}", content)
                if match:
                    llm_result = json.loads(match.group())
                    departure = departure or llm_result.get("departure")
                    destination = destination or llm_result.get("destination")
                    date_str = date_str or llm_result.get("date")
                    passengers = passengers or llm_result.get("passengers", 1)
                    budget = budget or llm_result.get("budget")
            except Exception as e:
                print(f"[Extractor LLM Error] {e}")

    # Merge with existing trip info
    existing = state.trip.model_dump() if hasattr(state.trip, "model_dump") else {}

    new_trip = TripInfo(
        departure=departure or existing.get("departure"),
        destination=destination or existing.get("destination"),
        date=date_str or existing.get("date"),
        return_date=existing.get("return_date"),
        passengers=passengers if passengers != 1 else existing.get("passengers", 1),
        budget=budget or existing.get("budget"),
        preferences=existing.get("preferences"),
        trip_type=existing.get("trip_type", "one_way"),
    )

    missing = new_trip.missing_fields
    info_status = "complete" if not missing else f"missing: {', '.join(missing)}"

    return {
        "trip": new_trip,
        "current_step": "extracted",
        "messages": [
            {
                "role": "assistant",
                "content": f"已提取信息: {departure or '?'} -> {destination or '?'}, 日期: {date_str or '?'}, 人数: {passengers} [{info_status}]",
            }
        ]
        if not state.messages
        else [],
    }
