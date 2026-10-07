# MODELO DE DATOS — PostgreSQL + pgvector

Base de datos relacional y vectorial. ORM: `SQLAlchemy 2.0` con la extensión `pgvector`. Acceso **solo** a través de repositorios (`repositories/`); ningún servicio ni controlador usa la sesión de base de datos directamente.

Aquí aprovechamos las claves foráneas (`ON DELETE CASCADE`) para garantizar la integridad entre documentos, fragmentos (chunks) e historial de conversaciones.

## Esquema Relacional (Tablas)

### `documents`

Almacena los metadatos de los archivos procesados.

- `id`: UUID (Primary Key)
- `owner_id`: String (sub de Keycloak | 'global')
- `scope`: String ('user' | 'global')
- `filename`: String
- `title`: String
- `area`: String
- `language`: String ('es' | 'en')
- `sha256`: String
- `size_bytes`: Integer
- `pages`: Integer
- `chunks_count`: Integer
- `status`: String ('pending' | 'processing' | 'ready' | 'failed')
- `error`: String (Nullable)
- `created_at`: DateTime
- `updated_at`: DateTime

**Índices y Restricciones:**

- Restricción única: `UniqueConstraint('owner_id', 'sha256')` para garantizar idempotencia.
- Índice: B-Tree en `(owner_id, created_at DESC)`.

### `chunks`

Almacena los fragmentos de texto y sus representaciones vectoriales.

- `id`: UUID (Primary Key)
- `document_id`: UUID (Foreign Key a `documents.id`, `ON DELETE CASCADE`)
- `owner_id`: String (Desnormalizado para acelerar el filtro por usuario)
- `page`: Integer
- `chunk_index`: Integer
- `text`: Text
- `embedding`: Vector(1024)
- `embed_model`: String ('bge-m3')

**Índices:**

- Índice B-Tree en `(document_id, chunk_index)`.
- Índice B-Tree en `(owner_id)`.
- Índice Vectorial: HNSW usando métrica de distancia coseno (`vector_cosine_ops`) sobre la columna `embedding`.

### `conversations`

- `id`: UUID (Primary Key)
- `owner_id`: String
- `title`: String
- `created_at`: DateTime
- `updated_at`: DateTime

**Índices:** B-Tree en `(owner_id, updated_at DESC)`.

### `messages`

- `id`: UUID (Primary Key)
- `conversation_id`: UUID (Foreign Key a `conversations.id`, `ON DELETE CASCADE`)
- `owner_id`: String
- `role`: String ('user' | 'assistant')
- `content`: Text
- `decision`: String ('answered' | 'rejected' | 'clarify' | 'smalltalk' | Null)
- `sources`: JSONB (Almacena `[{"document_id": "...", "document": "...", "page": 0, "snippet": "...", "score": 0.0}]`)
- `best_score`: Float
- `latency_ms`: Integer
- `created_at`: DateTime

**Índices:** B-Tree en `(conversation_id, created_at)`.

## Índice de Búsqueda Vectorial (pgvector)

Al usar `bge-m3`, el tipo de columna se define estrictamente como `Vector(1024)`. **Cambiar de modelo de embeddings implica alterar la columna y reindexar todo.** Se utilizará un índice HNSW para optimizar la velocidad de recuperación.

## Consulta de recuperación (Patrón SQLAlchemy)

```python
from sqlalchemy import select

# La métrica coseno en pgvector devuelve la *distancia* (0 es idéntico, 2 es opuesto).
# Para estandarizar el score, usamos: similitud = 1 - distancia.
stmt = (
    select(
        Chunk.text,
        Chunk.page,
        Chunk.document_id,
        (1 - Chunk.embedding.cosine_distance(query_vector)).label("score")
    )
    .where(Chunk.owner_id.in_(["global", owner_id]))
    .order_by(Chunk.embedding.cosine_distance(query_vector))
    .limit(TOP_K)
)
```

`SIM_THRESHOLD` se calibra con el conjunto de evaluación sobre este cálculo de similitud (1 - distancia).

## Operaciones del repositorio

- `insert_chunks`(`session`, `document_id`, `owner_id`, `chunks`): Inserción en lotes (`session.add_all()` o `insert()` multi-fila).
- `delete_document`(`session`, `document_id`, `owner_id`): Basta con borrar el registro en `documents`; la base de datos elimina los `chunks` automáticamente por el `CASCADE`.
- `vector_search`(`session`, `query_vector`, `owner_id`, `k`): Ejecuta el `stmt` definido arriba.
- Idempotencia: Si la BD arroja un error de integridad por la tupla (`owner_id`, `sha256`), retornar 409 sin reprocesar.

## Capacidad (Almacenamiento Local)

PostgreSQL corre localmente en Docker, sin límite de almacenamiento de un servicio gratuito en la nube. Un vector de 1024 floats de precisión simple (4 bytes) ocupa ~4 KB. Con el texto y metadatos, estimamos ~5 KB por chunk. 100.000 chunks ocuparán apenas ~500 MB en disco, lo cual es fácilmente manejable por el equipo local.

## Configuración de PostgreSQL

La conexión se maneja vía SQLAlchemy: `postgresql+psycopg://user:pass@localhost:5432/datatutor`. Las credenciales irán en el `.env `(`DATABASE_URL`). Al levantar el entorno con Docker Compose, el volumen asociado garantizará la persistencia de los datos.
