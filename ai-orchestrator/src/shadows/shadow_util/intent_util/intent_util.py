
import json
from typing import Dict, Any, List
from datetime import datetime
from enum import Enum

from src.api.schemas.schemas import GraphState

class Route(Enum):
    """Enum for routing decisions"""
    SLOT_FILLING = "slot_filling"
    NORMALIZATION = "normalization"
    SEARCH = "search"
    REJECTION = "rejection"
    FALLBACK = "fallback"
    CACHE_CHECK = "cache_check"


class Intent(Enum):
    """Enum for intent types"""
    REJECTION = "rejection"
    GREETINGS = "greetings"
    HOTEL_LIST = "hotel_list"
    HOTEL_SIMILAR = "hotel_similar"
    HOTEL_DETAIL = "hotel_detail"
    HOTEL_DETAIL_FOLLOWUP = "hotel_detail_followup"
    HOTEL_ROOM_COMPARISON = "hotel_room_comparison"
    HOTEL_COMPARISON = "hotel_comparison"
    HOTEL_COMPARISON_FOLLOWUP = "hotel_comparison_followup"
    HOTEL_ASK = "hotel_ask"
    HOTEL_ASK_FOLLOWUP = "hotel_ask_followup"
    SERPAPI = "serpapi"
    HOTEL_LIST_NEXT = "hotel_list_next"
    OUT_OF_SCOPE = "out_of_scope"


class Service(Enum):
    """Enum for service types"""
    HOTEL_SEARCH = "hotel_search"
    NORMALIZATION_SERVICE = "normalization_service"
    CHAT_AGENT = "chat_agent"


class RequiredSlots:
    """Configuration for required slots per intent"""
    INTENT_REQUIREMENTS = {
        Intent.HOTEL_LIST.value: ["location"],
        Intent.HOTEL_COMPARISON.value: ["location", "hotelNameQuery"],
        Intent.HOTEL_COMPARISON_FOLLOWUP.value: ["location", "hotelNameQuery"],
        Intent.HOTEL_DETAIL.value: ["checkinDate", "checkoutDate", "location", "hotelNameQuery", "NumberOfPeople",
                                    "NumberOfRooms"],
        Intent.HOTEL_DETAIL_FOLLOWUP.value: ["checkinDate", "checkoutDate", "location", "hotelNameQuery",
                                             "NumberOfPeople", "NumberOfRooms"],
        Intent.HOTEL_ASK.value: ["hotelNameQuery"],
        Intent.HOTEL_ASK_FOLLOWUP.value: ["hotelNameQuery"],
        Intent.SERPAPI.value: ["location", "poi"],  # Special case: OR condition
    }


class StateHelper:
    """Helper class for state manipulation"""

    @staticmethod
    def extract_state_components(state: GraphState) -> Dict[str, Any]:
        """Extract commonly used state components"""
        state_dict = state.model_dump() if hasattr(state, 'model_dump') else state
        current = state_dict["state"].get("current", {})
        intent_phase = current.get("intent_phase", {})

        return {
            'state_dict': state_dict,
            'current': current,
            'intent_phase': intent_phase,
            'intent': intent_phase.get("intent", ""),
            'entities': intent_phase.get("entities", {}),
            'user_input': current.get("user_input", {}),
            'transition': state_dict["state"].get("transition", "")
        }

    @staticmethod
    def filter_entities(entities: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out empty or invalid entities"""
        return {k: v for k, v in entities.items() if v not in (None, "", "LLM_outputText")}

    @staticmethod
    def update_trace_info(state_dict: Dict[str, Any]) -> None:
        """Update trace information in state"""
        state_dict["trace_info"]["sequence"] = int(state_dict["trace_info"]["sequence"]) + 1
        state_dict["metadata"]["source_service"] = "orchestrator"
        state_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def has_minimum_slots_for_search(intent: str, entities: Dict[str, Any]) -> bool:
        """Check if minimum required slots are filled"""
        if intent == Intent.SERPAPI.value:
            # Accept if either poi OR location is provided (and non-empty)
            return bool(entities.get("poi")) or bool(entities.get("location"))

        required = RequiredSlots.INTENT_REQUIREMENTS.get(intent, [])
        return all(ent in entities and entities[ent] not in (None, "", "LLM_outputText")
                   for ent in required)

    @staticmethod
    def get_slots_to_collect(self, intent: str, entities: Dict[str, Any]) -> List[str]:
        """Get required slots based on intent"""
        required = RequiredSlots.INTENT_REQUIREMENTS.get(intent, [])
        return [ent for ent in required if ent not in entities]


class CacheChecker:
    """Helper class for cache-related operations"""

    @staticmethod
    def has_cache_data(state_dict: Dict[str, Any], cache_type: str) -> bool:
        """Check if cache data exists"""
        cache_key = f"redis_cache_address_{cache_type}"
        return bool(state_dict.get("metadata", {}).get(cache_key, []))

    @staticmethod
    def get_cache_count(state_dict: Dict[str, Any], cache_type: str) -> int:
        """Get cache data count"""
        cache_key = f"redis_cache_address_{cache_type}"
        return len(state_dict.get("metadata", {}).get(cache_key, []))

