import json
from datetime import datetime
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from src.config.config import AppConfig
from src.redis_connect.connect import RedisConnections
from src.shadows.shadow_agents.normalizer_shadow_agent.handle_nodes import NormalizationHandler
from src.api.schemas.schemas import GraphState


class ShadowNormalizerAgent:
    def __init__(self):
        self.redis_conn = RedisConnections(host=AppConfig.REDIS_HOST, port=AppConfig.REDIS_PORT)
        self.agent = "normalization_agent"
        self.redis_client = self.redis_conn.get_redis_client()
        self.pubsub = self.redis_conn.get_redis_pubsub()

        self.handle_functions = NormalizationHandler(self.redis_conn, self.redis_client, self.pubsub)

        self.graph = self._build_graph()



    def _build_graph(self) -> StateGraph:
        builder = StateGraph(GraphState)
        builder.add_node("check_normalization_result", self.route_phase)
        builder.add_node("handle_normalization_success", self.handle_functions.handle_normalization_success)
        builder.add_node("handle_normalization_failure", self.handle_functions.handle_normalization_failure)

        def route_condition(state):
            state_dict = state if isinstance(state, dict) else state.model_dump()
            route = state_dict.get("route")
            print(f"route_condition: {route}")
            return {
                "normalization_success": "handle_normalization_success",
                "normalization_failure": "handle_normalization_failure"
            }.get(route, " ")

        builder.add_conditional_edges("check_normalization_result", route_condition)
        builder.add_edge("handle_normalization_success", END)
        builder.add_edge("handle_normalization_failure", END)
        builder.set_entry_point("check_normalization_result")
        return builder.compile()

    def route_phase(self, state: GraphState) -> Dict[str, Any]:
        print("route_phase")
        state_dict = state.model_dump()
        normalization = state_dict["state"]["current"].get("normalization_phase", {})
        status = normalization.get("status")
        has_parameters = bool(normalization.get("normalized_parameters"))

        if "transition" not in state_dict["state"]:
            state_dict["state"]["transition"] = None
        else:
            transition = state_dict["state"]["transition"]

        state_dict["metadata"]["source_service"] = self.agent
        state_dict["message_id"] = state_dict["message_id"]
        state_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"

        print("DEBUG: Normalization status:", transition, status)

        if status == "completed" and has_parameters:
            state_dict["route"] = "normalization_success"

        elif transition == "serpapi_completed":
            state_dict["route"] = "normalization_success"
        else:
            state_dict["route"] = "normalization_failure"
        print("DEBUG: Normalization completed with parameters", state_dict["route"])
        print(f"Determined route: {state_dict['route']}")
        return GraphState.model_validate(state_dict)




    def handle_message(self, json_str: str) -> Dict[str, Any]:
        print("handle_message")
        try:
            input_dict = json.loads(json_str)
            state = GraphState.model_validate(input_dict)
            final_state = self.graph.invoke(
                state,
                config={"configurable": {"thread_id": "shadow-normalizer-agent-thread"}}
            )
            if not isinstance(final_state, GraphState):
                final_state = GraphState.model_validate(final_state)
            return final_state.model_dump()
        except Exception as e:
            print(f"Error in handle_message: {e}")
            return {"error": str(e)}
