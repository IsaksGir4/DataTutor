# PROJECT_STATE — DataTutor

> Documento vivo y fuente de contexto del proyecto. Actualizarlo al cerrar cada fase o tras cambios relevantes, y pegarlo al inicio de cada chat nuevo con el Gem. Si el estado pegado difiere de los archivos de conocimiento, prevalece este estado para el contexto de la conversación; los archivos actuales del repositorio siguen siendo la fuente de verdad sobre qué código está realmente implementado.
>
> **Última actualización:** 18 oct 2026 · **Fase actual:** 6 — integración local, frontend y documentación · **Entrega del trabajo:** 18 oct 2026.
>
> **Etiquetas de certeza** usadas en este documento: **[PROBADO]** hay salida de una prueba o comando pegada en el chat · **[OBSERVADO]** visto en la UI, en la BD o en logs · **[IMPLEMENTADO]** el código se aplicó pero no hay prueba dedicada · **[HIPÓTESIS]** explicación plausible, sin demostrar · **[PENDIENTE]** falta hacerlo o verificarlo.
>
> **Documento hermano:** `Guia_definitiva_TutorDatos.md` (corte 11 oct) es el runbook de recuperación del entorno y el registro de incidencias de las Fases 0–2. Varias de sus secciones de agente y pendientes ya están superadas (ver §16); este estado manda en caso de diferencia.

## Índice

1. Resumen ejecutivo
2. Instrucciones de trabajo para el asistente
3. Arquitectura
4. Entorno local y arranque
5. Decisiones técnicas vigentes
6. Configuración y parámetros RAG
7. Versiones registradas
8. Estructura del repositorio
9. Contrato de la API
10. Agente LangGraph
11. Modelo de datos e ingesta
12. Corpus
13. Frontend
14. Seguridad y cadena de suministro
15. Validaciones y evidencia
16. Registro de incidencias resueltas
17. Pendientes y riesgos abiertos
18. Seguimiento de requisitos del enunciado
19. Git y publicación
20. Hoja de ruta
21. Próximas acciones
22. Siguiente prompt para el Gem
23. Variables de entorno
24. Historial de este documento

---

## 1. Resumen ejecutivo

**Qué es.** DataTutor es el "Trabajo Agente" de la materia de Integración e Implementación de Software: una aplicación web con un asistente RAG para ingeniería y ciencia de datos, con agente LangChain + LangGraph, modelo local (Ollama), base vectorial PostgreSQL + pgvector, autenticación Keycloak (OIDC + PKCE), backend FastAPI y frontend React. Responde solo con lo que respalda el corpus, cita sus fuentes y rechaza explícitamente lo que no puede sustentar.

**Qué funciona hoy.**

- **[PROBADO]** Backend protegido con JWT, aislamiento por usuario, subida/listado/borrado de PDFs con estados, historial de conversaciones, `pytest` (5 pruebas) y `vite build`.
- **[OBSERVADO]** Login con Keycloak, chat con fuentes (documento, página, similitud, fragmento), rechazo de preguntas fuera de dominio, historial recuperable, polling de documentos.
- **[OBSERVADO]** Corpus indexado: 3 libros grandes (6 020 chunks de usuario) + 2 documentos globales (57 chunks).

**Qué falta.** Calibración con el conjunto de evaluación, pruebas del respaldo léxico, decisión sobre el `scope` del corpus, preparación de la demo (extracto de la tesis), CI, README, diagrama, documento técnico, diapositivas y despliegue público.

**Riesgos principales (detalle en §17).**

1. Los libros grandes son `scope = user`: solo los ve un usuario concreto. Con otra cuenta, casi todo se rechazaría.
2. Ingestar los mismos libros como `global` sin retirar las copias de usuario duplicaría chunks en la búsqueda.
3. Las respuestas no muestran citas `[n]` en línea y el modelo de 3B puede usar conocimiento propio fuera del contexto.
4. Latencia de 12–33 s por consulta (solo CPU).
5. El despliegue público depende de que Keycloak sea alcanzable desde fuera; la red del campus bloquea ngrok, así que la demo debe funcionar 100 % en local.

---

## 2. Instrucciones de trabajo para el asistente

- Trabajar en pasos pequeños: inspeccionar el archivo actual antes de proponer cambios y explicar el mecanismo del problema antes del parche.
- No reemplazar archivos completos si basta un cambio localizado. Si se propone un reemplazo completo, compararlo primero con la versión real para no borrar lógica existente.
- Distinguir explícitamente entre implementado, probado, observado e hipotético. No afirmar que una solución está aplicada hasta verificar el archivo; no afirmar que una prueba pasó sin su salida.
- No inventar flags, comandos ni nombres de variables: si no se conoce la CLI de un script (p. ej. `ingest_corpus.py`), pedir su contenido o `--help`.
- No ejecutar ni recomendar acciones destructivas sin autorización explícita. En particular: **no `docker compose down -v`**, no borrar el volumen `datatutor-pgdata`, no eliminar ni reingerir el corpus como método genérico de diagnóstico, no `DELETE`/`UPDATE` masivos sin respaldo previo.
- Antes de cambiar esquema, ingesta o vectores, crear un respaldo nuevo (ver §11).
- Mantener las Fases 0–6 en localhost, sin ngrok ni proxy. El despliegue público es de la Fase 7 y se hace fuera del campus.
- Verificar la terminal antes de dar comandos: PowerShell (`PS C:\...>`), cmd (`C:\...>`) y Git Bash (`$`) no son intercambiables.
- Instalar paquetes npm solo con nombres exactos y `--ignore-scripts` (§14). No escribir versiones de memoria: dejar que `npm`/`uv` resuelvan y congelen en los lockfiles.
- El usuario aprende mejor con ejemplos y cambios precisos, explicados línea por línea; explicaciones en español, nombres técnicos en inglés. Documento clave: mantenerlo amplio, no resumirlo.
- Reglas del Gem referenciadas en el historial: **Regla 2** (no escribir versiones de memoria), **Regla 6** (no añadir endpoints no pedidos), **Regla 7** (avisar las diferencias con el enunciado antes de escribir código), **Regla 9** (diagnosticar la causa raíz con evidencia antes de tocar código).
- No bajar ni subir `SIM_THRESHOLD` / `SIM_LOW` para forzar una respuesta ni por una consulta aislada; la calibración usa un conjunto etiquetado.

---

## 3. Arquitectura

```text
Navegador  http://localhost:5173
  React + Vite + keycloak-js
     │  OIDC Authorization Code + PKCE (S256)            ┌───────────────────────────────┐
     ├──────────────────────────────────────────────────►│ Keycloak 24  :8080            │
     │                                                   │ realm datatutor               │
     │  Authorization: Bearer <JWT>                      │ cliente público datatutor-web │
     ▼                                                   └──────────────┬────────────────┘
FastAPI  http://127.0.0.1:8000/api/v1                                   │ JWKS (127.0.0.1)
  controllers → services → agents (LangGraph) / repositories ◄──────────┘ valida RS256
     │                          │
     │                          └──► Ollama nativo  127.0.0.1:11434
     │                               qwen2.5:3b (clasificar, juez, reescribir, responder)
     │                               bge-m3 (embeddings, 1024 dim)
     ▼
PostgreSQL 16 + pgvector  127.0.0.1:5432   (DB datatutor; Keycloak usa la DB keycloak)
```

