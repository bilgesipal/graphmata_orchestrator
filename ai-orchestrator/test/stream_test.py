import asyncio
import json
import time
from redis.asyncio import Redis
from typing import Dict, Any


class StreamConfig:
    """Configuration for Redis Streams"""

    def __init__(self, stream_name: str, consumer_group: str, consumer_name: str,
                 retention_hours: int = 2, batch_size: int = 10, max_length: int = 100):
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.retention_hours = retention_hours
        self.batch_size = batch_size
        self.max_length = max_length

    def get_trim_timestamp(self) -> str:
        """Get timestamp for trimming messages older than retention_hours"""
        cutoff_time = int(time.time() * 1000) - (self.retention_hours * 60 * 60 * 1000)
        return f"{cutoff_time}-0"


async def send_test_message_to_stream(
        redis_url: str,
        stream_name: str = "gateway",
        session_id: str= "session_160",
        message_id: str= "45",
        message_type: str = "chat"
):


    hotel_chat_content = """- **Melia Berlin**: 24 saat açık resepsiyona sahip bu lüks otel, ücretsiz kablosuz internet ve spor salonu gibi olanaklar sunarken, aynı zamanda Berlin Orkestrası'na ve Bode Müzesi'ne oldukça yakın konumda yer alıyor.

- **Vienna House by Wyndham Andel's Berlin**: Spa ve sağlık merkezi ile donatılmış bu otel, ücretsiz kablosuz internet ve uluslararası mutfakta uzmanlaşmış restoranlarıyla konforlu bir konaklama imkanı sunuyor.

- **NH Collection Berlin Mitte am Checkpoint Charlie**: Checkpoint Charlie'ye sadece birkaç adım mesafede yer alan bu otel, sauna ve spor salonu gibi dinlenme olanaklarıyla birlikte ücretsiz kablosuz internet sunuyor.

- **Novotel Suites Berlin City Potsdamer Platz**: 24 saat açık spor salonu ve teras keyfi sunan bu çevre dostu otel, Checkpoint Charlie ve Friedrichstrasse ile yürüyüş mesafesinde bulunuyor.

- **Mercure Hotel Berlin Zentrum**: Berlin Zoolojik Bahçesi'ne yürüme mesafesinde olan bu otel, ücretsiz kablosuz internet ve hafif yemek büfesi ile misafirlerine konforlu bir konaklama sunuyor.

Daha fazla bilgi veya farklı bir kritere göre (örneğin tarihler, fiyat aralığı, bölge) öneri ister misiniz?"""
    hotel_info_data = [
        {
            "hotel_name": "Melia Berlin",
            "hotel_id": "JP007035",
            "per_night": "689.16 USD",
            "policy": "available",
            "images": [
                "https://i.travelapi.com/lodging/2000000/1350000/1349700/1349646/f59751c6_b.jpg",
                "https://i.travelapi.com/lodging/2000000/1350000/1349700/1349646/2b53b39c_b.jpg",
                "https://i.travelapi.com/lodging/2000000/1350000/1349700/1349646/fb4b51b5_b.jpg"
            ],
            "longitude": "13.388314",
            "latitude": "52.52141",
            "hotel_star": 4,
            "location": "Berlin",
            "review_rate": 4.5,
            "type": "hotel"
        },
        {
            "hotel_name": "Mercure Hotel Berlin Zentrum",
            "hotel_id": "JP760586",
            "per_night": "504.3 USD",
            "policy": "available",
            "images": [
                "https://i.travelapi.com/lodging/1000000/30000/28600/28589/36961cdf_b.jpg",
                "https://i.travelapi.com/lodging/1000000/30000/28600/28589/d97e7400_b.jpg",
                "https://i.travelapi.com/lodging/1000000/30000/28600/28589/84b56647_b.jpg"
            ],
            "longitude": "13.34805",
            "latitude": "52.49913",
            "hotel_star": 3,
            "location": "Berlin",
            "review_rate": 4.0,
            "type": "hotel"
        },
        {
            "hotel_name": "Novotel Suites Berlin City Potsdamer Platz",
            "hotel_id": "JP156343",
            "per_night": "572.55 USD",
            "policy": "available",
            "images": [
                "https://i.travelapi.com/lodging/2000000/1120000/1119000/1118997/dfad6153_b.jpg",
                "https://i.travelapi.com/lodging/2000000/1120000/1119000/1118997/b33bd367_b.jpg",
                "https://i.travelapi.com/lodging/2000000/1120000/1119000/1118997/9bc7c4f9_b.jpg"
            ],
            "longitude": "13.38278",
            "latitude": "52.50463",
            "hotel_star": 3,
            "location": "Berlin",
            "review_rate": 4.1,
            "type": "hotel"
        },
        {
            "hotel_name": "Vienna House by Wyndham Andel's Berlin",
            "hotel_id": "JP007023",
            "per_night": "463.12 USD",
            "policy": "available",
            "images": [
                "https://i.travelapi.com/lodging/3000000/2360000/2350300/2350257/f2b02869_b.jpg",
                "https://i.travelapi.com/lodging/3000000/2360000/2350300/2350257/e9eaf610_b.jpg",
                "https://i.travelapi.com/lodging/3000000/2360000/2350300/2350257/ade7f70b_b.jpg"
            ],
            "longitude": "13.457397",
            "latitude": "52.528637",
            "hotel_star": 4,
            "location": "Berlin",
            "review_rate": 4.3,
            "type": "hotel"
        },
        {
            "hotel_name": "NH Collection Berlin Mitte am Checkpoint Charlie",
            "hotel_id": "JP110685",
            "per_night": "524.15 USD",
            "policy": "available",
            "images": [
                "https://i.travelapi.com/lodging/1000000/520000/517200/517191/8ef20a90_b.jpg",
                "https://i.travelapi.com/lodging/1000000/520000/517200/517191/0dd85297_b.jpg",
                "https://i.travelapi.com/lodging/1000000/520000/517200/517191/3dcce7a8_b.jpg"
            ],
            "longitude": "13.3891",
            "latitude": "52.51035",
            "hotel_star": 4,
            "location": "Berlin",
            "review_rate": 4.3,
            "type": "hotel"
        }
    ]

    redis_client = None

    try:
        redis_client = Redis.from_url(redis_url, decode_responses=True)
        print(f"Connected to Redis at {redis_url}")
        test_messages = []
        chat_message = {
            "session_id": session_id,
            "message_id": message_id,
            "response": "chat",
            "type": "chat_response",
            "chat": hotel_chat_content,
            "hotel_info": hotel_info_data,
            "timestamp": int(time.time()),
            "end": "false"
        }
        test_messages.append(("Chat Message with Hotel Info", chat_message))
        hotel_message = {
            "session_id": session_id,
            "message_id": message_id,
            "response": "hotel_list",
            "type": "hotel_results",
            "hotels": hotel_info_data,
            "location": "Berlin",
            "total_hotels": len(hotel_info_data),
            "timestamp": int(time.time()),
            "end": "false"
        }
        test_messages.append(("Hotel List Message", hotel_message))
        end_message = {
            "session_id": session_id,
            "message_id": message_id,
            "response": "end",
            "type": "completion",
            "content": "Conversation completed",
            "timestamp": int(time.time()),
            "end": "true"
        }
        test_messages.append(("End Message", end_message))
        for message_name, message_data in test_messages:
            try:

                payload = json.dumps(message_data)
                message_id_result = await redis_client.xadd(
                    stream_name,
                    fields={
                        "data": payload,
                        "timestamp": int(time.time()),
                        "message_type": message_type,
                        "session_id": session_id,
                        "message_id": message_id,
                    }
                )

                print(f"{message_name} sent successfully!")
                print(f"   Stream: {stream_name}")
                print(f"   Message ID: {message_id_result}")
                print(f"   Payload preview: {payload[:100]}...")
                print("-" * 50)
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f" Failed to send {message_name}: {e}")
        try:
            stream_info = await redis_client.xinfo_stream(stream_name)
            print(f" Stream '{stream_name}' info:")
            print(f"   Length: {stream_info.get('length', 'N/A')}")
            print(f"   Groups: {stream_info.get('groups', 'N/A')}")
            print(
                f"   Last entry ID: {stream_info.get('last-entry', ['N/A'])[0] if stream_info.get('last-entry') else 'N/A'}")
        except Exception as e:
            print(f" Could not get stream info: {e}")

    except Exception as e:
        print(f"Redis connection error: {e}")
    finally:
        if redis_client:
            await redis_client.close()
            print("Redis connection closed")


