# backend/nodes/intent_node.py
"""Intent classification node"""

import json
import re
from typing import Dict, Any

from backend.schemas.state import TravelState, IntentType


SYSTEM_PROMPT = """你是一个企业差旅智能助手，专门帮助员工安排出差行程。

你的职责：
1. 友好地与用户对话，询问差旅需求
2. 引导用户提供：出发城市、目的地、出行日期、人数等信息
3. 根据用户需求推荐合适的火车、航班和酒店
4. 协助完成预订流程
5. **如果用户问关于目的地的一般信息（如城市介绍、天气、景点等），你应该先回答这个问题，然后再继续收集差旅信息**

回复要求：
- 使用中文回复
- 语气友好、专业、简洁
- 主动引导用户说明目的地和日期
- 如果用户问你是谁，告诉用户你是企业差旅智能助手
- 每次回复要简洁，不要重复之前已经说过的内容
- 如果已知用户的需求，不要再重复询问已知信息
- **如果用户的问题与差旅安排无关，先回答用户的问题，然后再温柔地引导回差旅话题**"""


def _classify_intent(user_input: str) -> IntentType:
    """Simple rule-based + pattern matching intent classification"""
    text_lower = user_input.lower().strip()

    # Greeting keywords
    greeting_keywords = [
        "你好",
        "hi",
        "hello",
        "您好",
        "嗨",
        "hey",
        "早上好",
        "下午好",
        "晚上好",
    ]
    for kw in greeting_keywords:
        if text_lower == kw or text_lower.startswith(kw):
            return IntentType.GREETING

    # Booking keywords
    book_keywords = [
        "预订",
        "订",
        "book",
        "预定",
        "买票",
        "订票",
        "订房",
        "住宿",
        "酒店",
        "机票",
        "火车票",
    ]
    for kw in book_keywords:
        if kw in text_lower:
            return IntentType.BOOK

    # Cancel keywords
    cancel_keywords = ["取消", "退票", "退订", "cancel", "退款"]
    for kw in cancel_keywords:
        if kw in text_lower:
            return IntentType.CANCEL

    # Expense keywords
    expense_keywords = ["报销", "费用", "发票", "claim"]
    for kw in expense_keywords:
        if kw in text_lower:
            return IntentType.EXPENSE

    # Trip query pattern: from X to Y
    trip_pattern = re.search(
        r"从\s*[一-\u9fa5a-za-z]+(?:\s|,|，)?到\s*[一-\u9fa5a-za-z]+", user_input
    )
    if trip_pattern:
        return IntentType.TRIP_QUERY

    return IntentType.UNKNOWN


def intent_node(state: TravelState) -> Dict[str, Any]:
    """Classify user intent"""
    user_input = state.last_message or ""

    # Use rule-based classification
    intent = _classify_intent(user_input)

    # If uncertain, use LLM
    if intent == IntentType.UNKNOWN:
        intent = _classify_intent_llm(user_input)

    return {
        "intent": intent,
    }


def _classify_intent_llm(user_input: str) -> IntentType:
    """Use LLM for intent classification"""
    try:
        from backend.llm import get_llm
        from langchain_core.messages import HumanMessage

        llm = get_llm(timeout=10)
        if not llm:
            return IntentType.UNKNOWN

        prompt = f"""分析用户输入，判断意图类型。

用户输入: {user_input}

可能的意图类型：
- trip_query: 差旅查询（需要知道出发地、目的地、日期）
- book: 预订
- cancel: 取消
- expense: 报销
- greeting: 问候
- chat: 闲聊或一般问题

返回JSON格式: {{"intent": "意图类型", "confidence": 0.0-1.0}}"""

        resp = llm.invoke([HumanMessage(content=prompt)])
        content = resp.content if hasattr(resp, "content") else str(resp)

        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            data = json.loads(m.group())
            intent_str = data.get("intent", "unknown")
            confidence = float(data.get("confidence", 0.5))
            if confidence > 0.6:
                return IntentType(intent_str)
    except Exception as e:
        print(f"Intent LLM error: {e}")

    return IntentType.UNKNOWN