- Puertos: 5173 (Vite, estricto), 8000 (FastAPI), 8080 (Keycloak), 5432 (PostgreSQL), 11434 (Ollama).
- Contenedores Docker: `datatutor-postgres`, `datatutor-keycloak`. Volumen de datos: `datatutor-pgdata`.
- Separación IPv4/identidad: el navegador usa `localhost` (coincide con `redirectUris`, `webOrigins` y el claim `iss`); backend ↔ Keycloak/API usan `127.0.0.1` para evitar la demora IPv6 en Windows.

---

## 4. Entorno local y arranque

Runbook condensado; el detalle y las comprobaciones están en la guía definitiva.

**Orden de arranque (cada sesión):**

1. Abrir Docker Desktop y esperar al motor. `docker start datatutor-postgres datatutor-keycloak` si están detenidos. No recrearlos a ciegas.
2. Comprobar PostgreSQL: `docker exec datatutor-postgres pg_isready -U postgres -d datatutor` y puerto 5432.
3. Iniciar Ollama en CPU en una terminal que se queda abierta:

   ```powershell
   $env:CUDA_VISIBLE_DEVICES="-1"
   $env:OLLAMA_LLM_LIBRARY="cpu_avx2"
   ollama serve
   ```

   Cerrar antes Ollama Desktop y su icono de bandeja. `ollama list` debe mostrar `qwen2.5:3b` y `bge-m3`.
4. Backend (desde `backend/`): ejecutar desde PyCharm o `uv run uvicorn app.main:app --reload`. Comprobar con `uv run python --version` (3.12.7).
5. Frontend (desde `frontend/`): `npm run dev` → `http://localhost:5173` (usar siempre `localhost`, no `127.0.0.1`).
6. Pruebas del backend: `uv run pytest -v`.

**Apagado:** salir de los clientes, `Ctrl+C` en `ollama serve`, `docker stop datatutor-keycloak datatutor-postgres`. Nunca `-v`.

**Notas del entorno:**

- **GPU:** el usuario reporta que su GPU está dañada. Ollama falla en GPU (`CUDA error: an illegal instruction was encountered`, Ollama 0.40.0). CPU-only es la configuración definitiva de este equipo, no un workaround temporal.
- **PostgreSQL nativo:** el servicio `postgresql-x64-17` de Windows ocupó el puerto 5432; se dejó detenido y deshabilitado. Si reaparece un fallo de conexión, comprobar primero ese servicio.
- **Credenciales:** contraseñas de desarrollo local solo; viven en `.env` y deben coincidir con `settings.py`. No copiarlas a este documento, a Git ni a un chat.
- **Docker Hub:** si falla un `pull` por credenciales, `docker logout` y reintentar.

---

## 5. Decisiones técnicas vigentes

| Área              | Decisión                                                                                                                                                                                                                                                         |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sistema            | Windows; repo en `C:\Users\HP\Desktop\2026-2\Integracion e implementacion Soft\TutorDatos`                                                                                                                                                                      |
| Backend            | Python 3.12.7 + FastAPI + `uv`, ejecutado desde PyCharm; SQLAlchemy 2.0                                                                                                                                                                                         |
| Agente             | LangChain + LangGraph con `StateGraph` explícito                                                                                                                                                                                                               |
| LLM                | `qwen2.5:3b` en Ollama, CPU (`temperature` 0.0, `num_ctx` 4096, `num_predict` 512; hoy fijos en `app/llm/chat.py`)                                                                                                                                      |
| Embeddings         | `bge-m3`, 1024 dimensiones                                                                                                                                                                                                                                      |
| Datos              | PostgreSQL 16 + pgvector en Docker; índice HNSW; `ON DELETE CASCADE` en `messages` y `chunks`                                                                                                                                                              |
| Autenticación     | Keycloak 24, OIDC Authorization Code + PKCE S256; cliente público `datatutor-web` (sin Direct Access Grants); backend valida JWT RS256 (`iss` = `http://localhost:8080/realms/datatutor`, `aud` = `datatutor-web`, `exp`) con JWKS por `127.0.0.1` |
| Frontend           | React + Vite + `keycloak-js`; token en memoria (no `localStorage`); linter Oxlint                                                                                                                                                                             |
| PDF                | PyMuPDF (`fitz`), extracción por página; splitter por página (1000/200)                                                                                                                                                                                      |
| Cliente de pruebas | `datatutor-swagger` con Direct Access Grants, solo para scripts de consola                                                                                                                                                                                      |
| Ingesta            | Libros completos por `scripts/ingest_corpus.py`; la subida web, para extractos de ~5–30 páginas                                                                                                                                                               |

---

## 6. Configuración y parámetros RAG

**Parámetros (unificados en `settings.py` y `.env`):** `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `TOP_K=4`, `SIM_THRESHOLD=0.65`, `SIM_LOW=0.50`, `MAX_UPLOAD_MB=30`.

- **[OBSERVADO]** Un script de diagnóstico imprimió `THRESHOLD: 0.65` leyendo `settings`; `SIM_THRESHOLD` **no** es importable desde `core.py` (vive en `settings`).
- **[IMPLEMENTADO]** `core.py` y `graph.py` consumen `settings.TOP_K`, `settings.SIM_THRESHOLD` y `settings.SIM_LOW` como única fuente (según el estado previo; verificar el archivo si se toca).
- **[PENDIENTE]** Centralizar en `settings.py` el modelo, `num_ctx` y `num_predict` que hoy están fijos en `app/llm/chat.py`. Baja prioridad.

**Archivos de entorno:**

- `TutorDatos/.env`: backend y servicios; secretos locales; no se versiona.
- `TutorDatos/.env.example`: plantilla sin secretos.
- `TutorDatos/frontend/.env`: variables de Vite; solo públicas con prefijo `VITE_`.
- `TutorDatos/frontend/.env.example`: plantilla de las variables públicas.
- El frontend no necesita contraseñas de PostgreSQL, credenciales de Keycloak admin ni parámetros de Ollama. Backend y frontend se configuran por separado (el backend lee el `.env` raíz mediante `PROJECT_ROOT`).
- `CORS_ORIGINS` debe incluir `http://localhost:5173`.
- Se corrigió en el `.env` raíz una `KEYCLOAK_JWKS_URL` que traía sintaxis Markdown (`[url](url)`) y barras invertidas copiadas de un chat; el esquema resuelto apareció como `http`.

---

## 7. Versiones registradas

Copiadas del estado previo (`uv pip list`). Volver a comprobarlas con los comandos de cada gestor si se actualizan dependencias. No cambiar versiones solo para resolver un problema.

