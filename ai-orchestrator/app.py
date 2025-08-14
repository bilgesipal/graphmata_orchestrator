# Trademark (c) 2025 Prometa AI.
# This file is part of the GraphMata project.


import signal
import sys

from fastapi import FastAPI

from src.config.config import AppConfig
from src.api.routers.health_router import router as health_router
from src.api.routers.test_process_router import router as test_process_router
from src.api.routers.agents import router as agents_router
from src.api.routers.task_status import router as task_status_router
from src.shadows.shadow_agents_runtime.agent_supervisors import (
    stop_background_threads,
    lifespan,
)



def signal_handler(signum, frame):
    print(f"Received signal {signum}, initiating graceful shutdown...")
    stop_background_threads()
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

app = FastAPI(
    title=f"{AppConfig.SERVICE_NAME} Trigger API",
    description="Service that triggers intent processing for hotel booking queries",
    version="1.0.4",
    lifespan=lifespan
)


app.include_router(health_router, prefix="/health")
app.include_router(test_process_router, prefix="/test-process")
app.include_router(agents_router, prefix="/agents")
app.include_router(task_status_router, prefix="/task-status")




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8100,
        timeout_keep_alive=1800,
        access_log=True,
        log_level="info"
   )