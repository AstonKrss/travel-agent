from typing import Optional, Tuple
from datetime import datetime, date, timedelta
import re


# Canonical DAY_MAP — shared by all date-resolving code
DAY_MAP = {
    "周一": 0, "星期一": 0, "周1": 0, "周0": 0,
    "周二": 1, "星期二": 1, "周2": 1,
    "周三": 2, "星期三": 2, "周3": 2,
    "周四": 3, "星期四": 3, "周4": 3,
    "周五": 4, "星期五": 4, "周5": 4,
    "周六": 5, "星期六": 5, "周6": 5,
    "周日": 6, "星期天": 6, "周7": 6,
}

# Date suffixes appended to destination — must be stripped before saving
_DATE_SUFFIXES = (
    "下周一", "下周二", "下周三", "下周四", "下周五", "下周六", "下周日",
    "下周",
)


def _strip_date_suffix(dest: str) -> str:
    """Strip trailing date suffixes like '上海下周一' -> '上海'."""
    for sfx in _DATE_SUFFIXES:
        if dest.endswith(sfx):
            return dest[: len(dest) - len(sfx)]
    return dest


def resolve_date(text: str) -> Optional[str]:
    """Resolve relative date expressions to YYYY-MM-DD."""
    today = datetime.now().date()

    explicit = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if explicit:
        return f"{explicit.group(1)}-{int(explicit.group(2)):02d}-{int(explicit.group(3)):02d}"

    is_next = "下" in text

    for day_name, weekday in DAY_MAP.items():
        if day_name in text:
            days_ahead = weekday - today.weekday()
            if is_next or days_ahead <= 0:
                days_ahead += 7
            target = today + timedelta(days=days_ahead)
            return target.isoformat()

    if "明天" in text:
        return (today + timedelta(days=1)).isoformat()
    if "后天" in text:
        return (today + timedelta(days=2)).isoformat()
    if "今天" in text:
        return today.isoformat()

    return None


def extract_route(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract departure and destination from text, stripping date suffixes."""
    m = re.search(
        r"从\s*([\u4e00-\u9fa5A-Za-z]+?)\s*到\s*([\u4e00-\u9fa5A-Za-z]+)", text
    )
    if m:
        dep, dest = m.group(1).strip(), m.group(2).strip()
        return _strip_date_suffix(dep), _strip_date_suffix(dest)

    m = re.match(r"^([\u4e00-\u9fa5]{2,4})\s*到\s*([\u4e00-\u9fa5]{2,4})", text)
    if m:
        dep, dest = m.group(1).strip(), m.group(2).strip()
        return _strip_date_suffix(dep), _strip_date_suffix(dest)

    return None, None


def extract_passengers(text: str) -> int:
    """Extract number of passengers."""
    m = re.search(r"(\d+)\s*[人位]", text)
    if m:
        return max(1, int(m.group(1)))
    return 1


def extract_budget(text: str) -> Optional[float]:
    """Extract budget amount."""
    m = re.search(r"(\d+)\s*(元|块|cny|CNY)", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def parse_date_with_llm(date_text: str) -> Optional[date]:
    """Use LLM to parse complex/ambiguous date text."""
    from backend.llm import get_llm
    from langchain_core.messages import HumanMessage

    llm = get_llm(task="extraction", timeout=10)
    if not llm:
        return None

    prompt = (
        f"请根据今天的日期 {datetime.now().date()}，解析以下日期文本并返回标准日期。\n"
        f"日期文本: {date_text}\n"
        "只返回格式如 '2026-03-30' 的日期，不需要其他内容。如果无法解析，返回 'NONE'。"
    )

    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        content = resp.content if hasattr(resp, "content") else str(resp)
        date_str = content.strip()
        if date_str and date_str != "NONE":
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    pass
            match = re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", date_str)
            if match:
                return datetime.strptime(
                    match.group().replace("/", "-"), "%Y-%m-%d"
                ).date()
    except Exception as e:
        print(f"LLM date parse error: {e}")

    return None
