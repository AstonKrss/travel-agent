# backend/schemas/recommendation.py
"""Recommendation models"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel


class RecommendationCategory(str, Enum):
    """Recommendation category types"""

    TRAIN = "train"
    FLIGHT = "flight"
    HOTEL = "hotel"


class RecommendationItem(BaseModel):
    """Single recommendation item"""

    id: str
    type: str  # train/flight/hotel
    name: str
    departure: Optional[str] = None
    destination: Optional[str] = None
    date: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    price: float
    duration: Optional[str] = None
    available: bool = True
    details: Optional[Dict[str, Any]] = None

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "departure": self.departure,
            "destination": self.destination,
            "date": self.date,
            "departure_time": self.departure_time,
            "arrival_time": self.arrival_time,
            "price": self.price,
            "duration": self.duration,
            "available": self.available,
            "details": self.details,
        }


class RecommendationSet(BaseModel):
    """Collection of recommendations"""

    trains: list[RecommendationItem] = []
    flights: list[RecommendationItem] = []
    hotels: list[RecommendationItem] = []

    def to_list(self) -> list:
        """Convert to flat list"""
        return self.trains + self.flights + self.hotels

    def is_empty(self) -> bool:
        """Check if empty"""
        return not (self.trains or self.flights or self.hotels)
