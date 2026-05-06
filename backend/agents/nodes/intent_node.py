"""Intent Classification Node - Uses LLM for fast classification"""

import json
import re
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from backend.llm import get_llm
from backend.schemas.state import TravelState, IntentType


def intent_node(state: TravelState) -> Dict:
    """Classify user intent using LLM."""
    last_msg = state.last_message or (
        state.messages[-1]["content"] if state.messages else ""
    )

    # Quick rule-based check for greetings
    greeting_words = [
        "你好",
        "您好",
        "hello",
        "hi",
        "hey",
        "早上好",
        "晚上好",
        "下午好",
        "早",
        "嗨",
    ]
    if any(w in last_msg.lower() for w in greeting_words) and len(last_msg) < 20:
        return {
            "intent": "greeting",
            "current_step": "intent_classified",
        }

    llm = get_llm(task="intent", timeout=15)
    if not llm:
        return {
            "intent": "chat",
            "current_step": "intent_classified",
        }

    try:
        system_msg = (
            "You are an intent classifier. Classify the user input into one category: "
            "greeting, chat, trip_query, book, approve, cancel, expense. "
            "Return ONLY a JSON object with an 'intent' key. No markdown, no explanation."
        )
        user_msg = "User input: " + last_msg

        response = llm.invoke(
            [
                SystemMessage(content=system_msg),
                HumanMessage(content=user_msg),
            ]
        )

        content = response.content if hasattr(response, "content") else str(response)
        # Strip markdown code blocks
        content = re.sub(r"```(?:json)?\s*", "", content)
        content = re.sub(r"```\s*", "", content)
        content = content.strip()

        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            result = json.loads(match.group())
            intent_str = str(result.get("intent", "chat")).strip().lower()
            # Validate against known intents
            valid = {e.value for e in IntentType}
            if intent_str not in valid:
                intent_str = "chat"
            return {
                "intent": intent_str,
                "current_step": "intent_classified",
            }
    except Exception as e:
        print(f"[Intent Node Error] {e}")
        import traceback

        traceback.print_exc()

    return {
        "intent": "chat",
        "current_step": "intent_classified",
    }
