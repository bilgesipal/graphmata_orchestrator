import json

from src.api.schemas.schemas import GraphState
from src.config.config import AppConfig
from datetime import datetime

from src.shadows.shadow_util.intent_util.intent_util import CacheChecker, StateHelper
from src.shadows.shadow_util.intent_util.intent_util import Intent, Route


class IntentHandlerNodes:

    def __init__(self, redis_conn,  redis_client, agent: str):
        self.redis_conn = redis_conn
        self.agent = agent
        self.redis_client = redis_client
        self.cache_helper = CacheChecker()
        self.helpers_state= StateHelper()


    def publish_action(self, state: GraphState, *, transition, node_id, service, action, parameters, flow_id):
        """Publish next action to appropriate channel """
        state_dict = state.model_dump()
        self.redis_conn.cache_state_conv_redis(state=state_dict, agent_type=self.agent)


        current_state = state_dict["state"].get("current", {})
        if transition == "proceed_to_slot_filling":
            trans_state = {
                "current": current_state,
                "previous_transition": state_dict["state"].get("transition", ""),
                "transition": transition}
        else:
            trans_state = {
                "previous_transition": state_dict["state"].get("transition", ""),
                "transition": transition}

        message = {
            "session_id": state_dict["session_id"],
            "message_id": state_dict["message_id"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.4",
            "trace_info": {
                "trace_id": state_dict["trace_info"]["trace_id"] + 1,
                "flow_type" : state_dict["trace_info"]["flow_type"],
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
                "customerid_ui" : state_dict["metadata"].get("customer_ui", []),
                "travelUsageType": state_dict["metadata"].get("travelUsageType", "corporate"),
                  "redis_cache_address_general_info": state_dict["metadata"].get("redis_cache_address_general_info", []),
                "redis_cache_address_price_policy":state_dict["metadata"].get("redis_cache_address_price_policy", [])
            },
            "state": trans_state,
            "orchestration": {
                "flow_director": "orchestrator",
                "flow_id": state_dict["trace_info"]["flow"],
                "node_id": node_id,
                "actions": {
                    "service": service,
                    "action": action,
                    "parameters": parameters
                }
            }
        }
        if service == "hotel_search":
            channel = AppConfig.REDIS_PUBLISH_SEARCH
        elif service == "normalization_service":
            channel = AppConfig.REDIS_PUBLISH_NORMALIZER
        else:
            channel = AppConfig.REDIS_PUBLISH_CHAT

        message_json = json.dumps(message, default=str, ensure_ascii=False)
        action_state = GraphState.model_validate(message)
        self.redis_conn.cache_state_conv_redis(state=action_state, agent_type=self.agent)
        self.redis_client.publish(channel=channel, message=message_json)
        print(f"[shadow_intent_agent] Published to {channel}: {action} at {node_id}")

        return message


    def handle_slot_filling(self, state: GraphState) -> GraphState:
        """Handle slot filling strategy"""
        state_dict = state.model_dump()
        current = state_dict["state"].get("current", {})
        intent_phase = current.get("intent_phase", {})
        intent = intent_phase.get("intent", "hotel_list")
        entities = intent_phase.get("entities", {})
        filtered_entities = {k: v for k, v in entities.items() if v not in (None, "", "LLM_outputText")}

        collector_list = self.helpers_state.get_slots_to_collect(intent, filtered_entities)

        if state_dict.get("route") == Route.CACHE_CHECK.value:
            if "hotel_list_next" == intent:
                parameters = {
                    "chosen_hotels": state_dict["chosen_hotels"]
                }
            transition = "proceed_to_cache_check"
            node_id = "cache_check"
            service = "chat_agent"
            action = "check_cache_and_respond"
        else:
            transition = "proceed_to_slot_filling"
            node_id = "slot_filling"
            service = "chat_agent"
            action = "collect_slot"
            parameters = {
                "filled_slots": filtered_entities,
                "slots_to_collect": collector_list
            }

        new_state = GraphState.model_validate(state_dict)
        self.publish_action(
            state,
            transition=transition,
            node_id=node_id,
            service=service,
            action=action,
            parameters=parameters,
            flow_id=f"{intent.split('_')[0]}_flow"
        )

        return new_state

    def handle_search(self, state: GraphState) -> GraphState:
        print("handle_normalization_success")
        state_dict = state.model_dump()
        current = state_dict["state"].get("current", {})
        intent_phase = current.get("intent_phase", {})
        intent = intent_phase.get("intent", "hotel_list")
        entities = intent_phase.get("entities", {})
        filtered_entities = self.helpers_state.filter_entities(entities)

        self.publish_action(
            state,
            transition="proceed_to_hotel_search",
            node_id="hotel_search",
            service="hotel_search",
            action="search_hotels",
            parameters={
                "filled_slots": filtered_entities},
            flow_id=f"{intent.split('_')[0]}_flow"
        )
        return state


    def handle_normalization(self,state: GraphState) -> GraphState:
        """Handle normalization for filled slots"""
        state_dict = state.model_dump()
        current = state_dict["state"].get("current", {})
        intent_phase = current.get("intent_phase", {})
        intent = intent_phase.get("intent", "hotel_list")
        entities = intent_phase.get("entities", {})
        filtered_entities = self.helpers_state.filter_entities(entities)
        raw_parameters = entities = intent_phase.get("entities", {})

        if intent == Intent.SERPAPI.value:
            transition = "proceed_to_serpapi"
            node_id = "request_normalization"
            service = "normalization_service"
            action = "serpapi_search"
            request_type = "serpapi"
            parameters = {
                "request_type": request_type,
                "search_parameters": filtered_entities
            }

        else:
            transition = "proceed_to_normalization"
            node_id = "request_normalization"
            service = "normalization_service"
            action = "check_and_normalize"
            request_type = "hotel_search"
            parameters = {
                "request_type": request_type,
                "raw_parameters": raw_parameters
            }

            if entities.get("NumberOfPeople", "") == "":
                entities["NumberOfPeople"] = 2
            if entities.get("NumberOfRooms", "") == "":
                entities["NumberOfRooms"] = 1

        new_state = GraphState.model_validate(state_dict)
        self.publish_action(
            state,
            transition=transition,
            node_id=node_id,
            service=service,
            action=action,
            parameters=parameters,
            flow_id=f"{intent.split('_')[0]}_flow"
        )
        return new_state

    def handle_rejection(self, state: GraphState) -> GraphState:
        """Handle rejection strategy"""
        state_dict = state.model_dump()
        current = state_dict["state"].get("current", {})
        intent_phase = current.get("intent_phase", {})
        entities = intent_phase.get("entities", {})

        filtered_entities = self.helpers_state.filter_entities(entities)

        new_state = GraphState.model_validate(state_dict)
        self.publish_action(
            state,
            transition="refill_after_rejection",
            node_id="slot_filling",
            service="chat_agent",
            action="collect_slot",
            parameters={
                "filled_slots": filtered_entities,
                "slots_to_collect": self.helpers_state.get_slots_to_collect(intent="hotel_list", entities=filtered_entities),
                "note": "User rejected. Ask which part was wrong."
            },
            flow_id="hotel_list_flow"
        )

        return new_state


    def handle_fallback(self, state: GraphState) -> GraphState:
        """Handle fallback strategy"""
        state_dict = state.model_dump()
        current = state_dict["state"].get("current", {})
        intent_phase = current.get("intent_phase", {})
        intent = intent_phase.get("intent", "")
        user_input = current.get("user_input", {})

        new_state = GraphState.model_validate(state_dict)
        if intent == 'greetings':
            self.publish_action(
                state,
                transition="proceed_to_greeting",
                node_id="handle_fallback",
                service="chat_agent",
                action="handle_fallback",
                parameters={
                    "user_input": user_input
                },
                flow_id="fallback_flow"
            )

        else:
            self.publish_action(
                state,
                transition="proceed_to_out_of_scope",
                node_id="handle_fallback",
                service="chat_agent",
                action="handle_fallback",
                parameters={
                    "user_input": user_input
                },
                flow_id="fallback_flow"
            )

        return new_state


