from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import uuid
import requests

from backend.config import settings


class TMCBookInput(BaseModel):
    user_id: str = Field(description="User ID making the booking")
    item_type: str = Field(description="Type of item to book (train, flight, hotel)")
    item_id: str = Field(description="ID of the item to book")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional booking details"
    )


class TMCBookingResult(BaseModel):
    success: bool
    order_id: Optional[str] = None
    message: str
    amount_charged: float = 0.0


class TMCApiTool(BaseTool):
    name: str = "tmc_api"
    description: str = (
        "TMC API for querying availability and making company-paid bookings"
    )
    args_schema: type[BaseModel] = TMCBookInput

    def _mock_booking(
        self, user_id: str, item_type: str, item_id: str
    ) -> TMCBookingResult:
        """Mock implementation when no TMC API is configured"""
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # Calculate mock amount based on type
        price_map = {"train": 862.0, "flight": 1200.0, "hotel": 480.0}
        amount = price_map.get(item_type, 500.0)

        return TMCBookingResult(
            success=True,
            order_id=order_id,
            message=f"Booking confirmed successfully. Company account has been charged ¥{amount:.2f}. No employee payment needed.",
            amount_charged=amount,
        )

    def _real_booking(
        self, user_id: str, item_type: str, item_id: str, details: Dict[str, Any]
    ) -> TMCBookingResult:
        """Real implementation calling external TMC API"""
        if not settings.tmc_api_base_url or not settings.tmc_api_key:
            return TMCBookingResult(
                success=False,
                message="TMC API not configured. Please set TMC_API_BASE_URL and TMC_API_KEY in .env",
                amount_charged=0.0,
            )

        try:
            url = f"{settings.tmc_api_base_url}/v1/book"
            headers = {
                "Authorization": f"Bearer {settings.tmc_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "user_id": user_id,
                "item_type": item_type,
                "item_id": item_id,
                "company_account_id": settings.tmc_company_account_id,
                "details": details,
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            return TMCBookingResult(
                success=data.get("success", False),
                order_id=data.get("order_id"),
                message=data.get("message", "Booking processed"),
                amount_charged=data.get("amount_charged", 0.0),
            )
        except Exception as e:
            return TMCBookingResult(
                success=False, message=f"TMC API error: {str(e)}", amount_charged=0.0
            )

    def _run(
        self, user_id: str, item_type: str, item_id: str, details: Dict[str, Any] = None
    ) -> TMCBookingResult:
        """Main entry point - uses mock if not configured, else real API"""
        if details is None:
            details = {}

        if settings.use_mock or not settings.tmc_api_base_url:
            return self._mock_booking(user_id, item_type, item_id)
        else:
            return self._real_booking(user_id, item_type, item_id, details)

    async def _arun(
        self, user_id: str, item_type: str, item_id: str, details: Dict[str, Any] = None
    ) -> TMCBookingResult:
        if details is None:
            details = {}
        return self._run(user_id, item_type, item_id, details)
