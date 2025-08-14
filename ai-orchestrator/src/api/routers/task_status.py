
import asyncio
import logging
import signal
import sys
from typing import Optional
from fastapi import FastAPI
from contextlib import asynccontextmanager
from threading import Thread, Event
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Request, status

from src.shadows.shadow_agents_runtime.agent_supervisors import (
    shutdown_event,
)


router = APIRouter(tags=["Task Status"])


@router.get("/task-status")
def task_status():
    """Get the status of all background agent shadow_agents_runtime."""
    global chat_thread, intent_thread, normalizer_thread

    return {
        "shutdown_requested": shutdown_event.is_set(),
        "chat_agent": {
            "running": chat_thread is not None and chat_thread.is_alive(),
            "thread_name": chat_thread.name if chat_thread else None,
            "thread_id": chat_thread.ident if chat_thread else None
        },
        "intent_agent": {
            "running": intent_thread is not None and intent_thread.is_alive(),
            "thread_name": intent_thread.name if intent_thread else None,
            "thread_id": intent_thread.ident if intent_thread else None
        },
        "normalizer_agent": {
            "running": normalizer_thread is not None and normalizer_thread.is_alive(),
            "thread_name": normalizer_thread.name if normalizer_thread else None,
            "thread_id": normalizer_thread.ident if normalizer_thread else None
        }
    }
