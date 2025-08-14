#This file is part of the GraphMata project.
#Trademark (c) 2025 Prometa AI.

import os
#from dotenv import load_dotenv

#load_dotenv()

class AppConfig:

    ENVIRONMENT = os.getenv("ENVIRONMENT", "TEST")
    SERVICE_NAME = os.getenv("SERVICE_NAME", "orchestrator")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    NAMESPACE = os.getenv("NAMESPACE", "GraphMata")

    REDIS_HOST = os.getenv("REDIS_HOST", "testredis02.erkaws.com")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", 15))
    REDIS_LOG = os.getenv("REDIS_LOG", "service-logs")


    REDIS_PUBLISH_CHAT = os.getenv("REDIS_PUBLISH_CHAT", "chat-agent-trigger")
    REDIS_PUBLISH_CONFIRMATION = os.getenv("REDIS_PUBLISH_CONFIRMATION", "chat-agent-trigger")
    REDIS_PUBLISH_NORMALIZER = os.getenv("REDIS_PUBLISH_NORMALIZER", "normalizer-trigger")
    REDIS_PUBLISH_SEARCH = os.getenv("REDIS_PUBLISH_SEARCH", "search-trigger")

    REDIS_LISTEN_INTENT = os.getenv("REDIS_LISTEN_INTENT", "intent-state-update")
    REDIS_LISTEN_CHAT = os.getenv("REDIS_LISTEN_CHAT", "chat-state-update")
    REDIS_LISTEN_NORMALIZER = os.getenv("REDIS_LISTEN_NORMALIZER", "normalizer-update")
    REDIS_LISTEN_SEARCH = os.getenv("REDIS_LISTEN_SEARCH", "search-update")

