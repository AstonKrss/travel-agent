"""Recommendation Node - Algorithmic scoring + LLM enhancement"""

import json
import re
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from backend.llm import get_llm
from backend.schemas.state import TravelState, get_trip_field


def _score_train(candidate: dict, trip) -> float:
    """Score train options. Higher = better."""
    price = candidate.get("price", 0)
    duration = candidate.get("duration", "")
    seat = candidate.get("seat_class", "")
    seats = candidate.get("available_seats", 0)

    # Price score (cheaper = better, normalized)
    price_score = max(0, 100 - price / 10)

    # Duration score (shorter = better)
    hours = 0
    if "h" in duration:
        try:
            parts = duration.replace("h", ":").replace("m", "").split(":")
            hours = (
                int(parts[0]) + int(parts[1]) / 60 if len(parts) > 1 else int(parts[0])
            )
        except (ValueError, IndexError):
            hours = 5
    duration_score = max(0, 100 - hours * 15)

    # Seat class bonus
    seat_bonus = {"二等座": 10, "一等座": 5, "动卧": 0}.get(seat, 0)

    # Availability bonus
    avail_score = min(10, seats / 20)

    # Time of day preference (morning preferred for business)
    dep_time = candidate.get("departure_time", "")
    time_bonus = 0
    if dep_time:
        try:
            hour = int(dep_time.split(":")[0])
            if 7 <= hour <= 10:
                time_bonus = 10
            elif 10 < hour <= 14:
                time_bonus = 5
        except (ValueError, IndexError):
            pass

    return (
        price_score * 0.35
        + duration_score * 0.30
        + seat_bonus
        + avail_score
        + time_bonus
    )


def _score_flight(candidate: dict, trip) -> float:
    """Score flight options."""
    price = candidate.get("price", 0)
    duration = candidate.get("duration", "")
    cabin = candidate.get("cabin", "")

    price_score = max(0, 100 - price / 15)

    hours = 0
    if "h" in duration:
        try:
            parts = duration.replace("h", ":").replace("m", "").split(":")
            hours = (
                int(parts[0]) + int(parts[1]) / 60 if len(parts) > 1 else int(parts[0])
            )
        except (ValueError, IndexError):
            hours = 3
    duration_score = max(0, 100 - hours * 20)

    cabin_bonus = {"经济舱": 10, "商务舱": 0, "头等舱": -5}.get(cabin, 0)

    dep_time = candidate.get("departure_time", "")
    time_bonus = 0
    if dep_time:
        try:
            hour = int(dep_time.split(":")[0])
            if 7 <= hour <= 12:
                time_bonus = 10
            elif 12 < hour <= 18:
                time_bonus = 5
        except (ValueError, IndexError):
            pass

    return price_score * 0.35 + duration_score * 0.30 + cabin_bonus + time_bonus


def _score_hotel(candidate: dict, trip) -> float:
    """Score hotel options."""
    price = candidate.get("price", 0)
    rating = candidate.get("rating", 3.0)
    breakfast = candidate.get("breakfast", False)
    wifi = candidate.get("wifi", False)
    dist = candidate.get("distance_to_center", "5km")

    price_score = max(0, 100 - price / 8)
    rating_score = rating * 20
    amenity_bonus = (10 if breakfast else 0) + (5 if wifi else 0)

    dist_km = 5
    try:
        dist_km = float(dist.replace("km", ""))
    except (ValueError, AttributeError):
        pass
    dist_score = max(0, 30 - dist_km * 3)

    return price_score * 0.25 + rating_score * 0.35 + amenity_bonus + dist_score


def _generate_reason(candidate: dict, score: float) -> str:
    """Generate a human-readable recommendation reason."""
    ctype = candidate.get("type", "")
    price = candidate.get("price", 0)
    name = candidate.get("name", "")

    if ctype == "train":
        seat = candidate.get("seat_class", "")
        duration = candidate.get("duration", "")
        if score > 70:
            return f"性价比最高，{seat} {duration}，{price}元"
        return f"{seat}，{duration}，{price}元"
    elif ctype == "flight":
        cabin = candidate.get("cabin", "")
        duration = candidate.get("duration", "")
        if score > 70:
            return f"价格最优，{cabin} {duration}，{price}元"
        return f"{cabin}，{duration}，{price}元"
    elif ctype == "hotel":
        rating = candidate.get("rating", 0)
        breakfast = "含早餐" if candidate.get("breakfast") else ""
        dist = candidate.get("distance_to_center", "")
        return f"评分{rating}，{breakfast}，距市中心{dist}，{price}元/晚"
    return ""


