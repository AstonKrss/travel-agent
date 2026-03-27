from typing import List, Dict
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from datetime import date
import requests

from backend.config import settings
from backend.state import RecommendationItem


class RecommendationInput(BaseModel):
    departure: str = Field(description="Departure city")
    destination: str = Field(description="Destination city")
    travel_date: date = Field(description="Travel date")
    passengers: int = Field(default=1, description="Number of passengers")


LLM_PROMPT = """You are a travel consultant. Recommend top 3 from candidates based on user preference.

User: {passengers} people, from {departure} to {destination}, date: {date}
Preference: {preferences}

Candidates:
{candidates}

Return JSON only:
{{"recommendations": [{{"id": "ID", "reason": "reason"}}]}}"""


def get_llm():
    """Get LLM instance"""
    try:
        from langchain_openai import ChatOpenAI
    except:
        return None

    if settings.llm_provider == "volcano":
        return ChatOpenAI(
            api_key=settings.volcano_api_key,
            base_url=settings.volcano_base_url,
            model=settings.volcano_model,
            temperature=0.3,
            timeout=15,
        )
    elif settings.llm_provider == "openai":
        return ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            temperature=0.3,
            timeout=15,
        )
    return None


def rank_with_llm(
    candidates: List[RecommendationItem],
    passengers: int,
    departure: str,
    destination: str,
    travel_date: str,
    preferences: str = "price-performance ratio",
) -> tuple[List[RecommendationItem], Dict]:
    """Use LLM to intelligently rank candidates"""

    llm = get_llm()
    if not llm:
        return candidates[:5], {}

    # Format candidates
    txt = ""
    for i, item in enumerate(candidates):
        if item.type == "train":
            txt += f"{i + 1}. [train] {item.name}, time: {item.departure_time}->{item.arrival_time}, duration: {item.duration}, price: {item.price}\n"
        elif item.type == "flight":
            txt += f"{i + 1}. [flight] {item.name}, time: {item.departure_time}->{item.arrival_time}, duration: {item.duration}, price: {item.price}\n"
        elif item.type == "hotel":
            r = item.details.get("rating", "N/A") if item.details else "N/A"
            txt += f"{i + 1}. [hotel] {item.name}, rating: {r}, price: {item.price}/night\n"

    prompt = LLM_PROMPT.format(
        passengers=passengers,
        departure=departure,
        destination=destination,
        date=travel_date,
        preferences=preferences,
        candidates=txt,
    )

    from langchain_core.messages import HumanMessage

    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        content = resp.content if hasattr(resp, "content") else str(resp)

        import json, re

        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            result = json.loads(m.group())
            ids = [r["id"] for r in result.get("recommendations", [])]
            reasons = {r["id"]: r["reason"] for r in result.get("recommendations", [])}

            ranked = []
            for rid in ids:
                for item in candidates:
                    if item.id == rid:
                        ranked.append(item)
                        break
            for item in candidates:
                if item not in ranked:
                    ranked.append(item)
            return ranked[:5], reasons
    except Exception as e:
        print(f"LLM rank error: {e}")

    return candidates[:5], {}


