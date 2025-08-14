import uuid
import json
from typing import Dict, Any
from datetime import datetime
from langgraph.graph import END, StateGraph

from src.api.schemas.schemas import GraphState
from src.config.config import AppConfig
from src.redis_connect.connect import RedisConnections


class ShadowChatAgent:
    def __init__(self):
        self.redis_conn = RedisConnections(host=AppConfig.REDIS_HOST, port=AppConfig.REDIS_PORT)
        self.agent = "chat_agent"
        self.graph = self._build_graph()
        self.redis_client = self.redis_conn.get_redis_client()
        self.pubsub = self.redis_conn.get_redis_pubsub()

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(GraphState)
        builder.add_node("check_and_route", self.check_and_route)
        builder.add_node("save_to_redis", self.save_to_redis)
        builder.add_node("fallback", self.fallback)

        def route_condition(state):
            state_dict = state if isinstance(state, dict) else state.model_dump()
            route = state_dict.get("route", "save")
            print(f"[shadow_chat_agent] route_condition: {route}")

            if route == "fallback":
                return "fallback"
            else:
                return "save_to_redis"

        builder.add_conditional_edges(
            "check_and_route",
            route_condition
        )

        builder.add_edge("save_to_redis", END)
        builder.add_edge("fallback", END)
        builder.set_entry_point("check_and_route")

        return builder.compile()

    def check_and_route(self, state: GraphState) -> GraphState:
        """Check the state and determine routing"""
        state_dict = state.model_dump()
        route = "save"
        current = state_dict.get("state", {}).get("current", {})
        transition = state_dict.get("state", {}).get("transition", "")

        # TODO: FALLBACK LOGIC
        if transition == "error" or transition == "unknown":
            route = "fallback"
        if not current and not state_dict.get("system_message"):
            route = "fallback"

        state_dict["route"] = route
        print(f"[shadow_chat_agent] Routing to: {route}")

        return GraphState.model_validate(state_dict)

    def save_to_redis(self, state: GraphState) -> GraphState:
        """Save the state to Redis - no actions or publishing"""
        print("[shadow_chat_agent] Saving state to Redis")

        self.redis_conn.cache_state_conv_redis(state=state, agent_type=self.agent)
        state_dict = state.model_dump()
        session_id = state_dict.get("session_id")
        current = state_dict.get("state", {}).get("current", {})
        if "slot_filling_phase" in current:
            status = current["slot_filling_phase"].get("status")
            print(f"[shadow_chat_agent] Saved slot_filling state (status: {status}) for session: {session_id}")
        elif "confirmation_phase" in current:
            status = current["confirmation_phase"].get("status")
            print(f"[shadow_chat_agent] Saved confirmation state (status: {status}) for session: {session_id}")
        else:
            print(f"[shadow_chat_agent] Saved state for session: {session_id}")
        if "system_message" in state_dict and "text" in state_dict["system_message"]:
            print(f"[shadow_chat_agent] System message present: {state_dict['system_message']['text'][:50]}...")

        return state

    def fallback(self, state: GraphState) -> GraphState:
        """Handle fallback cases"""
        print("[shadow_chat_agent] Handling fallback case")

        state_dict = state.model_dump()
        session_id = state_dict.get("session_id")
        transition = state_dict.get("state", {}).get("transition", "")

        print(f"[shadow_chat_agent] Fallback triggered for session: {session_id}, transition: {transition}")
        self.redis_conn.cache_state_conv_redis(state=state, agent_type=self.agent)
        print(f"[shadow_chat_agent] Fallback: Saved state to Redis for session: {session_id}")

        # TODO: Add any specific fallback handling logic here

        return state

    def handle_message(self, json_str: str) -> Dict[str, Any]:
        """Main entry point to process a message"""
        print("[shadow_chat_agent] handle_message called")
        try:
            input_dict = json.loads(json_str)
            #print('INPUT:', json.dumps(input_dict, indent=2))
            session_id = input_dict.get("session_id")
            transition = input_dict.get("state", {}).get("transition", "")
            print(f"[shadow_chat_agent] Processing message for session: {session_id}, transition: {transition}")
            state = GraphState.model_validate(input_dict)
            final_state = self.graph.invoke(
                state,
                config={"configurable": {"thread_id": f"shadow-chat-agent-thread-{session_id}"}}
            )

            if not isinstance(final_state, GraphState):
                final_state = GraphState.model_validate(final_state)

            final_dict = final_state.model_dump()

            print(f"[shadow_chat_agent] Successfully processed state for session: {session_id}")
            return final_dict

        except Exception as e:
            print(f"[shadow_chat_agent] Error in handle_message: {e}")
            return {
                "error": str(e),
                "input": json_str[:100] + "..." if len(json_str) > 100 else json_str
            }