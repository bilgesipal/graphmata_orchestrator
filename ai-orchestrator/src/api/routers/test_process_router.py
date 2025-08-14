
import json
import redis.asyncio as aioredis
from fastapi import HTTPException, Response, APIRouter
from src.api.schemas.schemas import QueryRequest
from src.config.config import AppConfig

router = APIRouter(tags=["Check Process"])

REDIS_URL = f"redis://{AppConfig.REDIS_HOST}:{AppConfig.REDIS_PORT}"

@router.post("/process_query",
             summary="Streamlit Querry Processing for Entities and Intent"
             )
async def test_process(
        payload: QueryRequest,
        channel:str,
        response: Response
                        ):
    """
    Trigger intent processing with user input. Results will be published
    to Redis PubSub, not returned in the response.
    """
    message_json = json.dumps(QueryRequest)
    redis_client = aioredis.Redis.from_url(REDIS_URL, decode_responses=True)

    if not message_json:
        print("Missing user_input in request")
        raise HTTPException(status_code=400, detail="user_input is required")
    try:

        result = await  redis_client.publish(channel, message_json)

    except Exception as e:
        print(f"Error in background processing: {str(e)}")

    return {
     "message1" : f"Published message to channel {channel}" ,
     "message2": f"Delivery count: {result}",
     "message": "processing triggered"
    }