**Backend:** `fastapi==0.142.2`, `uvicorn==0.54.0`, `pydantic==2.13.5`, `pydantic-settings==2.15.0`, `sqlalchemy==2.1.3`, `psycopg==3.3.6`, `pgvector==0.5.0`, `langchain==1.4.3`, `langchain-core==1.6.7`, `langchain-ollama==1.1.0`, `langgraph==1.2.14`, `pymupdf==1.28.2`, `pyjwt==2.15.1`, `cryptography==50.0.2`, `httpx==0.28.1`, `pytest==9.1.1`, `ruff==0.16.10`.

**Frontend:** `react@19.3.1`, `react-dom@19.3.1`, `keycloak-js@26.2.4`, `vite@8.3.4`, `@vitejs/plugin-react@6.1.2`, `oxlint@1.88.0`, `@types/react@19.3.0`, `@types/react-dom@19.3.0` .

- **[OBSERVADO]** El frontend se reinstaló el 16 oct con `npm create vite@latest` + `npm install --ignore-scripts` (25 packages have verified registry signatures, 15 packages have verified attestations) y se añadió `keycloak-js`.

**npm list --depth=0**
frontend@0.0.0 C:\Users\HP\Desktop\2026-2\Integracion e implementacion Soft\TutorDatos\frontend
├── @types/react-dom@19.3.0
├── @types/react@19.3.0
├── @vitejs/plugin-react@6.1.2
├── keycloak-js@26.2.4
├── oxlint@1.88.0
├── react-dom@19.3.1
├── react@19.3.1
└── vite@8.3.4

**npm audit signatures**
audited 25 packages in 3s

25 packages have verified registry signatures

15 packages have verified attestations

---

## 8. Estructura del repositorio

Confirmar contra el árbol real antes de añadir o mover archivos.

```text
TutorDatos/
├── .env  .env.example  .gitignore  compose.yml
├── corpus/                       # PDFs locales; NO se versionan (§19)
├── docker/postgres/init/01-keycloak-db.sql
├── docs/                         # 01 a 07 (07 = este documento)
├── keycloak/import/datatutor-realm.json
├── backend/
│   ├── pyproject.toml  uv.lock
│   ├── app/
│   │   ├── main.py               # lifespan: fail_interrupted_documents
│   │   ├── agents/               # graph.py, prompts.py, state.py, nodes/core.py
│   │   ├── config/settings.py
│   │   ├── controllers/          # chat.py, documents.py
│   │   ├── core/                 # database.py, deps.py, errors.py, security.py
│   │   ├── llm/                  # chat.py, embeddings.py
│   │   ├── repositories/         # models.py, chat_repo.py, document_repo.py
│   │   ├── schemas/              # chat.py, document.py
│   │   ├── services/             # chat.py, documents.py, ingestion.py
│   │   └── vectorstore/retriever.py
│   ├── eval/questions.jsonl
│   ├── scripts/                  # verificar_entorno, ingest_corpus, chat_cli, test_api, test_documents
│   └── tests/test_api_contracts.py
└── frontend/
    ├── .env  .env.example  package.json  package-lock.json  vite.config.js  index.html  .oxlintrc.json
    └── src/  main.jsx  App.jsx  styles.css  services/{auth.js, api.js}
```

---

## 9. Contrato de la API

Prefijo `/api/v1`. Todas las rutas, salvo `/health`, exigen `Authorization: Bearer <JWT>`; el aislamiento usa `owner_id = sub`.

| Método y ruta                       | Función                                                                                                     | Códigos relevantes |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ------------------- |
| `GET /health`                      | Salud (pública)                                                                                             | 200                 |
| `GET /me`                          | Perfil del token (`sub`, `preferred_username`, `roles`)                                                | 200, 401            |
| `POST /chat`                       | Un turno: `{question, conversation_id?}` → `{conversation_id, answer, decision, sources[], latency_ms}` | 200, 401, 422, 503  |
| `GET /conversations`               | Conversaciones propias, recientes primero                                                                    | 200                 |
| `GET /conversations/{id}/messages` | Mensajes (`role`, `content`, `decision`, `sources`, `best_score`, `latency_ms`)                  | 200, 404            |
| `DELETE /conversations/{id}`       | Borra conversación y mensajes (cascada)                                                                     | 204, 404            |
| `POST /documents`                  | Subida `multipart/form-data`; procesa en segundo plano                                                     | 202, 409, 413, 415  |
| `GET /documents`                   | Documentos propios y globales                                                                                | 200                 |
| `GET /documents/{id}`              | Detalle                                                                                                      | 200, 404            |
| `DELETE /documents/{id}`           | Borra documento propio (no globales) y chunks                                                                | 204, 404            |

**Reglas del contrato:**

- Pregunta de 2 a 2000 caracteres; en blanco → 422.
- `decision` ∈ `answered`, `rejected`, `clarify`, `smalltalk`. **Un rechazo del agente es HTTP 200** con `decision = "rejected"`; no es un error de infraestructura.
- Errores: `{ "error": { "code", "message", "request_id" } }`. El 503 `agent_error` incluye `conversation_id` para que el frontend fije la conversación activa y no cree duplicados al reintentar.
- **Limitación conocida:** el envío no es idempotente. Reintentar la misma pregunta tras un 503 reutiliza la conversación pero inserta otro mensaje `user`.
- Conversación ajena o inexistente → 404 (no se revela su existencia).
- Estados de documento: `pending` → `processing` → `ready` | `failed`. `ready` con 0 chunks no existe: un PDF sin texto seleccionable queda `failed`.
- Mensaje obligatorio de rechazo (observado): "No tengo suficiente información en mi base de conocimiento para responder esa pregunta. Te sugiero cargar documentos relacionados con el tema."

---

## 10. Agente LangGraph

**Flujo [OBSERVADO en CLI y UI]:**

```text
START → receive → classify_intent
  ├── smalltalk      → generate_smalltalk → save_history → END
  ├── out_of_domain  → refuse             → save_history → END
  └── explain / exercise / fallback → retrieve → grade_context
        ├── suficiente → generate_answer → save_history → END
        └── insuficiente
              ├── primer intento → rewrite_query → retrieve → grade_context
              └── tras el reintento:
                    ├── consulta corta/ambigua (≤ 4 palabras) → clarify
                    └── resto sin evidencia                    → refuse (rejected)
```

**Umbrales aplicados en `grade_context` [IMPLEMENTADO]:**

| Condición                                            | Comportamiento                                                          |
| ----------------------------------------------------- | ----------------------------------------------------------------------- |
| `best_score < SIM_LOW` (0.50)                       | Contexto insuficiente, sin llamar al juez                               |
| `SIM_LOW ≤ score < SIM_THRESHOLD`, primer intento  | Insuficiente, sin juez                                                  |
| `SIM_LOW ≤ score < SIM_THRESHOLD`, tras reescribir | El juez LLM evalúa                                                     |
| `score ≥ SIM_THRESHOLD`                            | El juez LLM evalúa; si no responde `true`, entra el respaldo léxico |

