# GraphMata

GraphMata is an orchestration service for managing agent-based interactions via Redis pub/sub. It provides an infrastructure for coordinating various agents like chat, intent, normalization, search, and confirmation agents in a distributed system.

## Tech Stack

- **Backend**: Python 3.11, FastAPI
- **Agent Framework**: LangChain, LangGraph
- **Messaging**: Redis (Pub/Sub)
- **Deployment**: Docker, Google Cloud Run
- **Dependencies Management**: pip-tools
- **Documentation**: FastAPI auto-generated docs (sphinx TODO: next version)

## Folder Structure

```
graph_mata/
├── app.py                 # Main application entry point
├── requirements.in        # Primary dependencies (used by pip-tools)
├── Dockerfile             # Docker configuration
├── cloudbuild.yaml        # Google Cloud Build configuration
└── src/                   # Source code
    ├── agents_runtime/    # Agent execution and supervisor logic
    │   ├── __init__.py
    │   ├── agent_loop.py      # Core agent execution loop
    │   └── agent_supervisors.py  # Manages agent lifecycles
    ├── config/            # Configuration and environment settings
    │   ├── __init__.py
    │   └── config.py      # Environment variables and app configuration
    ├── logger/            # Logging functionality
    │   ├── __init__.py
    │   └── async_logger.py    # Asynchronous logging utilities
    ├── redis_connect/     # Redis connection utilities
    │   ├── __init__.py
    │   └── connect.py     # Redis client connection management
    ├── routers/           # FastAPI route definitions
    │   ├── __init__.py
    │   ├── agents.py      # Agent triggering endpoints
    │   ├── health_router.py   # Health check endpoints
    │   ├── task_status.py     # Task status monitoring endpoints
    │   └── test_process_router.py  # Test endpoints
    ├── schemas/           # Data models and validation
    │   ├── __init__.py
    │   └── schemas.py     # Pydantic models for request/response validation
    └── shadow_agents/     # Agent implementations
        ├── __init__.py
        ├── chat_shadow_agent.py     # Chat processing agent
        ├── intent_shadow_agent.py   # Intent classification agent
        ├── normalizer_shadow_agent.py  # Data normalization agent
        └── search_shadow_agent.py   # Search functionality agent
```

## Installation Instructions

### Prerequisites
- Python 3.11+
- Redis server
- Git

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/graph_mata.git
   cd graph_mata
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install pip-tools
   pip-compile requirements.in
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the root directory with the following variables:
   ```
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_LOG=service-logs
   
   REDIS_PUBLISH_CHAT=chat-agent-trigger
   REDIS_PUBLISH_CONFIRMATION=confirmation-trigger
   REDIS_PUBLISH_NORMALIZER=normalizer-trigger
   REDIS_PUBLISH_SEARCH=search-trigger
   
   REDIS_LISTEN_INTENT=intent-state-update
   REDIS_LISTEN_CHAT=chat-state-update
   REDIS_LISTEN_CONFIRMATION=confirmation-update
   REDIS_LISTEN_NORMALIZER=normalizer-update
   REDIS_LISTEN_SEARCH=search-update
   
   OPENAI=your_openai_api_key
   ```

5. **Run the application**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8080 --reload
   ```

### Docker Setup

1. **Build the Docker image**
   ```bash
   docker build -t graph_mata .
   ```

2. **Run the container**
   ```bash
   docker run -p 8080:8080 --env-file .env graph_mata
   ```

## Usage & API Examples

### Health Check
```bash
curl -X GET http://localhost:8080/health
```
Response:
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### Triggering an Agent
```bash
curl -X POST http://localhost:8080/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "12345",
    "message": "I need help with booking a hotel"
  }'
```
Response:
```json
{
  "task_id": "12345",
  "status": "processing"
}
```

### Checking Task Status
```bash
curl -X GET http://localhost:8080/task-status/12345
```
Response:
```json
{
  "task_id": "12345",
  "status": "completed",
  "result": {
    "response": "I found some hotel options for you..."
  }
}
```

## Endpoints Documentation

### Health Routes
- `GET /health` - Check service health

### Agent Routes
- `POST /agents/chat` - Trigger chat agent
  - Body: `{ "task_id": string, "message": string }`
  - Response: `{ "task_id": string, "status": string }`

- `POST /agents/intent` - Trigger intent agent
  - Body: `{ "task_id": string, "message": string }`
  - Response: `{ "task_id": string, "status": string }`

### Task Status Routes
- `GET /task-status/{task_id}` - Get task status
  - Response: `{ "task_id": string, "status": string, "result": object }`

### Test Process Routes
- `POST /test-process` - Test processing endpoint
  - Body: `{ "message": string }`
  - Response: `{ "status": string, "message": string }`

## Running Tests

To run the test suite:

```bash
pytest
```

For running mock tests:

```bash
python -m mock_test.mock_chat_test
```

## Project Architecture

GraphMata uses a microservice architecture with event-driven communication between components:

1. **Main Application (FastAPI)**: Handles HTTP requests and manages agent lifecycles
2. **Agent Supervisors**: Manages background threads for listening agents
3. **Shadow Agents**: Implementation of each agent's functionality
4. **Redis Pub/Sub**: Message passing between agents
5. **LangGraph**: Orchestrates the flow of information between agents

The system follows a loosely coupled design where each agent operates independently but communicates through standardized message formats via Redis channels.

## Flow Diagram

Below is a simplified flow diagram showing how data moves through the GraphMata system:

```
                                  ┌─────────────────────────────┐
                                  │                             │
                                  │      FastAPI Server         │
                                  │   (Health & Status Checks)  │
                                  │                             │
                                  └─────────────────┬───────────┘
                                                    │
                                                    ▼
                                  ┌─────────────────────────────┐
                                  │                             │
                                  │    Agent Supervisors        │
                                  │                             │
                                  └───┬─────────┬─────────┬─────┘
                                      │         │         │
         ┌───────────────────────────┐│         │         │┌──────────────────────────┐
         │                            ▼         │         ▼│                          │
