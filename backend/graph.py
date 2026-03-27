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
5. **如果用户问关于目的地的一般信息（如城市介绍、天气、景点等），你应该先回答这个问题，然后再继续收集差旅信息**

回复要求：
- 使用中文回复
- 语气友好、专业、简洁
- 主动引导用户说明目的地和日期
- 如果用户问你是谁，告诉用户你是企业差旅智能助手
- 每次回复要简洁，不要重复之前已经说过的内容
- 如果已知用户的需求，不要再重复询问已知信息
- **如果用户的问题与差旅安排无关，先回答用户的问题，然后再温柔地引导回差旅话题**"""


SUMMARY_PROMPT = """请用简短的一段话总结以下对话内容，提取已确定的差旅信息（出发地、目的地、日期、人数、交通偏好等）。如果用户还未提供完整信息，也要说明缺少哪些信息。

对话内容：
{messages}

请直接给出总结，不需要其他解释。"""


def summarize_conversation(messages: list) -> str:
    """用另一个LLM调用来总结对话"""
    # 只取最近5条消息，避免过长
    recent_msgs = messages[-5:] if len(messages) > 5 else messages

    # 格式化对话
    formatted = "\n".join(
        [
            f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:100]}..."
            for m in recent_msgs
        ]
    )

    result = call_llm(
        [{"role": "user", "content": SUMMARY_PROMPT.format(messages=formatted)}],
        system_prompt="你是一个对话总结助手，请用中文总结对话要点。",
    )
    return result if result else ""


def call_llm(
    messages: list, system_prompt: str = SYSTEM_PROMPT, include_summary: bool = True
) -> str:
    """调用LLM API，带超时处理"""
    import threading

    result = [None]
    error = [None]

    def _call():
        try:
            from backend.llm import get_llm
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = get_llm(timeout=30)

            # 构建消息
            langchain_msgs = [SystemMessage(content=system_prompt)]

            # 如果有摘要，加到开头
            if include_summary:
                # 从当前状态获取摘要
                pass  # 会在外部处理

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
    """Node that calls the travel recommendation tool with LLM ranking"""
    rec_tool = TravelRecommendationTool()

    # 获取推荐和推荐理由
    recommendations, reasons = rec_tool._run(
        departure=state.trip.departure,
        destination=state.trip.destination,
        travel_date=state.trip.date,
        passengers=state.trip.passengers,
    )

    # 生成带推荐理由的响应
    if reasons:
        reason_texts = []
        for item in recommendations[:3]:  # 只显示前3个的推荐理由
            if item.id in reasons:
                reason_texts.append(f"• {item.name}: {reasons[item.id]}")

        response_text = (
            f"为您找到了从 {state.trip.departure} 到 {state.trip.destination} 的出行方案：\n"
            + "\n".join(reason_texts)
        )
    else:
        response_text = f"为您找到了从 {state.trip.departure} 到 {state.trip.destination} 的出行方案。请选择以下选项："

    return {
        "recommendations": [item.model_dump() for item in recommendations],
        "current_step": "recommended",
        "messages": state.messages + [{"role": "assistant", "content": response_text}],
    }


def agent_node(state: TravelState) -> dict:
    """Main agent decision and execution node"""

    # 如果对话较长，先总结
    conversation_summary = ""
    if len(state.messages) > 6:
        conversation_summary = summarize_conversation(state.messages)
        state.conversation_summary = conversation_summary

    # 构建精简上下文：摘要 + 最后一条用户消息
    if conversation_summary:
        context_msgs = [
            {"role": "system", "content": f"【已确认信息】{conversation_summary}"}
        ]
    else:
        context_msgs = []

    context_msgs.append({"role": "user", "content": state.last_message})

    # 每次都尝试提取信息，不管之前是否extracted
    ie_tool = InformationExtractionTool()
    extracted = ie_tool._run(state.last_message)

    # 更新trip信息
    new_trip = state.trip.model_copy()
    has_new_info = False

    # 合并提取的信息
    if extracted.departure:
        new_trip.departure = extracted.departure
        has_new_info = True
    if extracted.destination:
        new_trip.destination = extracted.destination
        has_new_info = True
    if extracted.date:
        new_trip.date = extracted.date
        has_new_info = True
    if extracted.passengers > 1:
        new_trip.passengers = extracted.passengers
        has_new_info = True

    # 如果有提取到新信息，更新状态
    if has_new_info:
        new_trip.user_input = state.last_message

    # 已有出发地和目的地，检查是否需要继续询问日期
    has_departure_dest = new_trip.departure and new_trip.destination

    # 判断是否需要提取推荐
    if has_departure_dest and new_trip.date:
        # 有完整信息，生成推荐
        if not state.recommendations:
            updates = {
                "extracted": True,
                "current_step": "extracted",
                "trip": new_trip,
                "need_recommendation": True,
            }
            llm_resp = call_llm(context_msgs)
            if llm_resp:
                response_text = llm_resp
            else:
                response_text = f"好的，已为您记录出行信息：{new_trip.departure} → {new_trip.destination}，{new_trip.date}。正在为您查找推荐方案..."

            updates["messages"] = state.messages + [
                {"role": "assistant", "content": response_text}
            ]
            return updates

    # 有出发地和目的地但缺少日期，给 LLM 更多信息让它判断如何回复
    if has_departure_dest and not new_trip.date:
        updates = {
            "extracted": True,
            "current_step": "extracted",
            "trip": new_trip,
            "need_recommendation": False,
        }
        llm_resp = call_llm(context_msgs)
        if llm_resp:
            response_text = llm_resp
        else:
            response_text = f"好的，已记录您从 {new_trip.departure} 到 {new_trip.destination}。请问您计划哪天出发呢？"

        updates["messages"] = state.messages + [
            {"role": "assistant", "content": response_text}
        ]
        return updates

    # 信息不完整，继续询问
    updates = {
        "extracted": True,
        "current_step": "extracted",
        "trip": new_trip,
        "need_recommendation": False,
    }

    llm_resp = call_llm(context_msgs)
    if llm_resp:
        response_text = llm_resp
    else:
        missing = []
        if not new_trip.departure:
            missing.append("出发城市")
        if not new_trip.destination:
            missing.append("目的地")
        if not new_trip.date:
            missing.append("出行日期")
        if missing:
            response_text = f"好的，请问您{', '.join(missing)}呢？"
        else:
            response_text = "好的，请问您还需要补充什么信息？"

    updates["messages"] = state.messages + [
        {"role": "assistant", "content": response_text}
    ]

    return updates


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
