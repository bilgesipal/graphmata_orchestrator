from typing import Optional
from fastapi import FastAPI
from contextlib import asynccontextmanager
from threading import Thread, Event

from src.shadows.shadow_agents_runtime.agent_loop import run_chat_agent, run_intent_agent, run_normalizer_agent, run_search_agent

chat_thread: Optional[Thread] = None
intent_thread: Optional[Thread] = None
normalizer_thread: Optional[Thread] = None
search_thread: Optional[Thread] = None
shutdown_event = Event()


def safe_thread_runner(target_func, thread_name: str):
    """Wrapper function to run agents with error handling and restart capability."""
    while not shutdown_event.is_set():
        try:
            print(f"[{thread_name}] Starting agent...")
            target_func()
        except Exception as e:
            print(f"[{thread_name}] Agent crashed: {e}")
            if not shutdown_event.is_set():
                print(f"[{thread_name}] Restarting in 5 seconds...")
                shutdown_event.wait(5)  # Wait 5 seconds before restart
        else:
            print(f"[{thread_name}] Agent completed normally")
            break


def start_background_threads():
    """Start all background agent shadow_agents_runtime."""
    global chat_thread, intent_thread, normalizer_thread

    print("[Startup] Starting background agent shadow_agents_runtime...")

    chat_thread = Thread(
        target=safe_thread_runner,
        args=(run_chat_agent, "ChatAgent"),
        daemon=False,
        name="ChatAgentThread"
    )

    intent_thread = Thread(
        target=safe_thread_runner,
        args=(run_intent_agent, "IntentAgent"),
        daemon=False,
        name="IntentAgentThread"
    )

    normalizer_thread = Thread(
        target=safe_thread_runner,
        args=(run_normalizer_agent, "NormalizerAgent"),
        daemon=False,
        name="NormalizerAgentThread"
    )

    search_thread = Thread(
        target=safe_thread_runner,
        args=(run_search_agent, "SearchAgent"),
        daemon=False,
        name="SearchAgentThread"
    )

    chat_thread.start()
    intent_thread.start()
    normalizer_thread.start()
    search_thread.start()

    print(f"[Startup] All agent shadow_agents_runtime started successfully")


def stop_background_threads():
    """Gracefully stop all background shadow_agents_runtime."""
    global chat_thread, intent_thread, normalizer_thread, search_thread

    print("[Shutdown] Stopping background shadow_agents_runtime...")
    shutdown_event.set()
    threads = [chat_thread, intent_thread, normalizer_thread, search_thread]
    for thread in threads:
        if thread and thread.is_alive():
            print(f"[Shutdown] Waiting for {thread.name} to finish...")
            thread.join(timeout=10)  # Give 10 seconds for graceful shutdown
            if thread.is_alive():
                print(f"[Shutdown] {thread.name} did not finish gracefully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    start_background_threads()
    yield
    stop_background_threads()

