from typing import TypedDict, List, Optional, Any


class Source(TypedDict):
    document: str
    page: int
    snippet: str
    score: float


class AgentState(TypedDict):
    question: str
    owner_id: str
    conversation_id: Optional[str]
    history: List[dict]

    # Variables internas del flujo
    intent: str  # 'explain', 'exercise', 'smalltalk', 'out_of_domain'
    query: str
    retrieved: List[dict]
    best_score: float
    context_ok: bool
    retries: int

    # Salidas
    answer: str
    sources: List[Source]
    decision: str  # 'answered', 'rejected', 'clarify', 'smalltalk'
    latency_ms: int