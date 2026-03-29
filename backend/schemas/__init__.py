# backend/schemas/__init__.py

from backend.schemas.state import TravelState, TripInfo, OrderInfo, IntentType
from backend.schemas.recommendation import RecommendationItem, RecommendationCategory
from backend.schemas.request import ChatRequest
from backend.schemas.response import ChatResponse

__all__ = [
    "TravelState",
    "TripInfo",
    "OrderInfo",
    "IntentType",
    "RecommendationItem",
    "RecommendationCategory",
    "ChatRequest",
    "ChatResponse",
]
