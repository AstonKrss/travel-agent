from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from datetime import datetime, date, timedelta
import re


class IEInput(BaseModel):
    user_input: str = Field(description="User's natural language input text")


class ExtractedInfo(BaseModel):
    departure: Optional[str] = None
    destination: Optional[str] = None
    date: Optional[date] = None
    passengers: int = 1
    preferences: dict = Field(default_factory=dict)
    has_trip_request: bool = False


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
            "date": r"(下?周?[一二三四五六日]|\d{4}[-/]\d{1,2}[-/]\d{1,2}|(?:周|星期)[一二三四五六日天]|明天|后天|下周一|下周二|下周三|下周四|下周五|下周六|下周日)",
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
                "周一": 0,
                "星期一": 0,
                "周一": 0,
                "周二": 1,
                "星期二": 1,
                "周三": 2,
                "星期三": 2,
                "周四": 3,
                "星期四": 3,
                "周五": 4,
                "星期五": 4,
                "周六": 5,
                "星期六": 5,
                "周日": 6,
                "星期天": 6,
                "周日": 6,
            }

            # Handle "下周一" style
            if (
                "下周一" in date_str
                or "下周二" in date_str
                or "下周三" in date_str
                or "下周四" in date_str
                or "下周五" in date_str
                or "下周六" in date_str
                or "下周日" in date_str
                or "下周" in date_str
            ):
                today = datetime.now().date()
                # Find next occurrence of the day
                weekday = 0
                for k, v in day_map.items():
                    if k in date_str:
                        weekday = v
                        break
                days_ahead = weekday - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                result.date = today + timedelta(days=days_ahead)
            elif re.match(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", date_str):
                result.date = datetime.strptime(
                    date_str.replace("/", "-"), "%Y-%m-%d"
                ).date()
            elif "明天" in date_str:
                result.date = (datetime.now() + timedelta(days=1)).date()
            elif "后天" in date_str:
                result.date = (datetime.now() + timedelta(days=2)).date()
            else:
                # Default to tomorrow for other cases
                tomorrow = datetime.now().date() + timedelta(days=1)
                result.date = tomorrow

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