- El juez evalúa sobre `state["question"]`. Un JSON inválido o una clave no booleana cuenta como "no suficiente" (nunca como éxito).
- **Respaldo léxico (17 oct) [IMPLEMENTADO, OBSERVADO en logs]:** si el juez no devuelve `sufficient: true`, se acepta el contexto solo si `best_score ≥ SIM_THRESHOLD` **y** `_has_direct_lexical_evidence` es verdadero: al menos 2 términos específicos de la pregunta (≥ 5 letras, sin stopwords ni términos genéricos como "bases" o "datos") presentes en los chunks y que representen ≥ 35 % de los términos específicos de la pregunta.
  - **Motivo:** el juez `qwen2.5:3b` rechazaba la pregunta de normalización pese a recuperar fragmentos de Silberschatz (págs. 181, 182, 27, 28; score máx. 0.706). Reescribir `GRADER_PROMPT` no lo corrigió. Los descartes previos fueron: propietario (`owner_id` coincide en documentos y chunks), codificación y falta absoluta de evidencia.
  - **Limitaciones [HIPÓTESIS]:** es una heurística léxica; puede aceptar contexto débil con términos coincidentes; con preguntas en español y fragmentos en inglés (p. ej. *Fundamentals of Data Engineering*) rara vez coincidirá, así que no ayuda ahí; no rescata contextos por debajo de `SIM_THRESHOLD`.
- **[PENDIENTE]** `rewrite_query` sigue produciendo consultas casi idénticas a la original, de modo que el segundo `retrieve` recupera prácticamente lo mismo. No mezclarlo con otro cambio de comportamiento.
- **[PENDIENTE]** La ruta `clarify` por score quedó sustituida por la regla de longitud (≤ 4 palabras). Revisar casos de borde en la calibración.
- Historial: el servicio pasa al agente las últimas 6 interacciones y persiste cada turno (mensaje de usuario antes de invocar el grafo; respuesta después). El título de la conversación es `question[:40]`.
- `save_history` dejó de ser un paso ficticio: la persistencia real ocurre en `services/chat.py` **[OBSERVADO en BD]**.

---

## 11. Modelo de datos e ingesta

**Tablas relevantes** (columnas inferidas de los esquemas y de la restricción `uix_owner_sha256`; confirmar en `models.py`): `documents` (`id`, `filename`, `scope`, `owner_id`, `status`, `pages`, `chunks_count`, `size_bytes`, `error`, `sha256`, `created_at`), `chunks` (texto, página, `embedding vector(1024)`, `embed_model`, `owner_id`, `document_id`), `conversations`, `messages`.

- Restricción `uix_owner_sha256`: el mismo PDF no se duplica **por propietario**. Un mismo archivo sí puede existir como `global` y como `user` a la vez **[HIPÓTESIS a verificar en el esquema]**.
- `ON DELETE CASCADE` verificado en `pg_constraint` para `messages_conversation_id_fkey` y `chunks_document_id_fkey`.
- Búsqueda: `Chunk.owner_id IN ('global', <sub>)`, distancia coseno, `TOP_K = 4`.
- `fail_interrupted_documents` en `lifespan`: al arrancar marca como fallidos los documentos `pending`/`processing`. Precaución: un reinicio con `--reload` interrumpe una ingesta en curso; no ingerir libros grandes por la web.
- Un PDF que extrae 0 chunks pasa a `failed`.

**Lección del re-embedding (Fase 1–2):** el campo `embed_model='bge-m3'` no prueba que el vector se haya generado con ese modelo. Los 57 chunks iniciales tenían coseno `-0.056` contra una regeneración fresca; tras regenerarlos en sitio fue `1.000000`. Tras una ingesta grande, validar una muestra (coseno almacenado vs. regenerado, sin nulos ni normas cero) en vez de asumir que está bien.

**Respaldo antes de cambios de BD** (desde `backend/`, PowerShell):

```powershell
$backup = "datatutor_$(Get-Date -Format yyyyMMdd_HHmmss).dump"
docker exec datatutor-postgres pg_dump -U postgres -d datatutor -Fc -f "/tmp/$backup"
docker cp "datatutor-postgres:/tmp/$backup" ".\$backup"
```

Existe `backend/datatutor_pre_reembedding.dump` (298 kB, anterior al re-embedding; no sobrescribir). Los `.dump` no se versionan. Para practicar una restauración, usar una base nueva (`datatutor_restore_test`) y no la activa.

---

## 12. Corpus

**Plan por olas (según el estado previo):**

- **Ola 1:** Silberschatz (BD, español); *Fundamentals of Data Engineering Concepts* (inglés); *Libro GUIA ingeniería de datos* (español); *Fundamentos de Ingeniería de Datos* (español, ~38 KB, prueba de humo); *Principles of Data Science* (inglés); *Seven ways…* (inglés); *Understanding… failure* (inglés).
- **Ola 2:** *EDR teoría BD*; *Big Book of Data Warehousing and BI*; *Python programming for Data Analysis*; `INTELIGENCIA_ARTIFICIAL`; `Data science route`.
- **Fuera de v1:** *Geometric Data Science book*.
- **Reservada para la demo en vivo:** tesis sobre control predictivo no lineal basado en modelo borroso; usar un extracto de ~30 páginas con texto seleccionable, no el libro completo.
- **[PENDIENTE]** La auditoría consolidada de PDFs (páginas, caracteres por página, texto seleccionable) no está registrada.

**Indexado hoy (`status = ready`) [OBSERVADO en BD]:**

| Documento                                      | scope  | owner_id                     | págs | chunks |
| ---------------------------------------------- | ------ | ---------------------------- | ----- | ------ |
| Silberschatz, Fundamentos de BD 6ª ed.        | global | `global`                   | 673   | 4957   |
| Fundamentals-of-Data-Engineering-Concepts      | global | `global`                   | 219   | 693    |
| INTELIGENCIA_ARTIFICIAL                        | user   | `aaaaaaaa-…-000000000002` | 144   | 370    |
| Seven ways to make a data science project fail | global | `global`                   | 5     | 41     |
| Fundamentos-de-Ingeniería-de-Datos            | global | `global`                   | 16    | 16     |
| Libro GUIA ingenieria de datos.pdf             | global | `global`                   | 544   | 1320   |

