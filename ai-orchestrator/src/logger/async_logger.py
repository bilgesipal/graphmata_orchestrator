# import os
# import json
# import asyncio
# from datetime import datetime
# from typing import Dict, List, Optional, Any
# import redis.asyncio as aioredis
# from src.config.config import AppConfig
#
#
# class SimpleLogger:
#     """Simple logger that works in both sync and async contexts"""
#
#     def __init__(self, source: str, channel_name: str = "service_logs"):
#         self.source = source
#         self.channel_name = channel_name
#         self.instance_id = f"{os.getenv('K_REVISION', 'local')}-{os.getpid()}"
#         self._logs: List[Dict[str, Any]] = []
#
#     def log(self, level: str, message: str, context: Optional[Dict[str, Any]] = None):
#         """Add log to buffer (works in sync/async)"""
#         self._logs.append({
#             "timestamp": datetime.utcnow().isoformat(),
#             "level": level.upper(),
#             "source": self.source,
#             "message": message,
#             "context": context or {},
#             "instance_id": self.instance_id,
#             "env": AppConfig.ENVIRONMENT,
#             "module": AppConfig.SERVICE_NAME,
#         })
#
#     def info(self, message: str, context: Optional[Dict[str, Any]] = None):
#         self.log("INFO", message, context)
#
#     def error(self, message: str, context: Optional[Dict[str, Any]] = None):
#         self.log("ERROR", message, context)
#
#     def publish(self):
#         """Publish logs (automatically detects sync/async context)"""
#         if not self._logs:
#             return
#
#         try:
#             loop = asyncio.get_running_loop()
#             loop.create_task(self._async_publish())
#         except RuntimeError:
#             asyncio.run(self._async_publish())
#
#     async def _async_publish(self):
#         """Internal async publish method"""
#         if not self._logs:
#             return
#
#         redis = aioredis.Redis(
#             host=AppConfig.REDIS_HOST,
#             port=AppConfig.REDIS_PORT,
#             decode_responses=True
#         )
#
#         try:
#             payload = {
#                 "channel": self.channel_name,
#                 "messages": self._logs.copy(),
#                 "timestamp": datetime.utcnow().isoformat(),
#                 "batch_size": len(self._logs),
#                 "source": self.source
#             }
#
#             await redis.publish(self.channel_name, json.dumps(payload))
#             print(f"[{self.source.upper()}] Published {len(self._logs)} logs")
#
#         except Exception as e:
#             print(f"[{self.source.upper()}] Publish failed: {e}", flush=True)
#         finally:
#             await redis.close()
#             self._logs.clear()
