# backend/schemas/request.py
"""Request models for API"""

from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request model"""

    message: str = Field(..., description="User message")
    user_id: str = Field(default="default_user", description="User ID")
    thread_id: Optional[str] = Field(default=None, description="Conversation thread ID")

    model_config = {"extra": "allow"}


class OrderRequest(BaseModel):
    """Order booking request model"""

    action: str = Field(default="book", description="Action: book/cancel")
    type: str = Field(..., description="Item type: train/flight/hotel")
    user_id: str
    thread_id: Optional[str] = None

    # Train specific
    train_no: Optional[str] = None
    # Flight specific
    flight_no: Optional[str] = None
    # Hotel specific
    hotel_id: Optional[str] = None

    # Common
    departure: Optional[str] = None
    destination: Optional[str] = None
    date: Optional[str] = None

    model_config = {"extra": "allow"}
