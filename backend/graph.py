from typing import Literal, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from backend.state import TravelState
from tools.information_extraction import InformationExtractionTool, ExtractedInfo
from tools.travel_recommendation import TravelRecommendationTool
from tools.tmc_api import TMCApiTool, TMCBookingResult
from tools.oa_finance import OAFinanceTool

import json

# Initialize tools
tools = [
    InformationExtractionTool(),
    TravelRecommendationTool(),
    TMCApiTool(),
    OAFinanceTool(),
]

tool_node = ToolNode(tools)


def should_continue(state: TravelState) -> Literal["tools", END]:
    """Determine if we should continue or end the current loop"""
    messages = state.messages
    last_message = messages[-1]

    if "tool_calls" in last_message and last_message["tool_calls"]:
        return "tools"

    return END


def agent_node(state: TravelState) -> dict:
    """Main agent decision and execution node"""

    if not state.extracted and state.last_message:
        # First step: always extract information
        ie_tool = InformationExtractionTool()
        extracted = ie_tool._run(state.last_message)

        # Create a completely new TripInfo object to avoid validation issues
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
            response_text = f"I've extracted your trip info: {extracted.departure} to {extracted.destination} on {extracted.date}. I'll now find recommendations for you."
        else:
            missing = []
            if not extracted.departure:
                missing.append("departure city")
            if not extracted.destination:
                missing.append("destination city")
            if not extracted.date:
                missing.append("travel date")
            response_text = f"I need more information: Please provide {', '.join(missing)} for your trip."
            updates["need_recommendation"] = False

        updates["messages"] = state.messages + [
            {"role": "assistant", "content": response_text}
        ]

        return updates

    if state.need_recommendation and not state.recommendations:
        # Second step: generate recommendations
        rec_tool = TravelRecommendationTool()
        recommendations = rec_tool._run(
            departure=state.trip.departure,
            destination=state.trip.destination,
            travel_date=state.trip.date,
            passengers=state.trip.passengers,
        )

        response_text = f"Here are your travel recommendations from {state.trip.departure} to {state.trip.destination} on {state.trip.date.isoformat()}. Please select an option below:"

        return {
            "recommendations": [item.model_dump() for item in recommendations],
            "current_step": "recommended",
            "messages": state.messages
            + [{"role": "assistant", "content": response_text}],
        }

    # If booking is completed
    if (
        state.order.ticket_booked or state.order.hotel_booked
    ) and state.order.status == "booked":
        # Update finance system
        oa_tool = OAFinanceTool()
        result = oa_tool._run(
            order_id=state.order.order_id,
            user_id=state.user_id,
            status=state.order.status,
            amount=state.order.total_amount,
        )

        response_text = f"""✅ Booking completed successfully! 

Order ID: {state.order.order_id}
Amount charged to company account: ¥{state.order.total_amount:.2f}
Expense report created: {result.expense_id}

You can proceed directly to check-in / boarding with your ID. No payment needed from you. The finance system has been automatically updated."""

        return {
            "current_step": "completed",
            "messages": state.messages
            + [{"role": "assistant", "content": response_text}],
        }

    return {"messages": state.messages}


# Build the graph
workflow = StateGraph(TravelState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END,
    },
)
workflow.add_edge("tools", "agent")

# Compile with memory for persistence
memory = MemorySaver()
travel_graph = workflow.compile(checkpointer=memory)
