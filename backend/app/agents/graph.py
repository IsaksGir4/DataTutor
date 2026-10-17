from langgraph.graph import END, START, StateGraph

from app.agents.nodes.core import (
    clarify,
    classify_intent,
    generate_answer,
    generate_smalltalk,
    grade_context,
    receive,
    refuse,
    retrieve,
    rewrite_query,
    save_history,
)
from app.agents.state import AgentState
from app.config.settings import settings


def route_intent(state: AgentState) -> str:
    if state["intent"] == "smalltalk":
        return "generate_smalltalk"
    if state["intent"] == "out_of_domain":
        return "refuse"
    return "retrieve"


def route_context(state: AgentState) -> str:
    if state["context_ok"]:
        return "generate_answer"
    if state["best_score"] >= settings.SIM_LOW and state["retries"] < 1:
        return "rewrite_query"

    word_count = len(state["question"].strip().split())
    if state["best_score"] >= settings.SIM_LOW and word_count <= 4:
        return "clarify"
    return "refuse"


# Construcción
workflow = StateGraph(AgentState)

# Agregar nodos
workflow.add_node("receive", receive)
workflow.add_node("classify_intent", classify_intent)
workflow.add_node("generate_smalltalk", generate_smalltalk)
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_context", grade_context)
workflow.add_node("rewrite_query", rewrite_query)
workflow.add_node("generate_answer", generate_answer)
workflow.add_node("refuse", refuse)
workflow.add_node("clarify", clarify)
workflow.add_node("save_history", save_history)

# Flujo base
workflow.add_edge(START, "receive")
workflow.add_edge("receive", "classify_intent")

# Bifurcación tras intención
workflow.add_conditional_edges("classify_intent", route_intent)
workflow.add_edge("generate_smalltalk", "save_history")

# Bifurcación tras evaluación de suficiencia
workflow.add_edge("retrieve", "grade_context")
workflow.add_conditional_edges("grade_context", route_context)

# Retornos hacia salida del grafo
workflow.add_edge("rewrite_query", "retrieve")
workflow.add_edge("generate_answer", "save_history")
workflow.add_edge("refuse", "save_history")
workflow.add_edge("clarify", "save_history")
workflow.add_edge("save_history", END)

# Compilar grafo
agent_app = workflow.compile()