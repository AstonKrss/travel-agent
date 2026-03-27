from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import date


class TripInfo(BaseModel):
    departure: Optional[str] = None
    destination: Optional[str] = None
    date: Optional[date] = None
    return_date: Optional[date] = None
    passengers: int = 1
    trip_type: str = "one_way"
    preferences: Optional[Dict[str, Any]] = None
    user_input: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}


class RecommendationItem(BaseModel):
    id: str
    type: str
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


class OrderInfo(BaseModel):
    order_id: Optional[str] = None
    status: str = "pending"
    ticket_booked: bool = False
    hotel_booked: bool = False
    total_amount: float = 0.0

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}


class TravelState(BaseModel):
    user_id: str
    thread_id: str
    messages: List[Dict[str, str]] = Field(default_factory=list)
    trip: TripInfo = Field(default_factory=TripInfo)
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    order: OrderInfo = Field(default_factory=OrderInfo)
    current_step: str = "initial"
    extracted: bool = False
    need_recommendation: bool = False
    last_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"
