"""Main LangGraph - Enterprise Travel Agent with dynamic routing"""

from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.schemas.state import TravelState, IntentType, get_trip_field
from backend.agents.nodes import (
    intent_node,
    extractor_node,
    tmc_query_node,
    recommend_node,
    booker_node,
    chat_node,
)


def route_after_intent(
    state: TravelState,
) -> Literal["chat", "extractor", "booker", "end"]:
    """Route based on intent and existing state."""
    intent = state.intent or "unknown"
    if isinstance(intent, IntentType):
        intent = intent.value

    if intent in ("greeting", "chat", "cancel", "expense"):
        return "chat"

    # If recommendations exist and user confirms, go to booking
    recs = state.recommendations
    has_recs = bool(recs) if isinstance(recs, list) else False
    if has_recs and intent in ("approve", "book"):
        return "booker"

    if intent in ("trip_query", "book"):
        return "extractor"

    return "chat"


def route_after_extract(state: TravelState) -> Literal["tmc_query", "chat", "end"]:
    """Route after extraction: query TMC if complete, chat if missing info."""
    trip = state.trip
    departure = get_trip_field(trip, "departure")
    destination = get_trip_field(trip, "destination")
    date_val = get_trip_field(trip, "date")

    if departure and destination and date_val:
        return "tmc_query"
    return "chat"



def route_after_book(state: TravelState) -> Literal["end"]:
    """After booking, go to end."""
    return "end"


def build_travel_graph() -> StateGraph:
    """Build the main travel agent graph.

    Flow:
    intent -> extractor -> tmc_query -> recommend -> END (wait for confirm)
                                                    -> (next msg) booker -> END
    """
    workflow = StateGraph(TravelState)

    # Add nodes
    workflow.add_node("intent", intent_node)
    workflow.add_node("chat", chat_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("tmc_query", tmc_query_node)
    workflow.add_node("recommend", recommend_node)
    workflow.add_node("booker", booker_node)

    # Entry point
    workflow.set_entry_point("intent")

    # Intent -> Chat | Extractor | Booker
    workflow.add_conditional_edges(
        "intent",
        route_after_intent,
        {
            "chat": "chat",
            "extractor": "extractor",
            "booker": "booker",
            "end": END,
        },
    )

    # Chat -> END
    workflow.add_edge("chat", END)

    # Extractor -> TMC Query | Chat
    workflow.add_conditional_edges(
        "extractor",
        route_after_extract,
        {
            "tmc_query": "tmc_query",
            "chat": "chat",
            "end": END,
        },
    )

    # TMC Query -> Recommend
    workflow.add_edge("tmc_query", "recommend")

    # Recommend -> END (stop, wait for user)
    workflow.add_edge("recommend", END)

    # Booker -> END
    workflow.add_conditional_edges("booker", route_after_book, {"end": END})

    return workflow


# Compile with memory checkpointer
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

serde = JsonPlusSerializer().with_msgpack_allowlist(
    [
        ("backend", "schemas", "state", "TripInfo"),
        ("backend", "schemas", "state", "OrderRecord"),
        ("backend", "schemas", "state", "RecommendationItem"),
        ("backend", "schemas", "state", "PolicyViolation"),
    ]
)
memory = MemorySaver(serde=serde)
travel_graph = build_travel_graph().compile(checkpointer=memory)
