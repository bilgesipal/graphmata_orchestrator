import json
from typing import Dict, Any, List
from datetime import datetime

from langgraph.graph import StateGraph, START, END

from src.api.schemas.schemas import GraphState
from src.config.config import AppConfig
from src.redis_connect.connect import RedisConnections
from src.shadows.shadow_agents.intent_shadow_agent.handle_nodes import IntentHandlerNodes
from src.shadows.shadow_util.intent_util.intent_util import StateHelper, CacheChecker
from src.shadows.shadow_util.intent_util.intent_util import Intent, Route


class ShadowIntentAgent:

    def __init__(self):
        self.redis_conn = RedisConnections(host=AppConfig.REDIS_HOST, port=AppConfig.REDIS_PORT)
        self.agent = "intent_agent"
        self.redis_client = self.redis_conn.get_redis_client()
        self.pubsub = self.redis_conn.get_redis_pubsub()

        self.handle_func = IntentHandlerNodes(self.redis_conn, self.redis_client, self.agent)

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(GraphState)

        builder.add_node("check_intent_and_branch", self.route_intent)
        builder.add_node("handle_slot_filling", self.handle_func.handle_slot_filling)
        builder.add_node("handle_normalization", self.handle_func.handle_normalization)
        builder.add_node("handle_search", self.handle_func.handle_search)
        builder.add_node("handle_rejection", self.handle_func.handle_rejection)
        builder.add_node("handle_fallback", self.handle_func.handle_fallback)

        def route_condition(state):
            state_dict = state if isinstance(state, dict) else state.model_dump()
            route = state_dict.get("route", "fallback")
            intent = state_dict['trace_info'].get("flow", "")

            print(f"route_condition received route: {route}")

            route_mapping = {
                Route.SLOT_FILLING.value: "handle_slot_filling",
                Route.NORMALIZATION.value: "handle_normalization",
                Route.REJECTION.value: "handle_rejection",
                Route.SEARCH.value: "handle_search",
                Route.CACHE_CHECK.value: "handle_slot_filling"
            }

            return route_mapping.get(route, "handle_fallback")

        builder.add_conditional_edges(
            "check_intent_and_branch",
            route_condition
        )

        builder.add_edge("handle_slot_filling", END)
        builder.add_edge("handle_normalization", END)
        builder.add_edge("handle_search", END)

        builder.add_edge("handle_rejection", END)
        builder.add_edge("handle_fallback", END)
        builder.set_entry_point("check_intent_and_branch")

        return builder.compile()

    def _determine_comparison_route(self, state_dict: Dict[str, Any], entities: Dict[str, Any]) -> str:
        if entities.get("postQuery", []):
            if CacheChecker.get_cache_count(state_dict, "price_policy") == 2:
                return Route.CACHE_CHECK.value
            else:
                return Route.SEARCH.value

        general_cache_count = CacheChecker.get_cache_count(state_dict, "general_info")
        price_cache_count = CacheChecker.get_cache_count(state_dict, "price_policy")

        if general_cache_count == 2 and price_cache_count == 2:
            return Route.CACHE_CHECK.value
        elif general_cache_count == 2:
            return Route.CACHE_CHECK.value
        else:
            return Route.NORMALIZATION.value

    def _determine_ask_route(self, state_dict: Dict[str, Any], entities: Dict[str, Any]) -> str:
        post_query = entities.get("postQuery", [])

        if "price" in post_query:
            if CacheChecker.has_cache_data(state_dict, "price_policy"):
                return Route.CACHE_CHECK.value
            else:
                return Route.SEARCH.value

        if (CacheChecker.has_cache_data(state_dict, "general_info") and
                CacheChecker.has_cache_data(state_dict, "price_policy")):
            return Route.CACHE_CHECK.value
        elif CacheChecker.has_cache_data(state_dict, "general_info"):
            return Route.CACHE_CHECK.value
        else:
            return Route.NORMALIZATION.value

    def _handle_serpapi_intent(self, entities: Dict[str, Any], filled_entities: Dict[str, Any]) -> str:
        print(f"[DEBUG SERPAPI] Original entities: {entities}")
        print(f"[DEBUG SERPAPI] Filled entities: {filled_entities}")

        has_minimum = StateHelper.has_minimum_slots_for_search(Intent.SERPAPI.value, filled_entities)
        print(f"[DEBUG SERPAPI] Has minimum slots check: {has_minimum}")

        if has_minimum:
            route = Route.NORMALIZATION.value
            print(f"[DEBUG SERPAPI] Route set to normalization")
        else:
            route = Route.SLOT_FILLING.value
            print(f"[DEBUG SERPAPI] Route set to slot_filling")

        return route

    def route_intent(self, state: GraphState) -> GraphState:
        """Route based on intent classification"""
        state_dict = state.model_dump()
        current = state_dict["state"].get("current", {})
        intent_phase = current.get("intent_phase", {})
        intent = intent_phase.get("intent")
        transition = state_dict["state"].get("transition", "")
        user_input = current.get("user_input", {})
        if user_input and "text" in user_input:
            print(f"route_intent processing: {user_input['text']}")

        state_dict["trace_info"]["sequence"] = int(state_dict["trace_info"]["sequence"]) + 1
        state_dict["metadata"]["source_service"] = "orchestrator"
        state_dict["message_id"] = state_dict["message_id"]
        state_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"


        entities = intent_phase.get("entities", {})
        filled_entities = {k: v for k, v in entities.items() if v not in (None, "", "LLM_outputText")}
        route = 'fallback'

        if intent == Intent.REJECTION.value:
            route = Route.REJECTION.value
        elif intent == Intent.GREETINGS.value:
            route = Route.FALLBACK.value
        elif intent == Intent.HOTEL_LIST.value:
            if StateHelper.has_minimum_slots_for_search(intent, filled_entities):
                route = Route.NORMALIZATION.value
            else:
                route = Route.SLOT_FILLING.value
        elif intent == Intent.HOTEL_SIMILAR.value:
            route = Route.SEARCH.value
        elif intent in [Intent.HOTEL_DETAIL.value, Intent.HOTEL_DETAIL_FOLLOWUP.value,
                        Intent.HOTEL_ROOM_COMPARISON.value]:
            if StateHelper.has_minimum_slots_for_search(intent, filled_entities):
                route = Route.NORMALIZATION.value
            else:
                route = Route.SLOT_FILLING.value
        elif intent in [Intent.HOTEL_COMPARISON.value, Intent.HOTEL_COMPARISON_FOLLOWUP.value]:
            if StateHelper.has_minimum_slots_for_search(intent, filled_entities):
                route = self._determine_comparison_route(state_dict, entities)
            else:
                route = Route.SLOT_FILLING.value
        elif intent in [Intent.HOTEL_COMPARISON.value, Intent.HOTEL_COMPARISON_FOLLOWUP.value]:
                if StateHelper.has_minimum_slots_for_search(intent, filled_entities):
                    route = self._determine_comparison_route(state_dict, entities)
                else:
                    route = Route.SLOT_FILLING.value
        elif intent in [Intent.HOTEL_ASK.value, Intent.HOTEL_ASK_FOLLOWUP.value]:
            if StateHelper.has_minimum_slots_for_search(intent, filled_entities):
                route = self._determine_ask_route(state_dict, entities)
            else:
                route = Route.SLOT_FILLING.value
        elif intent == Intent.SERPAPI.value:
            route = self._handle_serpapi_intent(entities, filled_entities)
        elif intent == Intent.HOTEL_LIST_NEXT.value:
            redis_pp, redis_gen, chosen_hotels = self.redis_conn.handle_search_agent(state_dict)
            if chosen_hotels:
                state_dict["metadata"]["redis_cache_address_price_policy"] = redis_pp
                state_dict["metadata"]["redis_cache_address_general_info"] = redis_gen
                state_dict["chosen_hotels"] = chosen_hotels
                route = Route.CACHE_CHECK.value
            else:
                route = Route.SEARCH.value
        elif intent == Intent.OUT_OF_SCOPE.value:
            route = Route.FALLBACK.value

        print(f"route_intent: {intent}, route: {route}")
        state_dict["route"] = route

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
                "input": json_str[:100] + "..." if len(json_str) > 100 else json_str
            }