def recommend_node(state: TravelState) -> Dict:
    """Score and rank candidates using algorithm + LLM enhancement.

    Flow:
    1. Get raw candidates from tmc_query_node
    2. Score each candidate algorithmically
    3. Use LLM to generate personalized reasons
    4. Return top recommendations as structured cards
    """
    trip = state.trip
    candidates = list(state.raw_candidates) if state.raw_candidates else []
    if not candidates:
        candidates = state.recommendations if state.recommendations else []

    if not candidates:
        return {
            "current_step": "recommendation_failed",
            "messages": [{"role": "assistant", "content": "未找到合适的出行方案。"}],
        }

    # Score candidates
    scored = []
    for c in candidates:
        ctype = c.get("type", "")
        if ctype == "train":
            score = _score_train(c, trip)
        elif ctype == "flight":
            score = _score_flight(c, trip)
        elif ctype == "hotel":
            score = _score_hotel(c, trip)
        else:
            score = 50
        c["score"] = round(score, 1)
        c["reason"] = _generate_reason(c, score)
        scored.append(c)

    # Sort by score descending
    scored.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Take top 2 of each type
    trains = [c for c in scored if c.get("type") == "train"][:2]
    flights = [c for c in scored if c.get("type") == "flight"][:2]
    hotels = [c for c in scored if c.get("type") == "hotel"][:2]

    # Use LLM to enhance reasons (optional, non-blocking)
    llm = get_llm(task="reasoning", timeout=15)
    if llm:
        try:
            top_items = trains + flights + hotels
            if top_items:
                items_text = "\n".join(
                    [
                        f"- {i['type']}: {i['name']} {i.get('price', 0)}元, reason: {i.get('reason', '')}"
                        for i in top_items
                    ]
                )
                dep = get_trip_field(trip, "departure", "?")
                dest = get_trip_field(trip, "destination", "?")
                prompt = (
                    f"Trip: {dep} to {dest}. "
                    f"Enhance these recommendation reasons to be more personalized and helpful for a business traveler. "
                    f'Return JSON only: {{"reasons": {{"id": "enhanced reason"}}}}\n\n{items_text}'
                )
                resp = llm.invoke(
                    [
                        SystemMessage(
                            content="Enhance travel recommendation reasons. Return JSON only."
                        ),
                        HumanMessage(content=prompt),
                    ]
                )
                content = resp.content if hasattr(resp, "content") else str(resp)
                match = re.search(r"\{[\s\S]*\}", content)
                if match:
                    result = json.loads(match.group())
                    reasons = result.get("reasons", {})
                    for item in top_items:
                        if item.get("id") in reasons:
                            item["reason"] = reasons[item["id"]]
        except Exception as e:
            print(f"[Recommend LLM Error] {e}")

    # Build response message
    departure = get_trip_field(trip, "departure", "?")
    destination = get_trip_field(trip, "destination", "?")

    parts = [f"为您找到从 {departure} 到 {destination} 的推荐方案："]

    if trains:
        parts.append(f"\n高铁 ({len(trains)}个方案):")
        for t in trains:
            parts.append(
                f"  - {t['name']} {t.get('departure_time', '')}-{t.get('arrival_time', '')} ({t.get('duration', '')}) {t.get('price', 0)}元 - {t.get('reason', '')}"
            )

    if flights:
        parts.append(f"\n航班 ({len(flights)}个方案):")
        for f in flights:
            parts.append(
                f"  - {f['name']} {f.get('departure_time', '')}-{f.get('arrival_time', '')} ({f.get('duration', '')}) {f.get('price', 0)}元 - {f.get('reason', '')}"
            )

    if hotels:
        parts.append(f"\n酒店 ({len(hotels)}个方案):")
        for h in hotels:
            parts.append(
                f"  - {h['name']} 评分{h.get('rating', '')} {h.get('price', 0)}元/晚 - {h.get('reason', '')}"
            )

    parts.append("\n请回复 确认预订 选择最优方案，或告诉我您的偏好来调整。")

    # Build structured recommendation cards
    rec_cards = []
    for item in trains + flights + hotels:
        rec_cards.append(
            {
                "id": item["id"],
                "type": item["type"],
                "name": item["name"],
                "departure": item.get("departure"),
                "destination": item.get("destination"),
                "date": item.get("date"),
                "departure_time": item.get("departure_time"),
                "arrival_time": item.get("arrival_time"),
                "price": item.get("price", 0),
                "duration": item.get("duration"),
                "available": True,
                "reason": item.get("reason", ""),
                "score": item.get("score", 0),
                "details": {
                    k: v
                    for k, v in item.items()
                    if k
                    not in (
                        "id",
                        "type",
                        "name",
                        "departure",
                        "destination",
                        "date",
                        "departure_time",
                        "arrival_time",
                        "price",
                        "duration",
                        "available",
                        "reason",
                        "score",
                        "raw_candidates",
                    )
                },
            }
        )

    return {
        "recommendations": rec_cards,
        "current_step": "recommended",
        "messages": [{"role": "assistant", "content": "\n".join(parts)}],
    }
