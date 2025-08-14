import json
import redis
from datetime import datetime
from typing import Dict, Any
from src.config.config import AppConfig
from src.api.schemas.schemas import GraphState

class RedisConnections:
    def __init__(self, host: str = AppConfig.REDIS_HOST, port: int = AppConfig.REDIS_PORT):
        self.host = host
        self.port = port
        self.db = AppConfig.REDIS_DB
        self.redis_client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True
        )

    def get_redis_client(self):
        return self.redis_client

    def get_redis_pubsub(self):
        return self.redis_client.pubsub()

    def set_redis_client(self, client):
        self.redis_client = client

    def cache_state_conv_redis(self, state: GraphState, agent_type: str):
        if isinstance(state, dict):
            state = GraphState.model_validate(state)
        state_dict = state.model_dump()
        session_id = state_dict["session_id"]
        user_id = state_dict.get("metadata", {}).get("user_id", "unknown_user")
        sequence_key = f"prometa_ai:{agent_type}:{session_id}_{user_id}"
        state_json = json.dumps(state_dict, default=str, ensure_ascii=False)
        self.redis_client.set(name=sequence_key, value=state_json, ex=3600)
        print(f"[Redis] Saved state to Redis with key: {sequence_key}")
        redis_key = f"prometa_ai:conversation:{session_id}_{user_id}"
        full_context = self.get_input_to_redis(redis_key=redis_key, state_dict=state_dict, agent_type=agent_type)
        self.redis_client.set(name=redis_key, value=json.dumps(full_context, default=str, ensure_ascii=False), ex=3600)
        print(f"[Redis] Updated conversation:{session_id}_{user_id} with key: {redis_key}")

    def get_input_to_redis(self, redis_key: str, state_dict: dict, agent_type: str):
        full_context = self.get_context(redis_key)
        session_id = state_dict.get("session_id", "unknown_session"),
        user_id = state_dict.get("metadata", {}).get("user_id", "unknown_user"),
        sequence = state_dict.get("trace_info", {}).get("sequence", "unknown_sequence"),
        trace_id = state_dict.get("trace_info", {}).get("trace_id", "unknown_trace"),

        if full_context:
            full_context.update({
                "session_id": session_id[0],
                "user_id": user_id[0],
                "sequence": sequence[0],
                "trace_id": trace_id[0]
            })
        else:
            full_context = {
                "session_id": session_id,
                "user_id": user_id,
                "sequence": sequence,
                "trace_id": trace_id,
                "chat_history": "",
                "user_messages": [],
                "latest_entity": {},
                "error": None
            }

        current = state_dict.get("state", {}).get("current", {})
        try:
            if agent_type == "intent_agent":
                self._handle_intent_agent(full_context, current)
            if agent_type == "chat_agent":
                self._handle_chat_agent(full_context, current, state_dict)
        except Exception as e:
            print(f"[Redis] Error extracting or saving context for {redis_key}: {e}")
            full_context["error"] = str(e)

        return full_context

    def _handle_intent_agent(self, context: dict, current: dict):
        user_text = current.get("user_input", {}).get("text", "")

        intent = current.get("intent_phase", {}).get("intent", "")
        entities = {
            k: v for k, v in current.get("intent_phase", {}).get("entities", {}).items()
            if v not in (None, "")
        }

        if user_text:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "user_messages" not in context:
                context["user_messages"] = []
            if "chat_history" not in context:
                context["chat_history"] = ""

            new_entry = {
                "user": user_text,
                "trace_id": context.get("trace_id", "unknown_trace"),
                "sequence": context.get("sequence", "unknown_sequence"),
                "timestamp": timestamp,
                "intent": intent,
                "entities": {**entities, "intent": intent}
            }

            context["state"] = {
                "current": {
                    "user_input": {
                        "text": user_text
                    }
                }
            }


            context["user_messages"].append(new_entry)
            context["chat_history"] += f"[{timestamp}]User: {user_text}\n"

            context["latest_entity"] = {**entities, "intent": intent}


    def _handle_chat_agent(self, context: dict, current: dict, state_dict: dict):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_msg = state_dict.get("system_message", {}).get("text", "")

        if system_msg:
            if not isinstance(context["chat_history"], str):
                context["chat_history"] = ""

            context["chat_history"] += f"{timestamp} System: {system_msg}\n"
            #print(f"[Redis] System message added to chat_history: '{system_msg}'")

            if "system_messages" not in context:
                context["system_messages"] = []

            context["system_messages"].append({
                "system": system_msg,
                "timestamp": timestamp
            })

    def get_rank_hotels(self):
        r = self.get_redis_client()
        keys = r.keys("prometa:HotelSearch:*")
        hotel_names = [key.replace("prometa:HotelSearch:", "") for key in keys]
        price_pol = [name for name in hotel_names if name.startswith("Price")]
        hotel = [name for name in hotel_names if not name.startswith("Price")]
        return hotel, price_pol

    def handle_search_agent(self, state_dict: dict):
        redis = self.get_redis_client() if hasattr(self, "get_redis_client") else self.redis_client
        session_id = state_dict.get("session_id", "unknown_session")
        user_id = state_dict.get("metadata", {}).get("user_id", "unknown_user")
        batch_size = 5
        source_key = f"prometa:HotelSearch:Price:{user_id}:{session_id}"
        ranked_key = f"{source_key}:ranked_list"
        print('DBG: _handle_search_agent')
        print('DBG: current:', state_dict.get("metadata"))
        intent =  state_dict.get("trace_info", {}).get("flow","")

        if "hotel_list" == intent:
            metadata = state_dict.get("metadata", {})
            hotel_list = metadata.get("redis_cache_address_price_policy", [])
            print('DBG: hotel_list:', hotel_list)
            pipe = redis.pipeline()

            for hotel in hotel_list:
                pipe.get(hotel)
            values = pipe.execute()

            hotels = []
            for v in values:
                data = json.loads(v)
                name =  data.get("name")
                price_str = str(data.get("price", "")).strip()
                price = float(price_str.split()[0].replace(",", "."))
                hotels.append({"name": name, "price": price, "sent": False})

            hotels.sort(key=lambda hotel: (hotel["price"], hotel["name"]))
            print('DBG: sorted:', hotels)

            batch = []
            batch_general=[]
            chosen_name = []
            for hotel in hotels:
                if not hotel["sent"] and len(batch) < batch_size:
                    hotel["sent"] = True
                    batch.append(source_key+":" + hotel["name"])
                    batch_general.append(f"prometa:HotelSearch:"+ hotel["name"])
                    chosen_name.append(hotel["name"])

            redis.set(ranked_key, json.dumps({"hotels": hotels}, ensure_ascii=False), ex=300)
            print("DBG: hotels:", batch)
            print("DBG: batch_general:", batch_general)
            print("DBG: chosen_name:", chosen_name)
            return batch, batch_general, chosen_name

        elif intent == "hotel_list_next":
            print('DBG: hotel_list_next')
            blob = redis.get(ranked_key)
            payload = json.loads(blob)
            hotels = payload.get("hotels", [])

            batch = []
            batch_general=[]
            chosen_name = []
            for hotel in hotels:
                if not hotel.get("sent", False):
                    hotel["sent"] = True
                    batch.append(source_key + ":" + hotel["name"])
                    batch_general.append(f"prometa:HotelSearch:" + hotel["name"])
                    chosen_name.append(hotel["name"])
                    if len(batch) >= batch_size:
                        break
            print("DBG: hotels:", batch)
            print("DBG: batch_general:", batch_general)
            print("DBG: chosen_name:", chosen_name)

            redis.set(ranked_key, json.dumps({"hotels": hotels}, ensure_ascii=False), ex=300)

            return batch, batch_general, chosen_name

        else:
            return [],[],[]


    def get_context(self, redis_key: str) -> Dict[str, Any]:
        existing = self.redis_client.get(redis_key)
        if existing:
            try:
                return json.loads(existing)
            except json.JSONDecodeError:
                print(f"[Redis] Corrupted JSON in key: {redis_key}")
                return {}
        else:
            print(f"[Redis] No context found for {redis_key}")
            return {}

    def publish_redis(self, channel: str, message: Any):
        print(f"[Redis] Publishing to channel: {channel}")
        if isinstance(message, dict):
            message = json.dumps(message, ensure_ascii=False)
        self.redis_client.publish(channel, message)
        #print(f"[Redis] Published message to channel: {channel}")
        #print(f"[Redis] Message content: {message}")

    def subscribe(self, channel: str):
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(channel)
        print(f"[Redis] Subscribed to channel: {channel}")