async def send_custom_message_to_stream(
        redis_url: str,
        stream_name: str,
        custom_payload: Dict[str, Any],
        session_id: str = None,
        message_id: str = None
):


    redis_client = None

    try:
        redis_client = Redis.from_url(redis_url, decode_responses=True)
        if session_id:
            custom_payload["session_id"] = session_id
        if message_id:
            custom_payload["message_id"] = message_id

        custom_payload.setdefault("timestamp", int(time.time()))
        payload = json.dumps(custom_payload)
        result_id = await redis_client.xadd(
            stream_name,
            fields={
                "payload": payload,
                "timestamp": int(time.time()),
            }
        )

        print(f" Custom message sent successfully!")
        print(f"   Stream: {stream_name}")
        print(f"   Message ID: {result_id}")
        print(f"   Payload: {json.dumps(custom_payload, indent=2)}")

    except Exception as e:
        print(f"Failed to send custom message: {e}")
    finally:
        if redis_client:
            await redis_client.close()

async def run_basic_test():
    """Run basic test with default Redis URL"""
    redis_url = "redis://testredis02.erkaws.com:6379/15"
    print("Running basic test with Redis URL:", redis_url)





    await send_test_message_to_stream(redis_url)

#
# async def send_berlin_hotels_test():
#     """Send Berlin hotels message in the exact format you provided"""
#     redis_url = "redis://testredis02.erkaws.com:6379/15"
#
#     berlin_message = {
#         "session_id": "berlin_session_123",
#         "message_id": "berlin_message_456",
#         "response": "chat",
#         "chat": "- **Melia Berlin**: 24 saat açık resepsiyona sahip bu lüks otel, ücretsiz kablosuz internet ve spor salonu gibi olanaklar sunarken, aynı zamanda Berlin Orkestrası'na ve Bode Müzesi'ne oldukça yakın konumda yer alıyor.\n\n- **Vienna House by Wyndham Andel's Berlin**: Spa ve sağlık merkezi ile donatılmış bu otel, ücretsiz kablosuz internet ve uluslararası mutfakta uzmanlaşmış restoranlarıyla konforlu bir konaklama imkanı sunuyor.\n\n- **NH Collection Berlin Mitte am Checkpoint Charlie**: Checkpoint Charlie'ye sadece birkaç adım mesafede yer alan bu otel, sauna ve spor salonu gibi dinlenme olanaklarıyla birlikte ücretsiz kablosuz internet sunuyor.\n\n- **Novotel Suites Berlin City Potsdamer Platz**: 24 saat açık spor salonu ve teras keyfi sunan bu çevre dostu otel, Checkpoint Charlie ve Friedrichstrasse ile yürüyüş mesafesinde bulunuyor.\n\n- **Mercure Hotel Berlin Zentrum**: Berlin Zoolojik Bahçesi'ne yürüme mesafesinde olan bu otel, ücretsiz kablosuz internet ve hafif yemek büfesi ile misafirlerine konforlu bir konaklama sunuyor.\n\nDaha fazla bilgi veya farklı bir kritere göre (örneğin tarihler, fiyat aralığı, bölge) öneri ister misiniz?",
#         "hotel_info": [
#             {
#                 "hotel_name": "Melia Berlin",
#                 "hotel_id": "JP007035",
#                 "per_night": "689.16 USD",
#                 "policy": "available",
#                 "images": [
#                     "https://i.travelapi.com/lodging/2000000/1350000/1349700/1349646/f59751c6_b.jpg",
#                     "https://i.travelapi.com/lodging/2000000/1350000/1349700/1349646/2b53b39c_b.jpg",
#                     "https://i.travelapi.com/lodging/2000000/1350000/1349700/1349646/fb4b51b5_b.jpg"
#                 ],
#                 "longitude": "13.388314",
#                 "latitude": "52.52141",
#                 "hotel_star": 4,
#                 "location": "Berlin",
#                 "review_rate": 4.5,
#                 "type": "hotel"
#             },
#             {
#                 "hotel_name": "Mercure Hotel Berlin Zentrum",
#                 "hotel_id": "JP760586",
#                 "per_night": "504.3 USD",
#                 "policy": "available",
#                 "images": [
#                     "https://i.travelapi.com/lodging/1000000/30000/28600/28589/36961cdf_b.jpg",
#                     "https://i.travelapi.com/lodging/1000000/30000/28600/28589/d97e7400_b.jpg",
#                     "https://i.travelapi.com/lodging/1000000/30000/28600/28589/84b56647_b.jpg"
#                 ],
#                 "longitude": "13.34805",
#                 "latitude": "52.49913",
#                 "hotel_star": 3,
#                 "location": "Berlin",
#                 "review_rate": 4.0,
#                 "type": "hotel"
#             }
#         ],
#         "end": "false"
#     }
#
#     await send_custom_message_to_stream(
#         redis_url=redis_url,
#         stream_name="gateway",
#         custom_payload=berlin_message
#     )


if __name__ == "__main__":
    asyncio.run(run_basic_test())