- **[OBSERVADO]** `chunks.owner_id` coincide con el `owner_id` de su documento en los cinco casos.
- `Data science route.pdf` se eliminó tras comprobar que no tenía texto seleccionable (0 chunks).
- **Riesgo de visibilidad:** los tres libros grandes (6 020 chunks) solo los ve el usuario `aaaaaaaa-…-0002`. Cualquier otra cuenta, incluida una nueva registrada en Keycloak, buscaría solo en los 57 chunks globales.
- **Riesgo de duplicados:** si se ingiere otra vez un libro ya indexado como `user` esta vez como `global`, el retriever devolvería ambas copias y podrían ocupar los 4 resultados. Decidir el `scope` **antes** de ingerir los libros restantes.
- **Decisión pendiente:** convertir los tres libros a `global` actualizando `documents.scope`, `documents.owner_id` y `chunks.owner_id` de forma coherente, en una transacción y con respaldo previo, o dejar un único usuario de demo. Requiere autorización explícita.
- **Procedimiento para ingerir los libros restantes:** colocar los PDFs en `corpus/`, respaldar la BD, ejecutar `scripts/ingest_corpus.py` (consultar su `--help`; no asumir flags), con Ollama en CPU y sin otras cargas pesadas. Comparar luego `documents` y `chunks` contra lo esperado y validar una muestra de embeddings. Los libros largos tardan; no lanzar dos ingestas a la vez.
- **Política de repositorio:** los PDFs no se suben a GitHub. La base vive en el volumen Docker y se reproduce con el script. Sugerido: un `corpus/README.md` con los nombres esperados de los PDFs (sin los PDFs) para que el procedimiento sea reproducible.

---

## 13. Frontend

- **Auth:** `src/services/auth.js` con instancia `keycloak-js` y `initPromise` singleton (evita el doble `init()` de `React.StrictMode`); `onLoad: "login-required"`, `pkceMethod: "S256"`, `checkLoginIframe: false`; `getValidToken()` llama a `updateToken(30)` antes de cada petición. **[PENDIENTE]** verificar contra el archivo real (en `git status` aparece creado y modificado).
- **API:** `src/services/api.js` adjunta el `Bearer`; no fija `Content-Type` cuando el cuerpo es `FormData` (el navegador añade el `boundary`); traduce el sobre de error del backend. Los enlaces Markdown (`[url](url)`) que se colaron en código copiado deben ser URLs simples.
- **App:** barra lateral con usuario, nuevo chat, historial de conversaciones (seleccionar/borrar), subida de PDFs y lista de documentos con estado. Área principal con mensajes, insignias por decisión (`answered` verde, `clarify` azul, `rejected` rojo/ámbar, `smalltalk` gris), fuentes y latencia, banner de errores.
- **Polling:** si hay documentos `pending`/`processing`, `GET /documents` cada 3 s hasta que todos sean terminales. Un documento huérfano mantendría activo el polling (se mitiga con `fail_interrupted_documents`).
- **Botón de borrar documento:** solo para `scope = user` y estado no activo; la restricción real vive en el backend (404 o rechazo en la capa de servicio/repositorio).
- **Historial sin texto (resuelto):** `MessageItem` no exponía `content`. Se añadió `content: str` y `sources` en `schemas/chat.py`; verificado en UI y en pytest. Se propuso además un respaldo en `App.jsx`: `{m.content || m.answer || m.text || "(Mensaje sin contenido de texto)"}` dentro de `<div className="message-body">` **[IMPLEMENTADO si se aplicó; verificar]**; `message-body` no tiene reglas CSS propias (el `white-space: pre-wrap` lo aporta `.message-card`).
- **Build:** `vite build` compila sin errores (391 ms) **[PROBADO]**.
- **Origen:** acceder siempre por `http://localhost:5173`. `redirectUris` y `webOrigins` del realm solo lo permiten, y la API criptográfica de PKCE requiere contexto seguro.
- **[PENDIENTE]** Respuestas del usuario a las 3 preguntas de comprensión de la Fase 5 (StrictMode e `initPromise`; `FormData` sin `Content-Type` manual; qué capa frena un `DELETE` a un documento global o en proceso).

**Mejoras aplicadas el 18 oct [IMPLEMENTADO]:**

- Se conservaron la identidad oscura/azul y el contrato existente de la API.
- Se agregaron estados visuales de autenticación y carga con `aria-live`, spinner y mensajes de error con `role="alert"`.
- Se añadieron etiquetas accesibles y foco visible para controles de chat, subida, eliminación, logout y selección de conversaciones.
- Las conversaciones se pueden seleccionar también con teclado (`Enter` o espacio).
- Se agregó estado vacío explícito cuando no hay conversaciones o documentos.
- Se añadió un layout responsive para pantallas medianas y móviles, además de respeto por `prefers-reduced-motion`.
- Se corrigió el arranque local de PostgreSQL: el backend crea la extensión `vector` y las tablas ORM si la base está vacía, evitando que una instalación nueva falle con `relation does not exist`.
- Se registraron los tres integrantes en `docs/08_DOCUMENTO_TECNICO.md` y se incorporó la captura de la aplicación en `docs/evidencias/aplicacion-actual.png`.
- Se preparó `render.yaml` como configuración reproducible alternativa para Render (API + PostgreSQL con pgvector) y `frontend/vercel.json` para la SPA de Vercel.
- Se añadió `docs/09_GUIA_DESPLIEGUE.md` con el procedimiento manual mediante PostgreSQL + Web Service en Render, Vercel y el guion de pruebas manuales.
- Se rediseñó el frontend con una identidad futurista de Ingeniería de Datos: tipografías técnicas, paneles de sistema, flujo visual `INGEST → EMBED → RETRIEVE → ANSWER`, fondo de cuadrícula, estados visuales y responsive conservando las funciones existentes.
- Se estandarizó el nombre visible y técnico del agente como **DataTutor**: interfaz, título del navegador y metadatos de FastAPI.
- El cliente de chat ahora consume `CHAT_MODEL`, `NUM_CTX` y `NUM_PREDICT` desde configuración, lo que permite ajustar el despliegue sin modificar código.

---

## 14. Seguridad y cadena de suministro

- **npm (oct 2026):** hay campañas activas de malware y typosquatting en el registro (p. ej. MALFEX, el gusano de `tensorlake`, paquetes que imitan a `nestjs`, `vite` o `keycloak-js`) y un fallo de Trusted Publishing con más de 1 500 paquetes expuestos. No se encontró un aviso contra `react`, `react-dom`, `vite`, `@vitejs/plugin-react` ni `keycloak-js`, pero eso no garantiza que estén limpios.
- **Reglas:** nombres exactos; `npm install --ignore-scripts`; revisar `package-lock.json` en busca de nombres desconocidos; `npm audit` y `npm audit signatures` (esta última no es infalible: un ataque reciente tenía procedencia válida); `npm ci` para reproducir; no tener tokens reales en el entorno de instalación.
- **Secretos:** `.env`, `frontend/.env` y los `.dump` no se versionan. Las credenciales locales de desarrollo no se copian a documentos ni chats. La guía definitiva menciona valores de desarrollo locales: revisarla antes de hacer público el repositorio.
- **Tokens:** el JWT vive en memoria de `keycloak-js` (no en `localStorage`), con renovación preventiva.
- **Autorización:** todo acceso a conversaciones, mensajes y documentos filtra por `owner_id = sub`; un recurso ajeno responde 404.

---

## 15. Validaciones y evidencia

**Por fase:**

