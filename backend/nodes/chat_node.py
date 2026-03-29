# backend/nodes/chat_node.py
"""Chat/response node"""

from typing import Dict, Any
import threading

from backend.schemas.state import TravelState


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


def chat_node(state: TravelState) -> Dict[str, Any]:
    """Generate chat response using LLM"""

    def _call_llm():
        try:
            from backend.llm import get_llm
            from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

            llm = get_llm(timeout=30)
            if not llm:
                return None

            # Build messages with full history
            langchain_msgs = [SystemMessage(content=SYSTEM_PROMPT)]

            # Add conversation history
            for msg in state.messages:
                if msg["role"] == "user":
                    langchain_msgs.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_msgs.append(AIMessage(content=msg["content"]))

            # Add current message
            if state.last_message:
                langchain_msgs.append(HumanMessage(content=state.last_message))

            response = llm.invoke(langchain_msgs)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            print(f"LLM call error: {e}")
            return None

    # Call LLM in thread to avoid blocking
    result = [None]
    t = threading.Thread(target=lambda: result.__setitem__(0, _call_llm()))
    t.daemon = True
    t.start()
    t.join(timeout=35)

    response_text = result[0]

    if not response_text:
        # Generate fallback response based on trip info
        trip = state.trip
        missing = []
        if not trip.departure:
            missing.append("出发城市")
        if not trip.destination:
            missing.append("目的地")
        if not trip.date:
            missing.append("出行日期")

        if missing:
            response_text = f"好的，请问您{', '.join(missing)}呢？"
        else:
            response_text = "好的，请问您还需要补充什么信息？"

    return {
        "messages": state.messages + [{"role": "assistant", "content": response_text}],
    }
