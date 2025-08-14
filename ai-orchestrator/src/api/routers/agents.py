from fastapi import APIRouter, Request, status

from src.shadows.shadow_agents_runtime.agent_supervisors import (
    stop_background_threads,
    start_background_threads,
    shutdown_event,
)


router = APIRouter(tags=["Agents"])


@router.get("/restart-agents")
def restart_agents():
    """Manually restart all agent shadow_agents_runtime."""
    print("Manual restart requested via API")
    stop_background_threads()
    shutdown_event.clear()
    start_background_threads()
    return {"message": "All agents restarted successfully"}


@router.get("/agents-health")
def agents_health():
    """Health check for agent shadow_agents_runtime."""
    global chat_thread, intent_thread, normalizer_thread

    all_healthy = all([
        chat_thread and chat_thread.is_alive(),
        intent_thread and intent_thread.is_alive(),
        normalizer_thread and normalizer_thread.is_alive()
    ])

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "agents": {
            "chat_agent_healthy": chat_thread is not None and chat_thread.is_alive(),
            "intent_agent_healthy": intent_thread is not None and intent_thread.is_alive(),
            "normalizer_agent_healthy": normalizer_thread is not None and normalizer_thread.is_alive()
        }
    }
