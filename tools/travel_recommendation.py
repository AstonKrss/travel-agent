from typing import List, Optional
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


class TravelRecommendationTool(BaseTool):
    name: str = "travel_recommendation"
    description: str = (
        "Recommend trains, flights and hotels based on travel information"
    )
    args_schema: type[BaseModel] = RecommendationInput

    def _mock_recommendations(
        self, departure: str, destination: str, travel_date: date, passengers: int = 1
    ) -> List[RecommendationItem]:
        """Mock implementation to generate travel recommendations when no TMC API configured"""

        recommendations = []

        # High-speed train recommendations
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

        # Flight recommendations
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

        # Hotel recommendations
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

        # Add all to recommendations
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
        """Real implementation querying TMC API for actual availability and prices"""
        if not settings.tmc_api_base_url or not settings.tmc_api_key:
            # Fall back to mock if not configured
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

            recommendations = []
            for item in data.get("results", []):
                recommendations.append(RecommendationItem(**item))

            return recommendations
        except Exception as e:
            print(f"TMC search error: {e}")
            # Fall back to mock on error
            return self._mock_recommendations(
                departure, destination, travel_date, passengers
            )

    def _run(
        self, departure: str, destination: str, travel_date: date, passengers: int = 1
    ) -> List[RecommendationItem]:
        """Main entry point - uses mock if not configured, else real API"""
        if settings.use_mock or not settings.tmc_api_base_url:
            return self._mock_recommendations(
                departure, destination, travel_date, passengers
            )
        else:
            return self._real_recommendations(
                departure, destination, travel_date, passengers
            )

    async def _arun(
        self, departure: str, destination: str, travel_date: date, passengers: int = 1
    ) -> List[RecommendationItem]:
        return self._run(departure, destination, travel_date, passengers)
