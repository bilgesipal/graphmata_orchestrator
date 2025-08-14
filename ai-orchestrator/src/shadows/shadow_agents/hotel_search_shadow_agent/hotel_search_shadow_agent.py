import uuid
import json
from datetime import datetime
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from src.config.config import AppConfig
from src.redis_connect.connect import RedisConnections
from src.api.schemas.schemas import GraphState
from src.shadows.shadow_agents.hotel_search_shadow_agent.handle_nodes import HotelSearchHandler


class ShadowHotelSearchAgent:
    def __init__(self):
        self.redis_conn = RedisConnections(host=AppConfig.REDIS_HOST, port=AppConfig.REDIS_PORT)
        self.agent = "search_agent"
        self.redis_client = self.redis_conn.get_redis_client()
        self.pubsub = self.redis_conn.get_redis_pubsub()

        self.handle_functions = HotelSearchHandler(self.redis_conn, self.redis_client, self.pubsub)

        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(GraphState)
        builder.add_node("check_search_result", self.route_phase)
        builder.add_node("handle_search_found_results", self.handle_functions.handle_search_found_results)
        builder.add_node("handle_ask_detail", self.handle_functions.handle_ask_detail)
        builder.add_node("handle_hotel_compare", self.handle_functions.handle_hotel_compare)
        builder.add_node("handle_search_empty", self.handle_functions.handle_search_empty)

        def route_condition(state):
            state_dict = state if isinstance(state, dict) else state.model_dump()
            route = state_dict.get("route")
            print(f"route_condition: {route}")
            return {
                "search_success": "handle_search_found_results",
                "search_empty": "handle_search_empty",
                "handle_ask_detail": "handle_ask_detail",
                "handle_hotel_compare": "handle_hotel_compare"
            }.get(route, "handle_search_empty")

        builder.add_conditional_edges("check_search_result", route_condition)
        builder.add_edge("handle_search_found_results", END)
        builder.add_edge("handle_ask_detail", END)
        builder.add_edge("handle_hotel_compare", END)
        builder.add_edge("handle_search_empty", END)
        builder.set_entry_point("check_search_result")
        return builder.compile()

    def route_phase(self, state: GraphState) -> GraphState:
        print("route_phase")
        state_dict = state.model_dump()
        intent = state_dict["trace_info"]["flow"]
        redis_cache = state_dict["state"]["current"]["search_phase"].get("redis_cache_address", '')
        search_phase = state_dict["state"]["current"].get("search_phase", {})
        count = search_phase.get("total_results_count", 0)
        print(f"Total search results count: {count}")
        state_dict["trace_info"]["sequence"] += 1
        state_dict["metadata"]["source_service"] = self.agent
        state_dict["message_id"] = state_dict["message_id"]
        state_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"

        state_dict["route"] = "search_success" if count > 0 else "search_empty"
        if state_dict["route"] == "search_success" and redis_cache and 'hotel_ask' in intent:
            state_dict["route"] = "handle_ask_detail"
        elif state_dict["route"] == "search_success" and redis_cache and 'hotel_compare' in intent:
            state_dict["route"] = "handle_hotel_compare"

        print(f"Determined route: {state_dict['route']}")

        return GraphState.model_validate(state_dict)


    def handle_message(self, json_str: str) -> Dict[str, Any]:
        """Main entry point to process a message"""
        try:
            input_dict = json.loads(json_str)
            state = GraphState.model_validate(input_dict)
            final_state = self.graph.invoke(
                state,
                config={"configurable": {"thread_id": "shadow-intent-agent-thread"}}
            )

            if not isinstance(final_state, GraphState):
                final_state = GraphState.model_validate(final_state)

            return final_state.model_dump()

        except Exception as e:
            print(f"Error in handle_message: {e}")
            return {
                "error": str(e),
                "input": json_str[:100] + "..." if len(json_str) > 100 else json_str}
