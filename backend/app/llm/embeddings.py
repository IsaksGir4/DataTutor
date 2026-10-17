from langchain_ollama import OllamaEmbeddings
from app.config.settings import settings

def get_embeddings_model() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.EMBED_MODEL,
        base_url=settings.OLLAMA_URL
    )