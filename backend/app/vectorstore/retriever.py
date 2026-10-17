from sqlalchemy import select
from app.core.database import SessionLocal
from app.repositories.models import Chunk, Document


def vector_search(query_vector: list[float], owner_id: str, top_k: int = 4) -> list[dict]:
    with SessionLocal() as db:
        # 1 - distancia_coseno = score de similitud (0 a 1)
        score_label = (1 - Chunk.embedding.cosine_distance(query_vector)).label("score")

        stmt = (
            select(Chunk, Document.filename, score_label)
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.owner_id.in_(["global", owner_id]))
            .order_by(Chunk.embedding.cosine_distance(query_vector))
            .limit(top_k)
        )

        results = db.execute(stmt).all()

        return [
            {
                "text": row.Chunk.text,
                "page": row.Chunk.page,
                "document": row.filename,
                "score": float(row.score)
            }
            for row in results
        ]