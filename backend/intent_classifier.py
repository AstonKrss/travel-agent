from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import re

from backend.config import settings


class IntentType(str, Enum):
    TRIP_QUERY = "trip_query"  # 查询差旅行程（出发地、目的地、日期）
    BOOK = "book"  # 预订
    CANCEL = "cancel"  # 取消订单
    CHANGE = "change"  # 改签
    EXPENSE = "expense"  # 报销
    CHAT = "chat"  # 闲聊/一般问题
    GREETING = "greeting"  # 问候
    UNKNOWN = "unknown"  # 未知


class IntentResult(BaseModel):
    intent: IntentType
    confidence: float = 1.0
    extracted_keyword: Optional[str] = None
    reason: Optional[str] = None


class IntentClassifierTool(BaseTool):
    name: str = "intent_classifier"
    description: str = "Classify user intent from natural language input"

    def _classify_by_rules(self, text: str) -> Optional[IntentResult]:
        text_lower = text.lower().strip()

        # 预订关键词
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
                return IntentResult(
                    intent=IntentType.BOOK,
                    confidence=0.9,
                    extracted_keyword=kw,
                    reason=f"检测到预订关键词: {kw}",
                )

        # 取消关键词
        cancel_keywords = ["取消", "退票", "退订", "cancel", "退款"]
        for kw in cancel_keywords:
            if kw in text_lower:
                return IntentResult(
                    intent=IntentType.CANCEL,
                    confidence=0.9,
                    extracted_keyword=kw,
                    reason=f"检测到取消关键词: {kw}",
                )

        # 改签关键词
        change_keywords = ["改签", "改期", "更改", "change", "修改"]
        for kw in change_keywords:
            if kw in text_lower:
                return IntentResult(
                    intent=IntentType.CHANGE,
                    confidence=0.9,
                    extracted_keyword=kw,
                    reason=f"检测到改签关键词: {kw}",
                )

        # 报销关键词
        expense_keywords = ["报销", "报销", "报销", "费用", "报销", "发票", "claim"]
        for kw in expense_keywords:
            if kw in text_lower:
                return IntentResult(
                    intent=IntentType.EXPENSE,
                    confidence=0.9,
                    extracted_keyword=kw,
                    reason=f"检测到报销关键词: {kw}",
                )

        # 问候关键词
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
                return IntentResult(
                    intent=IntentType.GREETING, confidence=0.95, reason=f"检测到问候语"
                )

        # 差旅查询模式：从X到Y
        trip_pattern = re.search(
            r"从\s*[一-\u9fa5a-za-z]+(?:\s|,|，)?到\s*[一-\u9fa5a-za-z]+", text
        )
        if trip_pattern:
            return IntentResult(
                intent=IntentType.TRIP_QUERY,
                confidence=0.85,
                reason="检测到差旅路线模式",
            )

        # 单独的目的地
        simple_dest = re.match(r"^[一-\u9fa5a-z]+(?:到|去)?$", text.strip())
        if simple_dest:
            return IntentResult(
                intent=IntentType.TRIP_QUERY, confidence=0.7, reason="可能是目的地"
            )

        return None

    def _classify_by_llm(self, text: str) -> IntentResult:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage

            if settings.llm_provider == "volcano":
                llm = ChatOpenAI(
                    api_key=settings.volcano_api_key,
                    base_url=settings.volcano_base_url,
                    model=settings.volcano_model,
                    temperature=0.1,
                    timeout=10,
                )
            elif settings.llm_provider == "openai":
                llm = ChatOpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                    model=settings.openai_model,
                    temperature=0.1,
                    timeout=10,
                )
            else:
                return IntentResult(intent=IntentType.UNKNOWN, confidence=0.0)

            prompt = f"""请分析以下用户输入，判断其意图。

用户输入: {text}

可能的意图类型:
- trip_query: 用户在查询差旅行程（需要知道出发地、目的地、日期）
- book: 用户想要预订（机票、火车票、酒店）
- cancel: 用户想要取消订单
- change: 用户想要改签或更改订单
- expense: 用户想要报销
- chat: 用户在闲聊或问一般性问题（如城市介绍、天气等）
- greeting: 用户在问候

请直接返回以下JSON格式，不需要其他内容:
{{"intent": "意图类型", "confidence": 0.0-1.0, "reason": "简短理由"}}

只返回JSON，不要其他内容。"""

            resp = llm.invoke([HumanMessage(content=prompt)])
            content = resp.content if hasattr(resp, "content") else str(resp)

            import json, re

            m = re.search(r"\{[\s\S]*\}", content)
            if m:
                data = json.loads(m.group())
                return IntentResult(
                    intent=IntentType(data.get("intent", "unknown")),
                    confidence=float(data.get("confidence", 0.5)),
                    reason=data.get("reason", ""),
                )
        except Exception as e:
            print(f"Intent LLM error: {e}")

        return IntentResult(intent=IntentType.UNKNOWN, confidence=0.0)

    def _run(self, user_input: str) -> IntentResult:
        # 先尝试规则匹配
        rule_result = self._classify_by_rules(user_input)
        if rule_result and rule_result.confidence >= 0.85:
            return rule_result

        # 低置信度时用 LLM
        if rule_result and rule_result.confidence < 0.85:
            llm_result = self._classify_by_llm(user_input)
            if llm_result.confidence > rule_result.confidence:
                return llm_result
            return rule_result

        # 没有规则匹配，直接用 LLM
        return self._classify_by_llm(user_input)

    async def _arun(self, user_input: str) -> IntentResult:
        return self._run(user_input)


def classify_intent(user_input: str) -> IntentResult:
    """快速意图分类函数"""
    tool = IntentClassifierTool()
    return tool._run(user_input)
