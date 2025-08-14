
from datetime import datetime
from pydantic import BaseModel
import json

from src.config.config import AppConfig
from src.api.schemas.schemas import GraphState


class HotelSearchHandler:

    def __init__(self, redis_conn, redis_client, pubsub):
        self.redis_conn = redis_conn
        self.agent = "search_agent"
        self.redis_client = redis_client
        self.pubsub = pubsub


    def publish_action(self, state: GraphState, *, transition, node_id, service, action, parameters):
        state_dict = state.model_dump()
        message = {
            "session_id": state_dict["session_id"],
            "message_id": state_dict["message_id"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.4",
            "trace_info": {
                "trace_id": state_dict["trace_info"]["trace_id" ] +1,
                "flow_type" : state_dict["trace_info"].get("flow_type" ,"UNKNOWN"),
                "flow": state_dict["trace_info"]["flow"],
                "sequence": state_dict["trace_info"]["sequence" ] +1,
                "retry_count": 0
            },
            "metadata": {
                "user_id": state_dict["metadata"].get("user_id"),
                "application_id": state_dict["metadata"].get("application_id"),
                "language": state_dict["metadata"].get("language"),
                "source_service": "orchestrator",
                "event_type": "next_action",
                "customerid_ui": state_dict["metadata"].get("customer_ui", []),
                "travelUsageType": state_dict["metadata"].get("travelUsageType", "corporate"),
                "redis_cache_address_general_info": state_dict["metadata"].get("redis_cache_address_general_info", []),
                "redis_cache_address_price_policy" :state_dict["metadata"].get("redis_cache_address_price_policy", [])
            },
            "state": {
                "previous_transition": state_dict["state"].get("transition", ""),
                "transition": transition
            },
            "orchestration": {
                "flow_director": "orchestrator",
                "flow_id": state_dict["trace_info"]["flow"],
                "node_id": node_id,
                "actions": {
                    "service": service,
                    "action": action,
                    "redis_cache_address": state_dict["state"]["current"]["search_phase"].get("redis_cache_address", ''),
                    "parameters": parameters
                }
            }
        }

        channel = AppConfig.REDIS_PUBLISH_CHAT
        self.redis_conn.publish_redis(channel=channel, message=json.dumps(message))
        self.redis_conn.cache_state_conv_redis(state=message, agent_type=self.agent)
        print(f"[shadow_search_agent] Published to {channel}: {action} at {node_id}")
        return message

    def handle_ask_detail(self, state: GraphState) -> GraphState:
        print("handle_search_found_results")
        state_dict = state.model_dump()
        chosen_hotels = state_dict["state"]["current"]["search_phase"]["results_in_message"].get("chosen_hotels", {})
        return GraphState.model_validate(self.publish_action(
            state,
            transition="proceed_to_cache_check",
            node_id="cache_check",
            service="chat_agent",
            action="check_cache_and_respond",
            parameters={
                "total_results_count": state_dict["state"]["current"]["search_phase"].get("total_results_count", 0),
                "chosen_hotels": chosen_hotels}
        ))

    def handle_search_found_results(self, state: GraphState) -> GraphState:
        print("handle_search_found_results")
        state_dict = state.model_dump()
        intent = state.trace_info.flow
        print(f"handle_search_found_results: {intent}")

        chosen_hotels = state_dict["state"]["current"]["search_phase"]["results_in_message"].get("chosen_hotels", {})
        if "hotel_list" in intent:
            redis_pp, redis_gen, chosen_hotels = self.redis_conn.handle_search_agent(state_dict)
            state_dict["metadata"]["redis_cache_address_price_policy"] = redis_pp
            state_dict["metadata"]["redis_cache_address_general_info"] = redis_gen

        self.publish_action(
            state,
            transition="request_chat_show_hotels",
            node_id="show_hotels",
            service="chat_agent",
            action="show_hotels",
            parameters={
                "total_results_count": state_dict["state"]["current"]["search_phase"].get("total_results_count", 0),
                "chosen_hotels": chosen_hotels}
        )
        return state

    def handle_search_empty(self, state: GraphState) -> GraphState:
        print("handle_search_NO_results")
        state_dict = state.model_dump()

        return GraphState.model_validate(self.publish_action(
            state,
            transition="request_chat_empty_hotels",
            node_id="show_hotels",
            service="chat_agent",
            action="create_system_message",
            parameters={
                "total_results_count": 0,
                "chosen_hotels": []}
        ))

    def handle_hotel_compare(self, state: GraphState) -> GraphState:
        print("handle_hotel_compare")
        state_dict = state.model_dump()
        chosen_hotels = state_dict["state"]["current"]["search_phase"]["results_in_message"].get("chosen_hotels", {})
        return GraphState.model_validate(self.publish_action(
            state,
            transition="proceed_to_hotel_compare",
            node_id="hotel_compare",
            service="chat_agent",
            action="compare_hotels",
            parameters={
                "total_results_count": state_dict["state"]["current"]["search_phase"].get("total_results_count", 0),
                "chosen_hotels": chosen_hotels}
        ))
