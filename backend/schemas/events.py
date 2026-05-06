"""SSE Events for streaming"""

import json
from enum import Enum
from typing import Any, Dict


class SSEEventType(str, Enum):
    START = "start"
    NODE = "node"
    MESSAGE = "message"
    CLEAR = "clear"
    RECOMMENDATION_CATEGORY = "recommendation_category"
    RECOMMENDATION = "recommendation"
    RECOMMENDATIONS_DONE = "recommendations_done"
    APPROVAL_REQUEST = "approval_request"
    DONE = "done"
    ERROR = "error"


class SSEEvent:
    @staticmethod
    def start(thread_id: str) -> str:
        return json.dumps({"type": SSEEventType.START.value, "thread_id": thread_id})

    @staticmethod
    def node(name: str, status: str = "running") -> str:
        return json.dumps(
            {"type": SSEEventType.NODE.value, "node": name, "status": status}
        )

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
    def approval_request(reason: str) -> str:
        return json.dumps(
            {
                "type": SSEEventType.APPROVAL_REQUEST.value,
                "reason": reason,
                "actions": ["approve", "reject"],
            }
        )

    @staticmethod
    def done(step: str = "complete") -> str:
        return json.dumps({"type": SSEEventType.DONE.value, "step": step})

    @staticmethod
    def error(message: str) -> str:
        return json.dumps({"type": SSEEventType.ERROR.value, "message": message})


class ProcessingStatus:
    UNDERSTANDING = "正在理解您的需求..."
    EXTRACTING = "正在提取出行信息..."
    CHECKING_POLICY = "正在检查差旅政策..."
    PLANNING = "正在规划行程..."
    RECOMMENDING = "正在智能推荐..."
    WAITING_APPROVAL = "等待审批..."
    BOOKING = "正在预订..."
    CONNECTING = "正在连接..."
