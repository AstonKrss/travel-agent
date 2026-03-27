from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, field_serializer, field_validator
from datetime import date, datetime


class IntentType(str, Enum):
    TRIP_QUERY = "trip_query"
    BOOK = "book"
    CANCEL = "cancel"
    CHANGE = "change"
    EXPENSE = "expense"
    CHAT = "chat"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class TripInfo(BaseModel):
    departure: Optional[str] = None
    destination: Optional[str] = None
    date: Union[date, datetime, None] = None
    return_date: Union[date, datetime, None] = None
    passengers: int = 1
    trip_type: str = "one_way"
    preferences: Optional[Dict[str, Any]] = None
    user_input: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    @field_serializer("date")
    def serialize_date(self, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.date().isoformat()
        if isinstance(v, date):
            return v.isoformat()
        return str(v)

    @field_serializer("return_date")
    def serialize_return_date(self, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.date().isoformat()
        if isinstance(v, date):
            return v.isoformat()
        return str(v)

    @field_validator("date", "return_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if v is None:
            return None
        if isinstance(v, (date, datetime)):
            return v
        if isinstance(v, str):
            try:
                for fmt in ["%Y-%m-%d", "%Y/%m/%d"]:
                    return datetime.strptime(v, fmt).date()
            except:
                pass
        return v


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
    intent: Optional[IntentType] = None
    streaming_progress: str = ""

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"
