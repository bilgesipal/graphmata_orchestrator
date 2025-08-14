import json
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Request, status
from src.config.config import AppConfig
import redis.asyncio as aioredis

router = APIRouter(tags=["Health"])

redis_client = aioredis.Redis(host=AppConfig.REDIS_HOST, port=AppConfig.REDIS_PORT)


@router.get("/api/v1/healthcheck/pubsub")
async def get_redis_pubsub():
    try:
        payload = {"state": {"save": "true", "dump": "false"}}
        await redis_client.publish("health-test", json.dumps(payload))
        return {"status": "published", "payload": payload}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )



@router.get("/")
def root(request: Request):
    app_info = f"{request.app.title}:{request.app.version}"
    return f"{app_info}"

@router.get("/api/v1/healthcheck",
            summary="Health Check Endpoint",
            description="This is the health endpoint, you can check the health of the services with it.",
            )
def healthcheck():
    return {"status": "ok"}


@router.get("/api/v1/healthcheck/redis_conn",
            summary="Health Check Endpoint",
            description="This is the health endpoint, you can check the health of the services with it.",
            )
async def get_redis_client():
    try:
        await redis_client.ping()
        return {"status": "connected"}
    except Exception as e:
        return {"error": str(e)}

@router.get(
    "/api/v1/healthcheck/ready/keys",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def health_ready_keys():

    return {
            "status": "ok",
            "redis_host": AppConfig.REDIS_HOST,
            "redis_port": AppConfig.REDIS_PORT,
        }
