"""Chat Node - General conversation and information gathering"""

from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from backend.llm import get_llm
from backend.schemas.state import TravelState, get_trip_field


def chat_node(state: TravelState) -> Dict:
    """Handle general conversation and information gathering."""
    trip = state.trip
    dep = get_trip_field(trip, "departure") or "未知"
    dest = get_trip_field(trip, "destination") or "未知"
    dt = get_trip_field(trip, "date") or "未知"
    pax = get_trip_field(trip, "passengers", 1)

    system_msg = (
        f"你是一个企业差旅智能助手。当前差旅信息：出发地={dep}, 目的地={dest}, 日期={dt}, 人数={pax}。"
        f"如果用户提供了新的差旅信息，在回复末尾用 JSON 格式标记："
        f"<extract>field: value</extract>。"
        f"否则正常对话。使用中文回复，语气友好专业。"
    )

    llm = get_llm(task="chat", timeout=20)
    if not llm:
        return _fallback_response(state)

    messages = [SystemMessage(content=system_msg)]
    for msg in state.messages[-10:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))

    try:
        resp = llm.invoke(messages)
        content = resp.content if hasattr(resp, "content") else str(resp)
        return {
            "current_step": "chat",
            "messages": [{"role": "assistant", "content": content}],
        }
    except Exception as e:
        print(f"[Chat Node Error] {e}")
        return _fallback_response(state)


def _fallback_response(state: TravelState) -> Dict:
    trip = state.trip
    dep = get_trip_field(trip, "departure")
    dest = get_trip_field(trip, "destination")
    dt = get_trip_field(trip, "date")
    pax = get_trip_field(trip, "passengers", 1)

    if not dep or not dest:
        return {
            "current_step": "chat",
            "messages": [
                {
                    "role": "assistant",
                    "content": "您好！我是企业差旅智能助手。请告诉我您的出行需求，例如：从北京到上海，下周一，1人。",
                }
            ],
        }
    if not dt:
        return {
            "current_step": "chat",
            "messages": [
                {
                    "role": "assistant",
                    "content": f"好的，从 {dep} 到 {dest}。请问您计划哪天出发？",
                }
            ],
        }
    return {
        "current_step": "chat",
        "messages": [
            {
                "role": "assistant",
                "content": f"好的，{dep} 到 {dest}，{dt}，{pax}人。正在为您查找方案...",
            }
        ],
    }
