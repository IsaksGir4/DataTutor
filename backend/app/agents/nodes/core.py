import json

import logging
import re
import unicodedata

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts import (
    ANSWER_PROMPT,
    GRADER_PROMPT,
    INTENT_PROMPT,
    REWRITE_PROMPT,
)
from app.agents.state import AgentState
from app.config.settings import settings
from app.llm.chat import get_chat_model
from app.llm.embeddings import get_embeddings_model
from app.vectorstore.retriever import vector_search

logger = logging.getLogger(__name__)

_GENERIC_TERMS = {
    "base", "bases", "dato", "datos",
    "sistema", "sistemas", "informacion",
    "pregunta", "contexto", "documento", "documentos",
    "tema", "proceso", "procesos",
}

_STOPWORDS = {
    "que", "cual", "cuales", "como", "cuando", "donde",
    "para", "por", "con", "sin", "sobre", "entre",
    "del", "desde", "hasta", "una", "uno", "unas", "unos",
    "las", "los", "les", "este", "esta", "estos", "estas",
    "eso", "esa", "ese", "son", "ser", "es", "hay",
    "sirven", "sirve", "puede", "pueden", "hacer",
    "para", "por", "sus", "cada", "más", "menos",
}


def _normalized_tokens(text: str) -> set[str]:
    """Normaliza texto para comparar términos sin diferencias de tildes."""
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(
        char
        for char in normalized
        if not unicodedata.combining(char)
    )
    return set(re.findall(r"[a-z0-9]+", normalized))


def _has_direct_lexical_evidence(
    question: str,
    retrieved: list[dict],
) -> bool:
    """
    Respaldo conservador: exige coincidencias entre términos específicos
    de la pregunta y el texto recuperado.
    """
    question_terms = {
        token
        for token in _normalized_tokens(question)
        if len(token) >= 5
        and token not in _STOPWORDS
        and token not in _GENERIC_TERMS
    }

    # Una sola palabra específica puede ser suficiente cuando la pregunta
    # está formada por términos genéricos, por ejemplo "ciencia de datos".
    if len(question_terms) < 2:
        if not question_terms:
            return False
        context_terms: set[str] = set()
        for chunk in retrieved:
            context_terms.update(_normalized_tokens(chunk.get("text", "")))
        return next(iter(question_terms)) in context_terms

    context_terms: set[str] = set()

    for chunk in retrieved:
        context_terms.update(
            _normalized_tokens(chunk.get("text", ""))
        )

    matches = question_terms.intersection(context_terms)

    return (
        len(matches) >= 2
        and len(matches) / len(question_terms) >= 0.35
    )


def receive(state: AgentState) -> dict:
    # Inicializa variables para la corrida
    return {"retries": 0, "query": state["question"], "context_ok": False}


def classify_intent(state: AgentState) -> dict:
    llm_json = get_chat_model(format_type="json")
    msg = llm_json.invoke([
        SystemMessage(content=INTENT_PROMPT),
        HumanMessage(content=state["question"]),
    ])
    try:
        res = json.loads(msg.content)
        return {"intent": res.get("intent", "explain")}
    except Exception:
        return {"intent": "explain"}  # Ante la duda, intentamos recuperar


def retrieve(state: AgentState) -> dict:
    embed_model = get_embeddings_model()
    vector = embed_model.embed_query(state["query"])

    chunks = vector_search(
        vector,
        state["owner_id"],
        top_k=settings.TOP_K,
        query_text=state["query"],
    )
    best_score = chunks[0]["score"] if chunks else 0.0

    return {"retrieved": chunks, "best_score": best_score}


