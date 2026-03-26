from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import requests

from backend.config import settings


class OAUpdateInput(BaseModel):
    order_id: str = Field(description="Order ID to update")
    user_id: str = Field(description="User ID associated with the order")
    status: str = Field(description="New order status")
    amount: float = Field(description="Total amount of the order")


class OAUpdateResult(BaseModel):
    success: bool
    message: str
    expense_id: Optional[str] = None


class OAFinanceTool(BaseTool):
    name: str = "oa_finance_update"
    description: str = (
        "Update OA/finance system with order status and expense information"
    )
    args_schema: type[BaseModel] = OAUpdateInput

    def _mock_update(
        self, order_id: str, user_id: str, status: str, amount: float
    ) -> OAUpdateResult:
        """Mock implementation when no OA API is configured"""
        expense_id = (
            f"EXP-{order_id[4:]}" if order_id.startswith("ORD-") else f"EXP-{order_id}"
        )

        return OAUpdateResult(
            success=True,
            message=f"Order {order_id} has been updated in OA/finance system. Status: {status}. Amount: ¥{amount:.2f}",
            expense_id=expense_id,
        )

    def _real_update(
        self, order_id: str, user_id: str, status: str, amount: float
    ) -> OAUpdateResult:
        """Real implementation calling external OA/Finance API"""
        if not settings.oa_api_base_url or not settings.oa_api_key:
            return OAUpdateResult(
                success=False,
                message="OA API not configured. Please set OA_API_BASE_URL and OA_API_KEY in .env",
                expense_id=None,
            )

        try:
            url = f"{settings.oa_api_base_url}/v1/expense/create"
            headers = {
                "Authorization": f"Bearer {settings.oa_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "order_id": order_id,
                "user_id": user_id,
                "status": status,
                "amount": amount,
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            return OAUpdateResult(
                success=data.get("success", False),
                message=data.get("message", "OA update processed"),
                expense_id=data.get("expense_id"),
            )
        except Exception as e:
            return OAUpdateResult(
                success=False, message=f"OA API error: {str(e)}", expense_id=None
            )

    def _run(
        self, order_id: str, user_id: str, status: str, amount: float
    ) -> OAUpdateResult:
        """Main entry point - uses mock if not configured, else real API"""
        if settings.use_mock or not settings.oa_api_base_url:
            return self._mock_update(order_id, user_id, status, amount)
        else:
            return self._real_update(order_id, user_id, status, amount)

    async def _arun(
        self, order_id: str, user_id: str, status: str, amount: float
    ) -> OAUpdateResult:
        return self._run(order_id, user_id, status, amount)
