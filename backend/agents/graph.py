# backend/agents/graph.py
"""LangGraph travel agent workflow"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.schemas.state import TravelState
from backend.nodes.intent_node import intent_node
from backend.nodes.extract_node import extract_node
from backend.nodes.recommend_node import recommend_node
from backend.nodes.chat_node import chat_node


def should_continue(state: TravelState) -> Literal["recommend", "chat", "end"]:
    """Determine next step based on state"""

    # If need recommendation and not yet generated
    if state.need_recommendation and not state.recommendations:
        return "recommend"

    # Continue to chat for response
    return "chat"


# Build the graph
workflow = StateGraph(TravelState)

# Add nodes
workflow.add_node("intent", intent_node)
workflow.add_node("extract", extract_node)
workflow.add_node("recommend", recommend_node)
workflow.add_node("chat", chat_node)

# Set entry point
workflow.set_entry_point("intent")

# Add edges
workflow.add_edge("intent", "extract")


# Conditional edges from extract
def extract_continue(state: TravelState) -> Literal["recommend", "chat"]:
    """After extraction, either recommend or chat"""
    if state.need_recommendation and not state.recommendations:
        return "recommend"
    return "chat"


workflow.add_conditional_edges(
    "extract",
    extract_continue,
    {
        "recommend": "recommend",
        "chat": "chat",
    },
)

workflow.add_edge("recommend", END)
workflow.add_edge("chat", END)

# Compile with memory checkpointer
memory = MemorySaver()
travel_graph = workflow.compile(checkpointer=memory)
