from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.state import TravelState
from tools.information_extraction import InformationExtractionTool
from tools.travel_recommendation import TravelRecommendationTool

SYSTEM_PROMPT = """你是一个企业差旅智能助手，专门帮助员工安排出差行程。

你的职责：
1. 友好地与用户对话，询问差旅需求
2. 引导用户提供：出发城市、目的地、出行日期、人数等信息
3. 根据用户需求推荐合适的火车、航班和酒店
4. 协助完成预订流程

回复要求：
- 使用中文回复
- 语气友好、专业、简洁
- 主动引导用户说明目的地和日期
- 如果用户问你是谁，告诉用户你是企业差旅智能助手"""


def call_llm(messages: list, system_prompt: str = SYSTEM_PROMPT) -> str:
    """调用LLM API，带超时处理"""
    import threading

    result = [None]
    error = [None]

    def _call():
        try:
            from backend.llm import get_llm
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = get_llm(timeout=30)

            langchain_msgs = [SystemMessage(content=system_prompt)]
            for msg in messages:
                if msg["role"] == "user":
                    langchain_msgs.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_msgs.append({"type": "ai", "content": msg["content"]})

            response = llm.invoke(langchain_msgs)
            result[0] = (
                response.content if hasattr(response, "content") else str(response)
            )
        except Exception as e:
            error[0] = e

    # 用线程避免阻塞
    t = threading.Thread(target=_call)
    t.daemon = True
    t.start()
    t.join(timeout=35)

    if result[0]:
        return result[0]
    if error[0]:
        print(f"[LLM调用失败] {type(error[0]).__name__}: {error[0]}")
    return None


def recommendation_node(state: TravelState) -> dict:
    """Node that calls the travel recommendation tool"""
    rec_tool = TravelRecommendationTool()
    recommendations = rec_tool._run(
        departure=state.trip.departure,
        destination=state.trip.destination,
        travel_date=state.trip.date,
        passengers=state.trip.passengers,
    )

    response_text = f"为您找到了从 {state.trip.departure} 到 {state.trip.destination} 的出行方案。请选择以下选项："

    return {
        "recommendations": [item.model_dump() for item in recommendations],
        "current_step": "recommended",
        "messages": state.messages + [{"role": "assistant", "content": response_text}],
    }


def agent_node(state: TravelState) -> dict:
    """Main agent decision and execution node"""

    if not state.extracted and state.last_message:
        ie_tool = InformationExtractionTool()
        extracted = ie_tool._run(state.last_message)

        new_trip = state.trip.model_copy()
        new_trip.departure = extracted.departure
        new_trip.destination = extracted.destination
        new_trip.date = extracted.date
        new_trip.passengers = extracted.passengers
        new_trip.user_input = state.last_message

        updates = {
            "extracted": True,
            "current_step": "extracted",
            "trip": new_trip,
        }

        if (
            extracted.has_trip_request
            and extracted.departure
            and extracted.destination
            and extracted.date
        ):
            updates["need_recommendation"] = True
            # 优先用LLM
            llm_resp = call_llm(
                state.messages + [{"role": "user", "content": state.last_message}]
            )
            if llm_resp:
                response_text = llm_resp
            else:
                response_text = f"好的，已为您记录出行信息：{extracted.departure} → {extracted.destination}，{extracted.date}。正在为您查找推荐方案..."
        else:
            # 信息不完整，用LLM引导用户
            llm_resp = call_llm(
                state.messages + [{"role": "user", "content": state.last_message}]
            )
            if llm_resp:
                response_text = llm_resp
            else:
                response_text = "好的，请问您计划什么时候出发？去哪个城市出差呢？请告诉我目的地和出行日期。"

            updates["need_recommendation"] = False

        updates["messages"] = state.messages + [
            {"role": "assistant", "content": response_text}
        ]

        return updates

    if state.need_recommendation and not state.recommendations:
        rec_tool = TravelRecommendationTool()
        recommendations = rec_tool._run(
            departure=state.trip.departure,
            destination=state.trip.destination,
            travel_date=state.trip.date,
            passengers=state.trip.passengers,
        )

        response_text = f"为您找到了从 {state.trip.departure} 到 {state.trip.destination} 的出行方案。请选择以下选项："

        return {
            "recommendations": [item.model_dump() for item in recommendations],
            "current_step": "recommended",
            "messages": state.messages
            + [{"role": "assistant", "content": response_text}],
        }

    # 其他情况优先用LLM
    llm_resp = call_llm(
        state.messages + [{"role": "user", "content": state.last_message}]
    )
    if llm_resp:
        return {
            "messages": state.messages + [{"role": "assistant", "content": llm_resp}]
        }

    # Fallback中文回复
    if state.extracted and not state.need_recommendation:
        response_text = (
            "好的，请问您计划什么时候出发？去哪个城市出差呢？请告诉我目的地和出行日期。"
        )
    elif state.current_step == "recommended":
        response_text = "请问您需要选择哪个方案？"
    else:
        response_text = "您好！我是企业差旅智能助手，请告诉我您的出行需求。"

    return {
        "messages": state.messages + [{"role": "assistant", "content": response_text}]
    }


def should_continue(state: TravelState) -> Literal["recommendation", "end"]:
    """判断是否需要继续到推荐节点"""
    if state.need_recommendation and not state.recommendations:
        return "recommendation"
    return "end"


# Build the graph
workflow = StateGraph(TravelState)

workflow.add_node("agent", agent_node)
workflow.add_node("recommendation", recommendation_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "recommendation": "recommendation",
        "end": END,
    },
)
workflow.add_edge("recommendation", END)

memory = MemorySaver()
travel_graph = workflow.compile(checkpointer=memory)
