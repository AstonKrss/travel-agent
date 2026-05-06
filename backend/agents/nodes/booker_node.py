"""Booker Node - Execute travel booking via TMC (mock for now)"""

import uuid
from typing import Dict

from backend.schemas.state import TravelState, OrderRecord, BookingStatus


def booker_node(state: TravelState) -> Dict:
    """Execute booking through TMC. Currently uses mock data since TMC API is not integrated."""
    if not state.recommendations:
        return {
            "current_step": "booking_failed",
            "messages": [
                {"role": "assistant", "content": "没有可预订的方案。请先获取推荐。"}
            ],
        }

    best = state.recommendations[0]
    if not best:
        return {
            "current_step": "booking_failed",
            "messages": [{"role": "assistant", "content": "未找到合适的预订方案。"}],
        }

    result = _mock_booking(state, best)

    item_type = best.get("type", "")
    name = best.get("name", "?")

    order = OrderRecord(
        order_id=result["order_id"],
        status="booked",
        ticket_booked=item_type in ("train", "flight"),
        hotel_booked=item_type == "hotel",
        total_amount=result["amount"],
        booking_ref=result.get("booking_ref"),
    )
    return {
        "order": order,
        "current_step": "booked",
        "booking_status": BookingStatus.BOOKED,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"✅ 预订成功！\n\n"
                    f"订单号：{result['order_id']}\n"
                    f"方案：{name}\n"
                    f"金额：¥{result['amount']:.2f}\n"
                    f"状态：已确认（企业账户直接扣款，无需垫付）"
                ),
            }
        ],
    }


def _mock_booking(state: TravelState, item) -> Dict:
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    price = item.get("price", 0) if isinstance(item, dict) else item.price
    amount = price * state.trip.passengers
    return {
        "order_id": order_id,
        "amount": amount,
        "booking_ref": f"REF-{uuid.uuid4().hex[:6].upper()}",
        "success": True,
    }
