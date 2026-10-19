import re

from sqlalchemy import or_, select
from app.core.database import SessionLocal
from app.repositories.models import Chunk, Document


_STOPWORDS = {
    "que", "cual", "cuales", "como", "cuando", "donde", "para", "por",
    "con", "sin", "sobre", "entre", "del", "desde", "hasta", "una", "uno",
    "unas", "unos", "las", "los", "les", "este", "esta", "estos", "estas",
    "eso", "esa", "ese", "son", "ser", "es", "hay", "sirven", "sirve",
    "puede", "pueden", "hacer", "sus", "cada", "más", "menos",
}


def _search_terms(query_text: str | None) -> list[str]:
    if not query_text:
        return []
    return [
        term
        for term in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", query_text.casefold())
        if len(term) >= 4 and term not in _STOPWORDS
    ]


def vector_search(
    query_vector: list[float],
    owner_id: str,
    top_k: int = 4,
    query_text: str | None = None,
) -> list[dict]:
    with SessionLocal() as db:
        # 1 - distancia_coseno = score de similitud (0 a 1)
        score_label = (1 - Chunk.embedding.cosine_distance(query_vector)).label("score")
        owner_filter = Chunk.owner_id.in_(["global", owner_id])

        stmt = (
            select(Chunk, Document.filename, score_label)
            .join(Document, Chunk.document_id == Document.id)
            .where(owner_filter, Document.status == "ready")
            .order_by(Chunk.embedding.cosine_distance(query_vector))
            .limit(top_k)
        )

        results_by_id = {
            row.Chunk.id: {
                "text": row.Chunk.text,
                "page": row.Chunk.page,
                "document": row.filename,
                "score": float(row.score),
            }
            for row in db.execute(stmt).all()
        }

        # Complementa la similitud vectorial con coincidencias de términos
        # específicos. Es importante para títulos, nombres propios y conceptos
        # breves que pueden quedar por debajo del umbral semántico.
        terms = _search_terms(query_text)
        if terms:
            lexical_filters = [
                Chunk.text.ilike(f"%{term}%")
                for term in dict.fromkeys(terms)
            ]
            lexical_stmt = (
                select(Chunk, Document.filename)
                .join(Document, Chunk.document_id == Document.id)
                .where(
                    owner_filter,
                    Document.status == "ready",
                    or_(*lexical_filters),
                )
                .limit(top_k)
            )

            for row in db.execute(lexical_stmt).all():
                if row.Chunk.id in results_by_id:
                    continue
                matched_terms = sum(
                    term in row.Chunk.text.casefold()
                    for term in dict.fromkeys(terms)
                )
                results_by_id[row.Chunk.id] = {
                    "text": row.Chunk.text,
                    "page": row.Chunk.page,
                    "document": row.filename,
                    # Permite que el juez evalúe el contexto, pero no
                    # convierte una coincidencia textual en certeza semántica.
                    "score": min(0.60, 0.52 + (matched_terms * 0.02)),
                }

        return sorted(
            results_by_id.values(),
            key=lambda chunk: chunk["score"],
            reverse=True,
        )[: max(top_k * 2, 4)]