- **Fase 0 [PROBADO]:** `scripts/verificar_entorno.py` (PostgreSQL + pgvector, JWKS de Keycloak, Ollama con `qwen2.5:3b` y `bge-m3`).
- **Fases 1–2 [PROBADO]:** ingesta inicial, re-embedding de 57 chunks (coseno 1.000000, 0 nulos, 1024 dim), recuperación (0.7172 en inglés, 0.6825 en español) y CLI `chat_cli.py` con tres casos (pregunta respondible, sin soporte, saludo).
- **Fase 3 [PROBADO]:** `scripts/test_api.py`: JWT, 401 sin token y con token manipulado, `POST /chat` 200, aislamiento 404 entre usuarios.
- **Fase 4 [PROBADO]:** `scripts/test_documents.py`: 202, estado `ready`, listado 200, duplicado 409, validación de embeddings, borrado 204 y cascada.
- **Fase 5 [PROBADO/OBSERVADO]:** `pytest` 5 passed (1.80 s y 1.93 s en dos reportes); `vite build` correcto; login OIDC + PKCE, historial con texto, polling, recuperación de documentos interrumpidos y rechazo de PDFs sin texto verificados en UI. El fallo previo de `DataTutorException` sin `conversation_id` se corrigió en `core/errors.py`.
- **Salida de pytest [PROBADO]:**

```PowerShell
=============================================================================== test session starts ===============================================================================
platform win32 -- Python 3.12.7, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\HP\Desktop\2026-2\Integracion e implementacion Soft\TutorDatos\backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\HP\Desktop\2026-2\Integracion e implementacion Soft\TutorDatos\backend
configfile: pyproject.toml
plugins: anyio-4.15.1, langsmith-0.14.4
collected 5 items                                                                                                                                                                

tests/test_api_contracts.py::test_health_and_openapi_expose_all_endpoints PASSED                                                                                             [ 20%]
tests/test_api_contracts.py::test_protected_endpoints_reject_anonymous PASSED                                                                                                [ 40%]
tests/test_api_contracts.py::test_database_foreign_keys_enforce_sql_on_delete_cascade PASSED                                                                                 [ 60%]
tests/test_api_contracts.py::test_chat_503_returns_conversation_id_to_avoid_duplicate_conversations PASSED                                                                   [ 80%]
tests/test_api_contracts.py::test_conversation_lifecycle_and_cross_user_isolation PASSED                                                                                     [100%]

================================================================================ 5 passed in 1.82s ================================================================================
```

**Pruebas de chat del 17 oct (tras el respaldo léxico) [OBSERVADO en UI y en `messages`]:**

| Pregunta                                                                       | decision                    | best_score | latencia  |
| ------------------------------------------------------------------------------ | --------------------------- | ---------- | --------- |
| ¿Qué es la normalización… y para qué sirven las formas normales?          | answered                    | 0.706      | 33 039 ms |
| ¿Qué son la segunda y la tercera forma normal?                               | answered                    | 0.665      | 32 073 ms |
| ¿Cuál es la mejor receta para preparar sushi?                                | rejected (fuera de dominio) | 0.000      | 1 295 ms  |
| ¿Cómo se configura un clúster de Apache Kafka con ZooKeeper en producción? | rejected                    | 0.542      | 16 609 ms |
| Que es una automatizacion?                                                     | clarify                     | 0.607      | 13 943 ms |
| Que es una automatizacion en procesos de machine learning?                     | rejected                    | 0.550      | 12 617 ms |

- Antes del cambio, la de normalización terminaba en `rejected` (0.678, 29 741 ms). En una corrida anterior Kafka dio 0.614 y 15 540 ms; el `best_score` guardado es el del último intento, tras reescribir, por eso varía.
- **Rechazos correctos:** sushi (sin consultar `pgvector`) y Kafka (sin evidencia en el corpus).
- **Por revisar [HIPÓTESIS]:** "automatización en procesos de machine learning" (0.550) podría ser un falso negativo, porque `INTELIGENCIA_ARTIFICIAL` está indexado; revisar los chunks recuperados antes de concluir.

**Calidad observada del texto generado:**

- Las respuestas **no muestran citas `[n]` en línea**, aunque el prompt de respuesta las exige. Las fuentes aparecen al final, lo que no demuestra que cada afirmación esté respaldada.
- La respuesta de normalización define 1FN y 2FN con contenido que los fragmentos recuperados (por sus extractos) no parecen aportar, y la de 2FN/3FN admite "no hay detalles" para la 2FN. **[HIPÓTESIS]** el modelo de 3B usa conocimiento propio fuera del contexto; verificar con el texto completo de los chunks y una prueba de *grounding*.
- Terminología: en la Guía, una respuesta tradujo mal *unrealistic expectations* ("Realismos inaceptables").

**Latencia:** 12–33 s por consulta en CPU, con varias llamadas al LLM por turno (clasificar, juez, reescribir y responder; el juez puede correr dos veces). Algunas mediciones se hicieron con ingestas en paralelo (se llegó a 42 s). **[PENDIENTE]** medir por nodo y sin carga en paralelo.

**Datos de prueba en la BD de desarrollo [OBSERVADO]:** `messages` contiene un `owner_id` `pytest-503-user-…`, lo que indica que las pruebas dejan filas en la base real. Pendiente decidir una base de pruebas o limpieza en el teardown; no borrar sin autorización.

---

## 16. Registro de incidencias resueltas

| Incidencia                                             | Causa                                                          | Resolución                                                                    |
| ------------------------------------------------------ | -------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `uv` creó el proyecto con Python 3.14               | Versión global distinta de la objetivo                        | `uv python pin 3.12.7`; no borrar `backend/.venv`                          |
| Docker no descargaba la imagen                         | Credenciales guardadas de Docker Hub                           | `docker logout` y reintento                                                  |
| Puerto 5432 ocupado                                    | Servicio `postgresql-x64-17` de Windows                      | Detenido y deshabilitado                                                       |
| Errores de autenticación desde Windows                | Discrepancia de credenciales + colisión con PostgreSQL nativo | `ALTER USER` dentro del contenedor; `.env` y `settings.py` sincronizados |
| Ollama fallaba con JSON/GPU                            | Fallo de inferencia en GPU (la GPU del equipo está dañada)   | CPU-only con `CUDA_VISIBLE_DEVICES=-1` y `OLLAMA_LLM_LIBRARY=cpu_avx2`     |
| Búsqueda irrelevante con el artículo ya ingerido     | Embeddings guardados incompatibles con el modelo actual        | Respaldo + re-embedding en sitio de los 57 chunks                              |
| El CLI ejecutaba el grafo dos veces                    | Dos bucles sobre `agent_app.stream`                          | Un solo stream con `stream_mode="updates"`                                   |
| Juez con JSON inválido daba contexto válido          | `except` devolvía `context_ok=True`                       | Ahora `context_ok=False`                                                     |
| `clarify` para preguntas claras sin evidencia        | Decisión por score tras el reintento                          | `clarify` solo para consultas de ≤ 4 palabras; resto → `rejected`        |
| Pytest: `DataTutorException` sin `conversation_id` | El constructor no lo aceptaba                                  | `errors.py` acepta y serializa el campo                                      |
| Historial sin texto                                    | `MessageItem` sin `content`                                | Campo añadido en `schemas/chat.py`                                          |
| Documentos atascados en `processing`, `0 págs`    | Tareas en segundo plano interrumpidas por `--reload`         | `fail_interrupted_documents` en `lifespan`; ingesta de libros por CLI      |
| PDF sin texto indexado como `ready`                  | Extracción con 0 chunks                                       | Se marca `failed`                                                            |
| Normalización rechazada con score 0.706               | Falso negativo del juez 3B                                     | Respaldo léxico (§10)                                                        |
| `ImportError: SIM_THRESHOLD` en un diagnóstico      | La constante vive en `settings`, no en `core.py`           | Usar `settings.SIM_THRESHOLD`                                                |
| Código con enlaces Markdown corruptos                 | Copiado desde un chat                                          | Dejar URLs simples en `api.js`, `.env` y `security.py`                   |
| `keycloak.js` truncado en un adjunto                 | Salida cortada                                                 | Usar `services/auth.js` completo                                             |
| `npm install` colgado 30 min                         | Red universitaria                                              | Cambio de red; terminó en 14 s                                                |
| `Remove-Item` no reconocido                          | Se usaba cmd, no PowerShell                                    | En cmd, `rmdir /s /q`                                                        |

