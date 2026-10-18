from langchain_ollama import ChatOllama
from app.config.settings import settings


def get_chat_model(temperature: float = 0.0, format_type: str = "") -> ChatOllama:
    # Si format_type es "json", Ollama forzará que la salida sea un JSON válido.
    kwargs = {
        "model": settings.CHAT_MODEL,
        "base_url": settings.OLLAMA_URL,
        "temperature": temperature,
        "num_ctx": settings.NUM_CTX,
        "num_predict": settings.NUM_PREDICT,
    }
    if format_type:
        kwargs["format"] = format_type

    return ChatOllama(**kwargs)