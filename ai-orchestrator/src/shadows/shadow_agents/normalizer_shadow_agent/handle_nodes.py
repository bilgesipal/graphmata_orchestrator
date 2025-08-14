
import json
from datetime import datetime


from src.config.config import AppConfig
from src.api.schemas.schemas import GraphState


class NormalizationHandler:

    def __init__(self, redis_conn, redis_client, pubsub, agent="normalization_agent"):
        self.redis_client = redis_client
        self.redis_conn = redis_conn
        self.pubsub = pubsub
        self.agent = agent


    def handle_normalization_success(self, state: GraphState) -> GraphState:
        print("handle_normalization_success")
        state_dict = state.model_dump()
        intent = state_dict["trace_info"].get("flow", "unknown_intent")

        if intent == "serpapi":
            params = (state_dict["state"]["current"].get("search_phase", {}).get("results_in_message", {}))
            print("DEBUG: Normalization success with SERPAPI results:", params)
            self.publish_action(
                state,
                transition="show_places",
                node_id="places_search",
                service="chat_agent",
                action="show_places",
                parameters=params
            )

        else:
            normalized_params = state_dict["state"]["current"].get("normalization_phase", {}).get(
                "normalized_parameters", {})

            self.publish_action(
                state,
                transition="proceed_to_hotel_search",
                node_id="hotel_search",
                service="hotel_search",
                action="search_hotels",
                parameters=normalized_params
            )
        return state

    def handle_normalization_failure(self, state: GraphState) -> GraphState:
        print("handle_normalization_failure")
        state_dict = state.model_dump()
        fallback_params = state_dict["state"]["current"].get("normalization_phase", {}).get("normalized_parameters", {})

        self.publish_action(
            state,
            transition="proceed_to_slot_fixing",
            node_id="slot_filling",
            service="chat_slot",
            action="collect_slot",
            parameters={
                "filled_slots": fallback_params,
                "slots_to_collect": ["location", "check_in_date", "check_out_date"]
            }
        )
        return state

    def publish_action(self, state: GraphState, *, transition, node_id, service, action, parameters):
        state_dict = state.model_dump()
        message = {
            "session_id": state_dict["session_id"],
            "message_id": state_dict["message_id"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.4",
            "trace_info": {
                "trace_id": state_dict["trace_info"]["trace_id"]+1,
                "flow_type" : state_dict["trace_info"].get("flow_type","UNKNOWN"),
                "flow": state_dict["trace_info"]["flow"],
                "sequence": state_dict["trace_info"]["sequence"] + 1,
                "retry_count": 0
            },
            "metadata": {
                "user_id": state_dict["metadata"].get("user_id"),
                "application_id": state_dict["metadata"].get("application_id"),
                "language": state_dict["metadata"].get("language", "tr"),
                "source_service": "orchestrator",
                "event_type": "next_action",
                "customerid_ui": state_dict["metadata"].get("customer_ui", []),
                "travelUsageType": state_dict["metadata"].get("travelUsageType", "corporate"),
                "redis_cache_address_general_info": state_dict["metadata"].get("redis_cache_address_general_info", []),
                "redis_cache_address_price_policy":state_dict["metadata"].get("redis_cache_address_price_policy", [])
            },
            "state": {
                "previous_transition": state_dict["state"]["transition"],
                "transition": transition
            },
            "orchestration": {
                "flow_director": "orchestrator",
                "flow_id": state_dict["trace_info"]["flow"],
                "node_id": node_id,
                "actions": {
                    "service": service,
                    "action": action,
                    "parameters": parameters
                },
                'details': state_dict["state"]["current"].get("normalization_phase", {}).get("details", {}),
                'hotel_details': state_dict["state"]["current"].get("hotel_search_phase", {}).get("details", {})

            }
        }

        if service == "hotel_search":
            channel = AppConfig.REDIS_PUBLISH_SEARCH
        else:
            channel = AppConfig.REDIS_PUBLISH_CHAT
        message_json = json.dumps(message, default=str, ensure_ascii=False)
        self.redis_client.publish(channel=channel, message=message_json)
        self.redis_conn.cache_state_conv_redis(state=GraphState.model_validate(message), agent_type=self.agent)
        print(f"[shadow_normalizer_agent] Published to {channel}: {action} at {node_id}")
        return message