**Secciones de la guía definitiva que quedaron superadas:** el flujo con el umbral 0.45 para decidir entre aclarar y rechazar (§7), el pendiente de `save_history` ficticio, el de frontend/API sin validar y el de la ruta clara-sin-evidencia → `clarify`. El resto (arranque, respaldo, re-embedding) sigue vigente.

---

## 17. Pendientes y riesgos abiertos

| #  | Ítem                                                                | Tipo           | Acción propuesta                                                                                                                                                                                                                                                              |
| -- | -------------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1  | Visibilidad del corpus (`scope user` vs `global`)                | Riesgo alto    | Decidir con respaldo y autorización antes de ingerir más libros                                                                                                                                                                                                              |
| 2  | Duplicados al ingerir como `global` lo que ya está como `user`  | Riesgo medio   | Verificar `uix_owner_sha256`; no reingerir libros ya indexados                                                                                                                                                                                                               |
| 3  | Sin citas `[n]` en línea; posible conocimiento fuera del contexto | Calidad        | Revisar `ANSWER_PROMPT` y añadir prueba de *grounding*                                                                                                                                                                                                                    |
| 4  | Respaldo léxico sin pruebas unitarias                               | Calidad        | Pruebas con fakes: normalización acepta; Kafka y sushi rechazan                                                                                                                                                                                                               |
| 5  | Calibración de umbrales con `eval/questions.jsonl`                | Fase 6–7      | Métricas: aciertos, rechazos correctos, falsos negativos, latencia                                                                                                                                                                                                            |
| 6  | `rewrite_query` casi idéntico a la consulta original              | Calidad        | Mejorar sin mezclar con otros cambios                                                                                                                                                                                                                                          |
| 7  | Latencia 12–33 s                                                    | Rendimiento    | Medir por nodo, sin carga en paralelo; revisar `OLLAMA_KEEP_ALIVE`                                                                                                                                                                                                           |
| 8  | Las pruebas dejan datos en la BD de desarrollo                       | Higiene        | BD de pruebas o limpieza en teardown                                                                                                                                                                                                                                           |
| 9  | Versiones reales del frontend sin registrar                          | Documentación | `npm list --depth=0` y `npm audit signatures`                                                                                                                                                                                                                              |
| 10 | Despliegue público (Fase 7)                                         | Riesgo         | Con el frontend en Vercel/Netlify, un navegador externo intentaría `localhost:8080` para Keycloak; hace falta exponer Keycloak (segundo túnel), ajustar `KC_HOSTNAME`, `iss`, `redirectUris` y `CORS_ORIGINS`. La demo del campus debe ser local (ngrok bloqueado) |
| 11 | Comparación `bge-m3` vs `nomic-embed-text`                      | Fase 7         | `nomic-embed-text` suele generar 768 dimensiones **[verificar con `ollama show`]**; la columna es de 1024, así que haría falta otra columna o tabla y re-embedding completo en CPU. Planificar antes de tocar datos                                                |
| 12 | Auditoría de PDFs (texto seleccionable)                             | Documentación | Registrar páginas y caracteres por página                                                                                                                                                                                                                                    |
| 13 | CI                                                                   | Fase 7         | `pytest` y `vite build` en GitHub Actions                                                                                                                                                                                                                                  |
| 14 | Centralizar modelo, `num_ctx` y `num_predict` en `settings.py` | Limpieza       | Baja prioridad                                                                                                                                                                                                                                                                 |
| 15 | Respuestas a las 3 preguntas de la Fase 5                            | Aprendizaje    | Entregar al Gem                                                                                                                                                                                                                                                                |
| 16 | Documento huérfano mantiene el polling activo                       | Menor          | Mitigado por `fail_interrupted_documents`                                                                                                                                                                                                                                    |

---

## 18. Seguimiento de requisitos del enunciado

Contrastar siempre contra `trabajo_agente.pdf` y `04_API_CONTRATO.md`; esta tabla resume el estado del proyecto.

| Requisito                                                         | Estado                  |
| ----------------------------------------------------------------- | ----------------------- |
| Autenticación OIDC + PKCE con Keycloak (login, registro, logout) | [OBSERVADO]             |
| Backend protegido que valida el JWT                               | [PROBADO]               |
| Agente LangChain + LangGraph con modelo local                     | [OBSERVADO]             |
| Respuestas con fuentes (documento, página, similitud, fragmento) | [OBSERVADO]             |
| Rechazo explícito sin evidencia, con el mensaje obligatorio      | [OBSERVADO]             |
| Historial de conversaciones (listar, consultar, borrar)           | [PROBADO]               |
| Carga de documentos propios con estados asíncronos y borrado     | [PROBADO]               |
| Aislamiento entre usuarios                                        | [PROBADO]               |
| Conjunto de evaluación con métricas                             | [PENDIENTE] (Fase 6–7) |
| CI                                                                | [PENDIENTE] (Fase 7)    |
| Despliegue público (opcional si el campus lo bloquea)            | [PENDIENTE] (Fase 7)    |
| README, diagrama, documento técnico, diapositivas                | [PENDIENTE] (Fase 8)    |
| Ensayo de la sustentación presencial (demo en local)             | [PENDIENTE] (Fase 9)    |

---

## 19. Git y publicación

**Estado (17 oct) [OBSERVADO]:** rama `main`, al día con `origin/main`. Hay archivos en staging (backend y frontend de fases anteriores) y otros modificados sin staging; sin seguimiento, entre otros: `backend/app/config/`, `core/database.py`, `llm/embeddings.py`, `repositories/models.py`, `services/ingestion.py`, `scripts/ingest_corpus.py`, `backend/datatutor_pre_reembedding.dump`, todo el frontend de Vite (`package.json`, `package-lock.json`, `index.html`, `vite.config.js`, `.oxlintrc.json`, `src/App.jsx`, `main.jsx`, `styles.css`, `services/api.js`), `frontend/.gitignore`, `frontend/README.md` y `Guia_definitiva_TutorDatos.md`.

