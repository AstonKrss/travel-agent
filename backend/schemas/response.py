# backend/schemas/response.py
"""Response models for API"""

from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """Chat response model (non-streaming)"""

    message: str = Field(..., description="Assistant response message")
    thread_id: str = Field(..., description="Conversation thread ID")
    recommendations: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Recommendations if any"
    )
    trip_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Extracted trip information"
    )


class OrderResponse(BaseModel):
    """Order response model"""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    order_id: Optional[str] = Field(default=None, description="Order ID if booked")
    amount: Optional[float] = Field(default=None, description="Order amount")

    model_config = {"extra": "allow"}
