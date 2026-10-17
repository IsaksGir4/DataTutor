from langchain_ollama import ChatOllama
from app.config.settings import settings


def get_chat_model(temperature: float = 0.0, format_type: str = "") -> ChatOllama:
    # Si format_type es "json", Ollama forzará que la salida sea un JSON válido.
    kwargs = {
        "model": "qwen2.5:3b",  # Hardcodeado por ahora según lineamientos
        "base_url": settings.OLLAMA_URL,
        "temperature": temperature,
        "num_ctx": 4096,
        "num_predict": 512
    }
    if format_type:
        kwargs["format"] = format_type

    return ChatOllama(**kwargs)