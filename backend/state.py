# Re-export from schemas for backward compatibility
from backend.schemas.state import (
    TravelState,
    TripInfo,
    OrderInfo,
    IntentType,
)
from backend.schemas.recommendation import RecommendationItem

__all__ = [
    "TravelState",
    "TripInfo",
    "OrderInfo",
    "IntentType",
    "RecommendationItem",
]
