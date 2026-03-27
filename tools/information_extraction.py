from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from datetime import datetime, date, timedelta
import re

from backend.config import settings


class IEInput(BaseModel):
    user_input: str = Field(description="User's natural language input text")


class ExtractedInfo(BaseModel):
    departure: Optional[str] = None
    destination: Optional[str] = None
    date: Optional[date] = None
    passengers: int = 1
    preferences: dict = Field(default_factory=dict)
    has_trip_request: bool = False
    raw_date_text: Optional[str] = None  # 原始日期文本，用于 LLM 处理


def get_llm():
    """获取 LLM 用于日期解析"""
    try:
        from langchain_openai import ChatOpenAI

        if settings.llm_provider == "volcano":
            return ChatOpenAI(
                api_key=settings.volcano_api_key,
                base_url=settings.volcano_base_url,
                model=settings.volcano_model,
                temperature=0.1,
                timeout=10,
            )
        elif settings.llm_provider == "openai":
            return ChatOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_model,
                temperature=0.1,
                timeout=10,
            )
    except:
        return None


def parse_date_with_llm(date_text: str) -> Optional[date]:
    """用 LLM 解析复杂日期文本"""
    llm = get_llm()
    if not llm:
        return None

    from langchain_core.messages import HumanMessage

    prompt = f"""请根据今天的日期 {datetime.now().date()}，解析以下日期文本并返回标准日期。

日期文本: {date_text}

请返回格式如 "2026-03-30" 的日期，只需要返回日期，不需要其他内容。如果无法解析，返回 "NONE"。"""

    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        content = resp.content if hasattr(resp, "content") else str(resp)

        # 尝试解析日期
        date_str = content.strip()
        if date_str and date_str != "NONE":
            # 尝试各种格式
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"]:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except:
                    pass

            # 尝试直接解析
            import re

            match = re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", date_str)
            if match:
                return datetime.strptime(
                    match.group().replace("/", "-"), "%Y-%m-%d"
                ).date()
    except Exception as e:
        print(f"LLM date parse error: {e}")

    return None


class InformationExtractionTool(BaseTool):
    name: str = "information_extraction"
    description: str = "Extract travel information from user natural language input"
    args_schema: type[BaseModel] = IEInput

    def _run(self, user_input: str) -> ExtractedInfo:
        """Mock implementation to extract travel information"""
        result = ExtractedInfo()

        patterns = {
            "from": r"(从|from|出发[：,]?)\s*([一-\u9fa5A-Za-z]+)",
            "to": r"(到|to|目的地[：,]?)\s*([一-\u9fa5A-Za-z]+)",
            "date": r"(本|下)?周?[一二三四五六日天]|本?(?:周|星期)[一二三四五六日天]|明天|后天|\d{4}[-/]\d{1,2}[-/]\d{1,2}",
            "people": r"(\d+)\s*(人|位|个人)",
        }

        # Extract departure - first try "从X到Y" pattern
        from_match = re.search(
            r"从\s*([一-\u9fa5A-Za-z]+?)\s*到\s*([一-\u9fa5A-Za-z]+)", user_input
        )
        if from_match:
            result.departure = from_match.group(1).strip()
            result.destination = from_match.group(2).strip()
        else:
            # Check for pattern like "北京到广州" or "北京,到,广州" or "北京到广州，下周二"
            simple_match = re.match(
                r"^([一-\u9fa5A-Za-z]+?)\s*[,，]?\s*(到|to)\s*[,，]?\s*([一-\u9fa5A-Za-z]+?)(?:下周一|下周二|下周三|下周四|下周五|下周六|下周日|\d{4}[-/]\d{1,2}[-/]\d{1,2})?$",
                user_input,
            )
            if simple_match:
                result.departure = simple_match.group(1).strip()
                result.destination = simple_match.group(3).strip()

        # Extract destination if not found above
        if not result.destination:
            to_match = re.search(patterns["to"], user_input, re.IGNORECASE)
            if to_match:
                result.destination = to_match.group(2).strip()

        # 如果目的地包含日期（如"北京下周二"），需要分离
        if result.destination:
            date_in_dest = re.search(
                r"(.+?)(下周一|下周二|下周三|下周四|下周五|下周六|下周日)$",
                result.destination,
            )
            if date_in_dest:
                result.destination = date_in_dest.group(1).strip()

        # Extract date
        date_match = re.search(patterns["date"], user_input, re.IGNORECASE)
        if date_match:
            date_str = date_match.group(0)

            # Map day names to weekday numbers (Monday=0, Sunday=6)
            day_map = {
                "周一": 0,
                "星期一": 0,
                "周1": 0,
                "周二": 1,
                "星期二": 1,
                "周2": 1,
                "周三": 2,
                "星期三": 2,
                "周3": 2,
                "周四": 3,
                "星期四": 3,
                "周4": 3,
                "周五": 4,
                "星期五": 4,
                "周5": 4,
                "周六": 5,
                "星期六": 5,
                "周6": 5,
                "周日": 6,
                "星期天": 6,
                "周0": 6,
                "周7": 6,
            }

            # Determine if it's "this week" or "next week"
            is_next_week = "下" in date_str or "下周" in date_str

            # Find the day
            weekday = None
            for k, v in day_map.items():
                if k in date_str:
                    weekday = v
                    break

            if weekday is not None:
                today = datetime.now().date()
                days_ahead = weekday - today.weekday()

                if is_next_week:
                    # Next week: add 7 days if already passed or today
                    if days_ahead <= 0:
                        days_ahead += 7
                else:
                    # This week: if already passed, go to next week
                    if days_ahead <= 0:
                        days_ahead += 7

                result.date = today + timedelta(days=days_ahead)
                result.raw_date_text = date_str
            elif re.match(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", date_str):
                result.date = datetime.strptime(
                    date_str.replace("/", "-"), "%Y-%m-%d"
                ).date()
                result.raw_date_text = date_str
            elif "明天" in date_str:
                result.date = (datetime.now() + timedelta(days=1)).date()
                result.raw_date_text = date_str
            elif "后天" in date_str:
                result.date = (datetime.now() + timedelta(days=2)).date()
                result.raw_date_text = date_str
            else:
                # 正则无法解析，保存原始文本让 LLM 处理
                result.raw_date_text = date_str
                # 尝试用 LLM 解析
                llm_date = parse_date_with_llm(date_str)
                if llm_date:
                    result.date = llm_date
                else:
                    # 默认明天
                    result.date = (datetime.now() + timedelta(days=1)).date()

        # Extract number of passengers
        people_match = re.search(patterns["people"], user_input, re.IGNORECASE)
        if people_match:
            result.passengers = int(people_match.group(1))

        # Check if we have enough info for a trip
        if result.departure and result.destination and result.date:
            result.has_trip_request = True

        return result

    async def _arun(self, user_input: str) -> ExtractedInfo:
        return self._run(user_input)