def grade_context(state: AgentState) -> dict:
    best_score = state["best_score"]

    if best_score < settings.SIM_LOW:
        return {"context_ok": False}

    # La evidencia textual directa no debe depender de otra llamada al LLM.
    # Esto evita falsos rechazos cuando el juez devuelve JSON incorrecto o
    # cuando un concepto del PDF tiene baja similitud semántica.
    has_direct_evidence = _has_direct_lexical_evidence(
        state["question"],
        state["retrieved"],
    )
    if has_direct_evidence:
        logger.info(
            "Contexto aceptado por evidencia léxica directa: score=%.3f",
            best_score,
        )
        return {"context_ok": True}

    # En el primer intento se exige SIM_THRESHOLD para consultar al juez.
    # Tras reescribir, el juez puede evaluar resultados desde SIM_LOW.
    should_run_judge = (
        best_score >= settings.SIM_THRESHOLD
        or state["retries"] >= 1
    )

    if not should_run_judge:
        return {"context_ok": False}

    llm_json = get_chat_model(format_type="json")
    context_str = "\n".join(
        f"- {chunk['text']}"
        for chunk in state["retrieved"]
    )

    msg = llm_json.invoke([
        SystemMessage(content=GRADER_PROMPT),
        HumanMessage(
            content=(
                f"Pregunta: {state['question']}\n\n"
                f"Contexto:\n{context_str}"
            )
        ),
    ])

    sufficient = None

    try:
        result = json.loads(msg.content)
        candidate = result.get("sufficient")

        # Solo aceptamos el booleano JSON real.
        if isinstance(candidate, bool):
            sufficient = candidate
        else:
            logger.warning(
                "El juez devolvió un campo 'sufficient' no booleano."
            )

    except (json.JSONDecodeError, TypeError, AttributeError):
        logger.warning(
            "No se pudo interpretar la respuesta JSON del juez."
        )

    # El juez confirmó que el contexto es suficiente.
    if sufficient is True:
        return {"context_ok": True}

    # Respaldo para falsos negativos y respuestas mal formadas:
    # solo con score alto y evidencia léxica directa.
    if best_score >= settings.SIM_LOW and has_direct_evidence:
        logger.warning(
            "Se acepta el contexto por respaldo léxico: "
            "score=%.3f; el juez no lo declaró suficiente.",
            best_score,
        )
        return {"context_ok": True}

    return {"context_ok": False}

def rewrite_query(state: AgentState) -> dict:
    llm = get_chat_model()
    msg = llm.invoke([
        SystemMessage(content=REWRITE_PROMPT),
        HumanMessage(content=state["question"]),
    ])
    return {"query": msg.content.strip(), "retries": state["retries"] + 1}


def generate_answer(state: AgentState) -> dict:
    llm = get_chat_model(temperature=0.1)

    # Formatear el contexto con índices para las citas
    context_str = ""
    sources_list = []
    for idx, c in enumerate(state["retrieved"], 1):
        context_str += f"\n[Documento {idx}]: {c['text']}\n"
        sources_list.append({
            "document": c["document"],
            "page": c["page"],
            "snippet": c["text"][:100] + "...",
            "score": c["score"],
        })

    msg = llm.invoke([
        SystemMessage(content=ANSWER_PROMPT.format(context=context_str)),
        HumanMessage(content=state["question"]),
    ])
    return {
        "answer": msg.content,
        "decision": "answered",
        "sources": sources_list,
    }


def refuse(state: AgentState) -> dict:
    msg = (
        "No tengo suficiente información en mi base de conocimiento para responder esa pregunta. "
        "Te sugiero cargar documentos relacionados con el tema."
    )
    return {"answer": msg, "decision": "rejected", "sources": []}


def clarify(state: AgentState) -> dict:
    msg = (
        "He encontrado información parcial sobre este tema, pero tu pregunta es un poco ambigua. "
        "¿Podrías ser más específico(a)?"
    )
    return {"answer": msg, "decision": "clarify", "sources": []}


def generate_smalltalk(state: AgentState) -> dict:
    return {
        "answer": (
            "¡Hola! Soy DataTutor. Estoy aquí para ayudarte con temas de ingeniería, "
            "datos y programación. ¿En qué te ayudo?"
        ),
        "decision": "smalltalk",
        "sources": [],
    }


def save_history(state: AgentState) -> dict:
    # La persistencia transaccional se realiza en services/chat.py
    return {}