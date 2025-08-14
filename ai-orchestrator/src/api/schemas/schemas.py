from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, model_validator


#ttl_config = {
#    "default_ttl": 60,
#    "refresh_on_read": True,
#}

# Pydantic models
class OrchestrationActions(BaseModel):
    service: str
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class Orchestration(BaseModel):
    flow_director: str = "orchestrator"
    flow_id: str
    node_id: str
    actions: OrchestrationActions = Field(default_factory=OrchestrationActions)

class TraceInfo(BaseModel):
    trace_id: int
    flow: str
    flow_type: Optional[str]=None
    sequence: int
    retry_count: int = 0

class UserInput(BaseModel):
    text: str
    language: str = "tr"

class StateTransition(BaseModel):
    current: Dict[str, Any] = Field(default_factory=dict)
    previous_transition: Optional[str] = None
    transition: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def ensure_current_dict(cls, values):
        if not isinstance(values.get("current"), dict):
            values["current"] = {}
        return values


class GraphState(BaseModel):
    session_id: str
    message_id: str
    timestamp: str
    version: str = "1.0.0"
    trace_info: TraceInfo
    metadata: Dict[str, Any]
    state: StateTransition
    system_message: Optional[Dict[str, Any]] = Field(default=None)
    route: Optional[str] = None
    orchestration: Optional[Orchestration] = None

class QueryRequest(BaseModel):
    session_id: str
    message_id: str
    timestamp: str
    version: str = "1.0.0"
    trace_info: TraceInfo
    metadata: Dict[str, Any]
    state: StateTransition
    system_message: Optional[Dict[str, Any]] = Field(default=None)
    route: Optional[str] = None
    orchestration: Optional[Orchestration] = None