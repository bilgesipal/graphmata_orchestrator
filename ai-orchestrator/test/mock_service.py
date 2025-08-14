
import asyncio
import json

from src.config.config import AppConfig
from src.utilities.utilities import get_redis_client



async def simulate_publish_chat(channel):
    message = {
  "end": "True",
  "user_id": "prometa@bizigo.com",
  "session_id": "f5b4d8b5-09d3-48d2-b8ec-2b93af77617b",
  "sequence": 10,
  "trace_id": 5,
  "message_id": "26fd0dea-c25e-4d13-96c0-9c5dbadd91c7",
  "response": "chat",
  "chat": "\"**The Mercer** {hotel_data: {\"zone\": \"New York\", \"lat\": 40.758229, \"long\": -73.974529, \"images\": [\"https://i.travelapi.com/lodging/1000000/10000/4900/4818/099ce97e_b.jpg\", \"https://i.travelapi.com/lodging/1000000/10000/4900/4818/13c522a8_b.jpg\", \"https://i.travelapi.com/lodging/1000000/10000/4900/4818/fceacb55_b.jpg\"], \"stars\": 4, \"type\": \"Hotel\"}} oteli, lüks konaklama imkanı ve spa ile sağlık merkezi gibi olanaklarıyla New York'un kalbinde yer alıyor.\\n\\n\" \n\"**Washington Square Hotel** {hotel_data: {\"zone\": \"New York\", \"lat\": 40.766518, \"long\": -73.97825, \"images\": [null, \"https://i.travelapi.com/lodging/1000000/540000/534200/534143/2e595753_b.jpg\", \"https://i.travelapi.com/lodging/1000000/540000/534200/534143/1f831592_b.jpg\"], \"stars\": 4, \"type\": \"Hotel\"}}; aile dostu yapısıyla, Washington Square Parkı ve 5. Cadde'ye yakınlığı ile dikkat çekiyor.\\n\\n\" \n\"**Thompson Central Park New York, by Hyatt** {hotel_data: {\"zone\": \"New York\", \"lat\": 40.756384, \"long\": -73.972087, \"images\": [\"https://i.travelapi.com/lodging/1000000/10000/5600/5550/f1eaafa7_b.jpg\", \"https://i.travelapi.com/lodging/1000000/10000/5600/5550/5cddc76d_b.jpg\", \"https://i.travelapi.com/lodging/1000000/10000/5600/5550/13e85421_b.jpg\"], \"stars\": 4, \"type\": \"Hotel\"}}; Central Park ve Carnegie Hall'a sadece 5 dakika yürüme mesafesinde olup, şık bir restoran sunuyor.\\n\\n\" \n\"**Lotte New York Palace** {hotel_data: {\"zone\": \"New York\", \"lat\": 40.687544, \"long\": -73.982564, \"images\": [\"https://i.travelapi.com/lodging/10000000/9310000/9303600/9303573/d4bbdf2e_b.jpg\", \"https://i.travelapi.com/lodging/10000000/9310000/9303600/9303573/79085d57_b.jpg\", \"https://i.travelapi.com/lodging/10000000/9310000/9303600/9303573/ef17f07b_b.jpg\"], \"stars\": 3, \"type\": \"Hotel\"}} oteli, 5. Cadde'ye yakın konumu ve sunduğu spa olanakları ile konforlu bir konaklama deneyimi sunuyor.\\n\\n\" \n\"**JW Marriott Essex House New York** {hotel_data: {\"zone\": \"New York\", \"lat\": 40.764079, \"long\": -73.978618, \"images\": [\"https://i.travelapi.com/lodging/22000000/21430000/21429600/21429545/bab4bc53_b.jpg\", \"https://i.travelapi.com/lodging/22000000/21430000/21429600/21429545/8e11e83b_b.jpg\", \"https://i.travelapi.com/lodging/22000000/21430000/21429600/21429545/38003d4d_b.jpg\"], \"stars\": 4, \"type\": \"Hotel\"}}; Central Park'ın hemen yanında yer alarak, lüks bir konaklama sunmakta ve misafirlerine spor salonu imkanı vermektedir.\\n\\n\" \n\"Daha fazla bilgi almak veya farklı bir kritere göre (örneğin tarihler, fiyat aralığı, bölge) öneri ister misiniz?\"",
  "system_message": ""
}
    redis_client = await get_redis_client()

    await redis_client.publish(channel, json.dumps(message))
    print(f"Message published to Redis channel {channel}")


async def simulate_publish_hotels(channel):
    message3 ={"end": "False",
               "response": "hotel_list",
               "URL": "/Hotel/list",
               "user_id": "prometa@bizigo.com",
               "session_id": "session_1200",
               "message_id": "21",
               "sequence": 6,
               "trace_id": 3,
               "payload": {"inPolicy": "false",
                           "id": "JPD034928",
                           "checkinDate": "2025-08-02",
                           "checkoutDate": "2025-08-07",
                           "travelUsageType": "corporate",
                           "hotelCodes": ["JP973564", "JP991978", "JP002618", "JP266578", "JP921212", "JP133823", "JP324404", "JP03791Y", "JP002638", "JP02691Q", "JP219380", "JP885058", "JP606157", "JP106688", "JP487301", "JP785020", "JP979254", "JP149878", "JP819069", "JP150978", "JP250991", "JP764393", "JP02906J", "JP06392K", "JP002504", "JP06744K"],
                           "rooms": [{"id": 0,
                                      "customerIds": ["1BB01C081BDC1C971BBB1FDB1C1E1F4C", "1B8F1B6E1C601C8C"],
                                      "passengerCount": 2}]}
               }




    redis_client = await get_redis_client()

    await redis_client.publish(channel, json.dumps(message3))
    print(f"Message published to Redis channel {channel}")

if __name__ == "__main__":
    channel = "gateway"
    async def run_sequence():
        await simulate_publish_hotels(channel)
        await asyncio.sleep(0.05)
        await simulate_publish_chat(channel)
    asyncio.run(run_sequence())