**Qué se sube y qué no:**

- Sí: código, `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, `.env.example` (raíz y frontend), `docs/`, `keycloak/import/`, `compose.yml`, `eval/questions.jsonl`.
- **No:** `.env`, `frontend/.env`, `*.dump`, `node_modules/`, `dist/`, `backend/.venv`, **los PDFs del corpus**.

**Corpus fuera de GitHub (decisión del 17 oct):** los libros se ponen en `corpus/` y se ingestan localmente, pero no se versionan. Reglas sugeridas para el `.gitignore` raíz:

```gitignore
# Corpus: PDFs con derechos de autor; se ingestan en local, no se versionan
corpus/*
!corpus/.gitkeep
!corpus/README.md

# Volcados de base de datos
*.dump
```

Comprobaciones en Git Bash, antes del primer commit:

```bash
git check-ignore -v .env frontend/.env corpus/ejemplo.pdf backend/datatutor_pre_reembedding.dump
git ls-files corpus
```

- Si `git ls-files corpus` lista PDFs que ya estaban versionados, el `.gitignore` no los des-rastrea. `git rm --cached <archivo>` los saca del índice sin borrarlos del disco. Si ya se empujaron a GitHub, siguen en el historial: reescribirlo es un paso aparte que no debe hacerse a la ligera.
- Hacer `git add` por carpetas y revisar `git status` antes de cada commit; no usar `git add .` a ciegas.

**Plan de commits (3):** backend (`backend/`, `.env.example`, `.gitignore`), frontend (`frontend/`), documentación (`docs/`, guía). Antes de cada commit, `git status` para confirmar qué quedó en staging.

---

## 20. Hoja de ruta

| Fase | Objetivo                                                                                                           | Fecha objetivo | Estado      |
| ---- | ------------------------------------------------------------------------------------------------------------------ | -------------- | ----------- |
| 0    | Repo, estructura, `pyproject` (`uv`), compose (Postgres + Keycloak), `.env.example`, script de verificación | 5 oct          | ✅          |
| 1    | Auditoría del corpus, PyMuPDF, chunking, embeddings, HNSW, ingesta CLI idempotente                                | 5–6 oct       | ✅          |
| 2    | Grafo LangGraph, pruebas con fakes, CLI de chat y evaluación inicial                                              | 6–11 oct      | ✅          |
| 3    | FastAPI, JWT de Keycloak, `/chat`, historial, aislamiento                                                        | 7–13 oct      | ✅          |
| 4    | Subida asíncrona, listar/borrar, estados, cascada                                                                 | 8–16 oct      | ✅          |
| 5    | Frontend: login, chat con fuentes, historial, documentos, errores, logout; corrección de defectos                 | 9–17 oct      | ✅          |
| 6    | Integración local completa, guion de demo (rechazo + subida de la tesis), calibración                            | 17 oct         | 🔄 En curso |
| 7    | Evaluación completa, `bge-m3` vs `nomic-embed-text`, CI, despliegue público fuera del campus                 | 17–18 oct     | 🔄 Pendiente |
| 8    | README, diagrama, documento técnico, diapositivas                                                                 | 17–18 oct     | 🔄 Parcial |
| 9    | Ensayo de sustentación y colchón sin funcionalidades nuevas                                                      | 18 oct         | ⬜          |

---

## 21. Próximas acciones

1. **Git (hoy):** comprobar `.gitignore`, revisar los cambios y preparar commits pequeños; no incluir PDFs ni secretos.
2. **Corpus:** decidir el `scope` de los libros antes de ingerir el resto; respaldar la BD; ingerir los libros restantes por `scripts/ingest_corpus.py`; validar muestra de embeddings.
3. **Pruebas del respaldo léxico** con fakes (sin LLM) y registrar `uv run pytest -v` completo.
4. **Revisar citas y *grounding*** de las respuestas (§15) y la posible falla de "automatización en ML".
5. **Calibración** con `eval/questions.jsonl`; registrar métricas y latencia por nodo.
6. **Demo:** extracto de la tesis con texto seleccionable, subida desde la UI y pregunta sobre su contenido; guion con rechazo incluido; ensayar en local.
7. **Documentación:** README raíz y `docs/08_DOCUMENTO_TECNICO.md` actualizados con arranque local, ingesta, límites, seguridad, flujo RAG y los 14 apartados; integrantes y captura inicial registrados; faltan convertir el documento a PDF y completar URLs públicas y capturas del despliegue.
8. **Despliegue:** publicar frontend en Vercel y backend/pgvector en Render; para la estrategia elegida, verificar URLs públicas y `/health`, pero ejecutar la demo completa localmente porque Keycloak y Ollama locales no son visibles desde internet.
8. **Opcional:** despliegue público y comparación de embeddings, solo si hay tiempo y fuera del campus.

---

## 22. Siguiente prompt para el Gem

> Estamos en DataTutor, Fase 6. Usa este `PROJECT_STATE.md` como contexto inicial, pero inspecciona los archivos reales que te comparta antes de asumir que un parche está aplicado. Hoy: (1) verificar `.gitignore` y el staging antes de los commits (los PDFs del corpus no van a GitHub), (2) decidir el `scope` de los libros del corpus antes de ingerir los restantes, (3) escribir pruebas del respaldo léxico de `grade_context`. No alteres umbrales RAG, no borres ni reingieras datos y no ejecutes comandos destructivos sin mi autorización.

---

## 23. Variables de entorno (nombres; valores locales en `.env`)

`DATABASE_URL`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `OLLAMA_URL`, `OLLAMA_KEEP_ALIVE`, `CHAT_MODEL`, `EMBED_MODEL`, `EMBED_DIM`, `NUM_CTX`, `TEMPERATURE`, `NUM_PREDICT`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`, `SIM_THRESHOLD`, `SIM_LOW`, `MAX_UPLOAD_MB`, `KEYCLOAK_URL`, `KEYCLOAK_JWKS_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_AUDIENCE`, `KC_ADMIN_USER`, `KC_ADMIN_PASSWORD`, `CORS_ORIGINS`, `VITE_API_BASE_URL`, `VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM`, `VITE_KEYCLOAK_CLIENT_ID`, `VITE_MAX_UPLOAD_MB`; solo en Fase 7: `NGROK_AUTHTOKEN`.

No copiar valores secretos a este documento, a `.env.example`, a Git ni a un chat nuevo.

---

## 24. Historial de este documento

- **17 oct (tarde):** fusión de la versión del usuario, la guía definitiva y la evidencia del día. Se retiraron textos obsoletos (defectos de UI abiertos, pytest 4/1 fallando, constantes locales de umbral). Se añadieron: runbook condensado, contrato de API, modelo de datos, incidencias resueltas, riesgos priorizados, seguimiento de requisitos, política de Git y corpus, y el respaldo léxico con sus limitaciones.