class TravelRecommendationTool(BaseTool):
    name: str = "travel_recommendation"
    description: str = (
        "Recommend trains, flights and hotels based on travel information"
    )
    args_schema: type[BaseModel] = RecommendationInput

    def _mock_recommendations(
        self, departure: str, destination: str, travel_date: date, passengers: int = 1
    ) -> List[RecommendationItem]:
        recommendations = []

        train_data = [
            {
                "id": "G1",
                "type": "train",
                "name": "G1",
                "departure_time": "08:00",
                "arrival_time": "14:30",
                "price": 862.0,
                "duration": "6h 30m",
            },
            {
                "id": "G27",
                "type": "train",
                "name": "G27",
                "departure_time": "09:00",
                "arrival_time": "15:45",
                "price": 862.0,
                "duration": "6h 45m",
            },
            {
                "id": "G3",
                "type": "train",
                "name": "G3",
                "departure_time": "10:00",
                "arrival_time": "16:30",
                "price": 862.0,
                "duration": "6h 30m",
            },
        ]

        flight_data = [
            {
                "id": "CA1321",
                "type": "flight",
                "name": "CA1321",
                "departure_time": "07:30",
                "arrival_time": "10:50",
                "price": 1200.0,
                "duration": "3h 20m",
            },
            {
                "id": "MU1234",
                "type": "flight",
                "name": "MU1234",
                "departure_time": "12:30",
                "arrival_time": "15:50",
                "price": 980.0,
                "duration": "3h 20m",
            },
        ]

        hotel_data = [
            {
                "id": "HOTEL001",
                "type": "hotel",
                "name": "City Center Business Hotel",
                "price": 480.0,
                "details": {"rating": 4.5, "free_breakfast": True, "wifi": True},
            },
            {
                "id": "HOTEL002",
                "type": "hotel",
                "name": "Business Express Hotel",
                "price": 320.0,
                "details": {"rating": 4.2, "free_breakfast": True, "wifi": True},
            },
        ]

        for item in train_data:
            recommendations.append(
                RecommendationItem(
                    id=item["id"],
                    type=item["type"],
                    name=item["name"],
                    departure=departure,
                    destination=destination,
                    date=travel_date.isoformat(),
                    departure_time=item["departure_time"],
                    arrival_time=item["arrival_time"],
                    price=item["price"] * passengers,
                    duration=item["duration"],
                    available=True,
                )
            )

        for item in flight_data:
            recommendations.append(
                RecommendationItem(
                    id=item["id"],
                    type=item["type"],
                    name=item["name"],
                    departure=departure,
                    destination=destination,
                    date=travel_date.isoformat(),
                    departure_time=item["departure_time"],
                    arrival_time=item["arrival_time"],
                    price=item["price"] * passengers,
                    duration=item["duration"],
                    available=True,
                )
            )

        for item in hotel_data:
            recommendations.append(
                RecommendationItem(
                    id=item["id"],
                    type=item["type"],
                    name=item["name"],
                    price=item["price"],
                    details=item["details"],
                    available=True,
                )
            )

        return recommendations

    def _real_recommendations(
        self, departure: str, destination: str, travel_date: date, passengers: int = 1
    ) -> List[RecommendationItem]:
        if not settings.tmc_api_base_url or not settings.tmc_api_key:
            return self._mock_recommendations(
                departure, destination, travel_date, passengers
            )

        try:
            url = f"{settings.tmc_api_base_url}/v1/search"
            headers = {
                "Authorization": f"Bearer {settings.tmc_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "departure": departure,
                "destination": destination,
                "date": travel_date.isoformat(),
                "passengers": passengers,
            }
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return [RecommendationItem(**item) for item in data.get("results", [])]
        except Exception as e:
            print(f"TMC search error: {e}")
            return self._mock_recommendations(
                departure, destination, travel_date, passengers
            )

    def _run(
        self,
        departure: str,
        destination: str,
        travel_date: date,
        passengers: int = 1,
        preferences: str = None,
    ) -> tuple[List[RecommendationItem], Dict]:
        if settings.use_mock or not settings.tmc_api_base_url:
            candidates = self._mock_recommendations(
                departure, destination, travel_date, passengers
            )
        else:
            candidates = self._real_recommendations(
                departure, destination, travel_date, passengers
            )

        if not candidates:
            return [], {}

        if preferences is None:
            preferences = "price-performance ratio, suitable for business travel"

        return rank_with_llm(
            candidates,
            passengers,
            departure,
            destination,
            travel_date.isoformat(),
            preferences,
        )

    async def _arun(
        self,
        departure: str,
        destination: str,
        travel_date: date,
        passengers: int = 1,
        preferences: str = None,
    ) -> tuple[List[RecommendationItem], Dict]:
        return self._run(departure, destination, travel_date, passengers, preferences)
