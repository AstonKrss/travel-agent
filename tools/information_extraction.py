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

        # Extract departure
        from_match = re.search(patterns["from"], user_input, re.IGNORECASE)
        if from_match:
            result.departure = from_match.group(2).strip()
        else:
            # Check for pattern like "北京到广州"
            simple_match = re.match(
                r"^([一-\u9fa5A-Za-z]+)\s*(到|to)\s*([一-\u9fa5A-Za-z]+)", user_input
            )
            if simple_match:
                result.departure = simple_match.group(1).strip()
                result.destination = simple_match.group(3).strip()

        # Extract destination if not found above
        if not result.destination:
            to_match = re.search(patterns["to"], user_input, re.IGNORECASE)
            if to_match:
                result.destination = to_match.group(2).strip()

        # Extract date
        date_match = re.search(patterns["date"], user_input, re.IGNORECASE)
        if date_match:
            date_str = date_match.group(0)
            # Handle "next Monday" style
            if "下周一" in date_str:
                # Calculate next Monday from today
                today = datetime.now().date()
                days_ahead = 0 - today.weekday() + 7
                if days_ahead <= 0:
                    days_ahead += 7
                result.date = today + timedelta(days=days_ahead)
            elif re.match(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", date_str):
                result.date = datetime.strptime(
                    date_str.replace("/", "-"), "%Y-%m-%d"
                ).date()
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
