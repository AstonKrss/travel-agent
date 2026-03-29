# backend/schemas/events.py
"""SSE Event types for streaming responses"""

from enum import Enum
from typing import Any, Dict, Optional, List
import json


class SSEEventType(str, Enum):
    """SSE event types"""

    START = "start"
    STATUS = "status"
    MESSAGE = "message"
    CLEAR = "clear"
    RECOMMENDATION_CATEGORY = "recommendation_category"
    RECOMMENDATION = "recommendation"
    RECOMMENDATIONS_DONE = "recommendations_done"
    DONE = "done"
    ERROR = "error"


class SSEEvent:
    """SSE event builder"""

    @staticmethod
    def start(thread_id: str, message: str = "正在连接...") -> str:
        return json.dumps(
            {
                "type": SSEEventType.START.value,
                "thread_id": thread_id,
                "message": message,
            }
        )

    @staticmethod
    def status(message: str) -> str:
        return json.dumps({"type": SSEEventType.STATUS.value, "message": message})

    @staticmethod
    def message(content: str) -> str:
        return json.dumps({"type": SSEEventType.MESSAGE.value, "content": content})

    @staticmethod
    def clear() -> str:
        return json.dumps({"type": SSEEventType.CLEAR.value})

    @staticmethod
    def recommendation_category(category: str, title: str) -> str:
        return json.dumps(
            {
                "type": SSEEventType.RECOMMENDATION_CATEGORY.value,
                "category": category,
                "title": title,
            }
        )

    @staticmethod
    def recommendation(data: Dict[str, Any]) -> str:
        return json.dumps({"type": SSEEventType.RECOMMENDATION.value, "data": data})

    @staticmethod
    def recommendations_done() -> str:
        return json.dumps({"type": SSEEventType.RECOMMENDATIONS_DONE.value})

    @staticmethod
    def done(step: str = "initial") -> str:
        return json.dumps({"type": SSEEventType.DONE.value, "step": step})

    @staticmethod
    def error(message: str) -> str:
        return json.dumps({"type": SSEEventType.ERROR.value, "message": message})


# Processing status messages for better UX
class ProcessingStatus:
    """User-friendly processing status messages"""

    UNDERSTANDING = "🤔 正在理解您的需求..."
    EXTRACTING = "🔍 正在提取出行信息（出发地、目的地、日期）..."
    PARSING_DATE = "🧠 正在用 AI 解析日期..."
    SEARCHING_TRAIN = "🚄 正在搜索高铁/动车..."
    SEARCHING_FLIGHT = "✈️ 正在搜索航班..."
    SEARCHING_HOTEL = "🏨 正在搜索酒店..."
    AI_RECOMMENDING = "🧠 正在用 AI 智能推荐（根据性价比）..."
    GENERATING_REASONS = "✨ 正在生成推荐理由..."
    CONNECTING = "🔗 正在连接..."


__all__ = [
    "SSEEventType",
    "SSEEvent",
    "ProcessingStatus",
]