┌────────▼─────────┐         ┌────────────────┐ │ ┌────────────────┐         ┌───────▼──────────┐
│                  │         │                │ │ │                │         │                  │
│   Chat Agent     │         │  Intent Agent  │ │ │ Normalizer     │         │  Search Agent    │
│   Thread         │         │  Thread        │ │ │ Agent Thread   │         │  Thread          │
│                  │         │                │ │ │                │         │                  │
└─────────┬────────┘         └────────┬───────┘ │ └────────┬───────┘         └──────────┬──────┘
          │                           │         │          │                            │
          ▼                           ▼         ▼          ▼                            ▼
  ┌───────────────┐            ┌───────────────┐   ┌───────────────┐            ┌───────────────┐
  │ LISTEN:       │            │ LISTEN:       │   │ LISTEN:       │            │ LISTEN:       │
  │ chat-state-   │            │ intent-state- │   │ normalizer-   │            │ search-       │
  │ update        │            │ update        │   │ update        │            │ update        │
  └───────┬───────┘            └───────┬───────┘   └───────┬───────┘            └───────┬───────┘
          │                            │                   │                            │
          │                            │                   │                            │
          ▼                            ▼                   ▼                            ▼
  ┌───────────────┐            ┌───────────────┐   ┌───────────────┐            ┌───────────────┐
  │ PUBLISH:      │            │ PUBLISH:      │   │ PUBLISH:      │            │ PUBLISH:      │
  │ chat-agent-   │            │ confirmation- │   │ normalizer-   │            │ search-       │
  │ trigger       │            │ trigger       │   │ trigger       │            │ trigger       │
  └───────────────┘            └───────────────┘   └───────────────┘            └───────────────┘
          │                            │                   │                            │
          │                            │                   │                            │
          ▼                            ▼                   ▼                            ▼
     ┌─────────────────────────────────────────────────────────────────────────────────┐
     │                                                                                 │
     │                              Redis Pub/Sub                                      │
     │                                                                                 │
     └─────────────────────────────────────────────────────────────────────────────────┘
```

### System Flow

1. **Initialization**: 
   - FastAPI server starts up and initializes agent supervisor threads in `agent_supervisors.py`
   - Each agent supervisor launches listening threads for different agents:
     - Chat agent via `chat_shadow_agent.py`
     - Intent agent via `intent_shadow_agent.py`
     - Normalizer agent via `normalizer_shadow_agent.py`
     - Search agent via `search_shadow_agent.py`
   - Each agent starts listening on its dedicated Redis channel:
     - `chat-state-update`
     - `intent-state-update`
     - `normalizer-update`
     - `search-update`
     - `confirmation-update`

2. **Event Processing**:
   - Each agent subscribes to its designated channel in Redis
   - When a message appears on a channel, the listening agent processes it
   - Each agent publishes results to another channel to trigger the next agent
   - The `agent_loop.py` handles the core processing logic for each agent type

3. **Communication Flow Example**:
   - Message published to `chat-agent-trigger`
   - Chat agent processes and publishes to `intent-state-update`
   - Intent agent receives, processes, and publishes to `search-trigger`
   - Search agent processes and publishes to `normalizer-trigger`
   - Normalizer agent processes and publishes to `confirmation-update`
   - Each step happens asynchronously in background threads

4. **Status Monitoring**:
   - API endpoints in `task_status.py` can check process status
   - If an agent thread stalls, endpoints in `agents.py` can be used to retrigger them

This architecture allows for fully decoupled, event-driven processing with each agent operating independently in its own thread, responding to events as they occur in the Redis messaging system.


## License

Copyright © 2025 Prometa AI. All rights reserved.

This is proprietary software. Unauthorized copying or distribution is prohibited.
