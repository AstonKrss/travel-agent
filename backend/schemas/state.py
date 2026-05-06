"""Enhanced state model with LangGraph reducers for proper state merging"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_serializer, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class IntentType(str, Enum):
    GREETING = "greeting"
    CHAT = "chat"
    TRIP_QUERY = "trip_query"
    BOOK = "book"
    APPROVE = "approve"
    CANCEL = "cancel"
    EXPENSE = "expense"
    UNKNOWN = "unknown"


class BookingStatus(str, Enum):
    PENDING = "pending"
    POLICY_CHECKED = "policy_checked"
    PLANNED = "planned"
    RECOMMENDED = "recommended"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    BOOKED = "booked"
    FINANCE_SYNCED = "finance_synced"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


class TripInfo(BaseModel):
    departure: Optional[str] = None
    destination: Optional[str] = None
    date: Union[date, datetime, str, None] = None
    return_date: Union[date, datetime, str, None] = None
    passengers: int = 1
    trip_type: str = "one_way"
    preferences: Optional[Dict[str, Any]] = None
    budget: Optional[float] = None

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    @field_serializer("date", "return_date")
    def serialize_dates(self, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, date):
            return v.isoformat()
        return str(v)

    @field_validator("date", "return_date", mode="before")
    @classmethod
    def parse_dates(cls, v):
        if v is None or isinstance(v, (date, datetime)):
            return v
        if isinstance(v, str):
            for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
                try:
                    return datetime.strptime(v, fmt).date()
                except ValueError:
                    pass
        return v

    @property
    def is_complete(self) -> bool:
        return bool(self.departure and self.destination and self.date)

    @property
    def missing_fields(self) -> List[str]:
        m = []
        if not self.departure:
            m.append("departure")
        if not self.destination:
            m.append("destination")
        if not self.date:
            m.append("date")
        return m


class RecommendationItem(BaseModel):
    id: str
    type: str  # train | flight | hotel
    name: str
    departure: Optional[str] = None
    destination: Optional[str] = None
    date: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    price: float = 0.0
    duration: Optional[str] = None
    available: bool = True
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}


class OrderRecord(BaseModel):
    order_id: Optional[str] = None
    status: str = "pending"
    ticket_booked: bool = False
    hotel_booked: bool = False
    total_amount: float = 0.0
    booking_ref: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}


class PolicyViolation(BaseModel):
    rule: str
    message: str
    severity: str = "warning"  # warning | error
    suggestion: Optional[str] = None


# ---------------------------------------------------------------------------
# Reducer helpers for LangGraph
# ---------------------------------------------------------------------------


def add_messages(left: list, right: list) -> list:
    """Append new messages, replacing the last assistant message if the new one is from assistant."""
    if not right:
        return left
    if not left:
        return right
    # If both last and new are assistant, replace
    if left[-1].get("role") == "assistant" and right[-1].get("role") == "assistant":
        return left[:-1] + right
    return left + right


def get_trip_field(trip, field: str, default=None):
    """Safely read a field from trip regardless of whether it is a dict or a Pydantic model."""
    if isinstance(trip, dict):
        return trip.get(field, default)
    return getattr(trip, field, default)


# ---------------------------------------------------------------------------
# Main State
# ---------------------------------------------------------------------------


class TravelState(BaseModel):
    """Main LangGraph state for the travel agent."""

    # Core
    user_id: str = "default"
    thread_id: str = "default"

    # Conversation - uses reducer for proper merging
    messages: Annotated[List[Dict[str, str]], add_messages] = Field(
        default_factory=list
    )

    # Trip info - replaced entirely on update
    trip: TripInfo = Field(default_factory=TripInfo)

    # Recommendations (plain dicts from recommend_node)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    raw_candidates: List[Dict[str, Any]] = Field(default_factory=list)

    # Order
    order: OrderRecord = Field(default_factory=OrderRecord)

    # Flow control
    current_step: str = "initial"
    intent: Optional[str] = None
    booking_status: BookingStatus = BookingStatus.PENDING

    # Policy
    policy_violations: List[PolicyViolation] = Field(default_factory=list)
    policy_approved: bool = False

    # Approval
    requires_approval: bool = False
    approval_reason: Optional[str] = None

    # Metadata
    last_message: Optional[str] = None
    node_timings: Dict[str, float] = Field(default_factory=dict)
    total_tokens: int = 0
    errors: List[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
