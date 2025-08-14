import os
import json
import traceback

from src.config.config import AppConfig
from src.shadows.shadow_agents.intent_shadow_agent.intent_shadow_agent import ShadowIntentAgent
from src.shadows.shadow_agents.chat_shadow_agent.chat_shadow_agent import ShadowChatAgent
from src.shadows.shadow_agents.normalizer_shadow_agent.normalizer_shadow_agent import ShadowNormalizerAgent
from src.shadows.shadow_agents.hotel_search_shadow_agent.hotel_search_shadow_agent import ShadowHotelSearchAgent


def run_agent(agent_name: str, agent_instance, redis_channel: str):
    instance_id = f"{os.getenv('K_REVISION', 'local')}-{os.getpid()}"
    print(f"[{agent_name.upper()}] Starting on instance: {instance_id}")
    print(f"[{agent_name.upper()}] Subscribing to Redis channel: {redis_channel}")

    pubsub = agent_instance.pubsub
    pubsub.subscribe(redis_channel)

    try:
        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                payload = json.loads(data)

                session_id = payload.get("session_id", "unknown")
                message_id = payload.get("message_id", "unknown")
                process_key = f"processing:{agent_name}:{session_id}:{message_id}"

                lock_acquired = agent_instance.redis_client.set(process_key, instance_id, nx=True, ex=30)
                if not lock_acquired:
                    existing_processor = agent_instance.redis_client.get(process_key)
                    print("DBG: existing_processor:" , existing_processor)
                    processor_name = existing_processor.decode() if existing_processor else "unknown"
                    print(f"[{agent_name.upper()}] Message {session_id}:{message_id} already being processed by: {processor_name}")
                    continue

                try:
                    #print(f"[{agent_name.upper()}] {instance_id} processing {session_id}:{message_id}")
                    result = agent_instance.handle_message(json.dumps(payload))
                    #print(f"[{agent_name.upper()}] Output:", json.dumps(result, indent=2, ensure_ascii=False))
                finally:
                    agent_instance.redis_client.delete(process_key)

            except json.JSONDecodeError as e:
                print(f"[{agent_name.upper()}] JSON decode error: {e}")
                #print(f"Raw message: {str(message['data'])[:200]}...")
            except Exception as e:
                print(f"[{agent_name.upper()}] Processing error: {e}")
                traceback.print_exc()

    except KeyboardInterrupt:
        print(f"[{agent_name.upper()}] Shutdown requested.")
    finally:
        pubsub.unsubscribe(redis_channel)
        pubsub.close()
        print(f"[{agent_name.upper()}] Cleaned up.")


def run_intent_agent():
    run_agent("intent", ShadowIntentAgent(), AppConfig.REDIS_LISTEN_INTENT)

def run_chat_agent():
    print("[CHAT AGENT] Starting chat agent...")
    run_agent("chat", ShadowChatAgent(), AppConfig.REDIS_LISTEN_CHAT)

def run_normalizer_agent():
    run_agent("normalizer", ShadowNormalizerAgent(), AppConfig.REDIS_LISTEN_NORMALIZER)

def run_search_agent():
    run_agent("search", ShadowHotelSearchAgent(), AppConfig.REDIS_LISTEN_SEARCH)