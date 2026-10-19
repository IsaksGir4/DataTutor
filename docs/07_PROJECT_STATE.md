# PROJECT_STATE — DataTutor

> Documento vivo y fuente de contexto del proyecto. Actualizarlo al cerrar cada fase o tras cambios relevantes, y pegarlo al inicio de cada chat nuevo con el Gem. Si el estado pegado difiere de los archivos de conocimiento, prevalece este estado para el contexto de la conversación; los archivos actuales del repositorio siguen siendo la fuente de verdad sobre qué código está realmente implementado.
>
> **Última actualización:** 18 oct 2026 (noche, rama `evilnightmare010-analyze-agent-project`, URLs públicas registradas) · **Fase actual:** 6 cerrada en local; 7 (despliegue/evaluación) y 8 (documentación) en cierre final · **Entrega del trabajo:** 18 oct 2026 (hoy).
>
> **Etiquetas de certeza** usadas en este documento: **[PROBADO]** hay salida de una prueba o comando pegada en el chat · **[OBSERVADO]** visto en la UI, en la BD, en GitHub o en logs · **[IMPLEMENTADO]** el código se aplicó pero no hay prueba dedicada · **[HIPÓTESIS]** explicación plausible, sin demostrar · **[PENDIENTE]** falta hacerlo o verificarlo.
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
- Anexo A. Despliegue público (Render + Vercel)

---

## 1. Resumen ejecutivo

**Qué es.** DataTutor es el "Trabajo Agente" de la materia de **Integración e Implementación de Software**: una aplicación web con un asistente RAG para ingeniería y ciencia de datos, con agente LangChain + LangGraph, modelo local (Ollama), base vectorial PostgreSQL + pgvector, autenticación Keycloak (OIDC + PKCE), backend FastAPI y frontend React. Responde solo con lo que respalda el corpus, cita sus fuentes y rechaza explícitamente lo que no puede sustentar. Equipo de 3 integrantes (el enunciado PDF §1.3 indica individual o parejas, pero el profesor autorizó un máximo de 3 integrantes).

**Qué funciona hoy.**

- **[PROBADO]** Backend protegido con JWT, aislamiento por usuario, subida/listado/borrado de PDFs con estados, historial de conversaciones y `pytest` (10 pruebas; última corrida: `10 passed in 4.74s`).
- **[PROBADO]** Separación de entornos: `.env` local restaurado apuntando al PostgreSQL de Docker (`127.0.0.1:5432/datatutor`), y credenciales de nube aisladas en `.env.render` (ignorado por `.gitignore` mediante `.env.*`).
- **[PROBADO]** Validador `normalize_database_url` en `backend/app/config/settings.py`: convierte `postgres://` y `postgresql://` a `postgresql+psycopg://` sin alterar la URL local.
- **[PROBADO]** Índice vectorial `idx_embedding_hnsw` (`postgresql_using="hnsw"`) confirmado en `backend/app/repositories/models.py` (líneas 108–111), por lo que `init_database()` crea tablas e índice HNSW automáticamente en una base vacía como la de Render.
- **[OBSERVADO]** Login con Keycloak, chat con fuentes (documento, página, similitud, fragmento), rechazo de preguntas fuera de dominio, historial recuperable, polling de documentos.
- **[OBSERVADO en BD, 18 oct]** Corpus indexado en el PostgreSQL local: **7 documentos, 7 932 chunks** (6 documentos globales con 7 562 chunks, incluido `Python programming for Data analysis` con 535 chunks, y 1 documento de usuario con 370 chunks perteneciente a `estudiante`). Detalle en §12.

**Qué cambió el 18 oct (rama `evilnightmare010-analyze-agent-project`, commits `22f64a0`, `0553f78`, `bb8813d` y `bd3db88`).** `README.md` raíz, rediseño del frontend con identidad de Ingeniería de Datos y posterior estética ciberpunk oscura con rojo neón, mejoras de accesibilidad y diseño responsive, mascota robótica animada, estado conversacional `Pensando...`, bloqueo de envío mientras hay PDFs en `pending`/`processing`, recuperación híbrida vectorial + textual para documentos recién cargados, filtro de documentos `ready`, `render.yaml`, `frontend/vercel.json`, `docs/08_DOCUMENTO_TECNICO.md` y `docs/09_GUIA_DESPLIEGUE.md`, captura en `docs/evidencias/aplicacion-actual.png`, `init_database()` en `core/database.py`, `llm/chat.py` leyendo el modelo y parámetros desde `settings` y metadatos oficiales `DataTutor`.

**Qué falta.** Ejecutar el runner de evaluación con métricas sobre `eval/questions.jsonl`, completar la tabla de corpus y exportar el documento técnico a PDF, diagrama gráfico, diapositivas y ensayo de la demo con el extracto de la tesis. Las URLs públicas ya están registradas y verificadas para carga del frontend y salud del backend.

**Riesgos principales (detalle en §17).**

1. **Consolidación documental pendiente (`07_PROJECT_STATE.md`):** debe confirmarse y subirse a `origin/evilnightmare010-analyze-agent-project`; no se debe asumir que estos cambios están en `main`.
2. **El despliegue público no puede ser funcional de extremo a extremo:** Render y Vercel no alcanzan el Ollama ni el Keycloak locales. Solo `GET /api/v1/health` y la interfaz estática en Vercel son demostrables públicamente; la demo completa debe ser local (Anexo A).
3. Las respuestas no siempre muestran citas `[n]` en línea y el modelo de 3B puede usar conocimiento propio fuera del contexto.
4. Latencia de 12–33 s por consulta (solo CPU).
5. Falta evaluación con métricas (requisito del documento técnico y del proyecto).

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
- **El `.env` de la raíz es exclusivamente para el entorno local.** Los valores de Render se guardan en `.env.render` (como respaldo local ignorado por Git) y se configuran en el panel *Environment* de Render; nunca se mezclan en el `.env` raíz (§16, incidencia del 18 oct).
- No pegar contraseñas reales en chats ni en documentos; enmascararlas.

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
FastAPI  [http://127.0.0.1:8000/api/v1](http://127.0.0.1:8000/api/v1)                                   │ JWKS (127.0.0.1)
  controllers → services → agents (LangGraph) / repositories ◄──────────┘ valida RS256
     │                          │
     │                          └──► Ollama nativo  127.0.0.1:11434
     │                               qwen2.5:3b (clasificar, juez, reescribir, responder)
     │                               bge-m3 (embeddings, 1024 dim)
     ▼
PostgreSQL 16 + pgvector  127.0.0.1:5432   (DB datatutor; Keycloak usa la DB keycloak)

```

* Puertos: 5173 (Vite, estricto), 8000 (FastAPI), 8080 (Keycloak), 5432 (PostgreSQL), 11434 (Ollama).
* Contenedores Docker: `datatutor-postgres`, `datatutor-keycloak`. Volumen de datos: `datatutor-pgdata`.
* Separación IPv4/identidad: el navegador usa `localhost` (coincide con `redirectUris`, `webOrigins` y el claim `iss`); backend ↔ Keycloak/API usan `127.0.0.1` para evitar la demora IPv6 en Windows.
* **Despliegue público registrado (Anexo A):** frontend en [Vercel](https://data-tutor.vercel.app/), backend en [Render](https://datatutor.onrender.com) y health check en [`/api/v1/health`](https://datatutor.onrender.com/api/v1/health). Keycloak y Ollama permanecen locales, por lo que la demo completa es local.

---

## 4. Entorno local y arranque

Runbook condensado; el detalle y las comprobaciones están en la guía definitiva y en el `README.md` raíz.

**Orden de arranque (cada sesión):**

1. Abrir Docker Desktop y esperar al motor. `docker start datatutor-postgres datatutor-keycloak` si están detenidos (o `docker compose up -d` desde la raíz). No recrearlos a ciegas.
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
6. Pruebas del backend: `uv run pytest -v`. Frontend: `npm run lint` y `npm run build`.

**Apagado:** salir de los clientes, `Ctrl+C` en `ollama serve`, `docker stop datatutor-keycloak datatutor-postgres`. Nunca `-v`.

**Notas del entorno:**

* **GPU:** el usuario reporta que su GPU está dañada. Ollama falla en GPU (`CUDA error: an illegal instruction was encountered`, Ollama 0.40.0). CPU-only es la configuración definitiva de este equipo, no un workaround temporal.
* **PostgreSQL nativo:** el servicio `postgresql-x64-17` de Windows ocupó el puerto 5432; se dejó detenido y deshabilitado. Si reaparece un fallo de conexión, comprobar primero ese servicio.
* **Credenciales:** contraseñas de desarrollo local solo (laboratorio); viven en `.env` y deben coincidir con `settings.py`. No copiarlas a este documento, a Git ni a un chat.
* **Docker Hub:** si falla un `pull` por credenciales, `docker logout` y reintentar.

---

## 5. Decisiones técnicas vigentes

| Área | Decisión |
| --- | --- |
| Sistema | Windows; repo en `C:\Users\HP\Desktop\2026-2\Integracion e implementacion Soft\TutorDatos` |
| Backend | Python 3.12.7 + FastAPI + `uv`, ejecutado desde PyCharm; SQLAlchemy 2.0 |
| Agente | LangChain + LangGraph con `StateGraph` explícito |
| LLM | `qwen2.5:3b` en Ollama, CPU (`temperature` 0.0, `num_ctx` 4096, `num_predict` 512; leídos desde `settings` mediante `CHAT_MODEL`, `NUM_CTX`, `TEMPERATURE` y `NUM_PREDICT`) |
| Embeddings | `bge-m3`, 1024 dimensiones |
| Datos | PostgreSQL 16 + pgvector en Docker; índice HNSW (`idx_embedding_hnsw` en `models.py`); `ON DELETE CASCADE` en `messages` y `chunks` |
| Autenticación | Keycloak 24, OIDC Authorization Code + PKCE S256; cliente público `datatutor-web` (sin Direct Access Grants); backend valida JWT RS256 (`iss` = `http://localhost:8080/realms/datatutor`, `aud` = `datatutor-web`, `exp`) con JWKS por `127.0.0.1` |
| Frontend | React + Vite + `keycloak-js`; token en memoria (no `localStorage`); linter Oxlint; rediseño visual de Ingeniería de Datos (`DataTutor`) |
| PDF | PyMuPDF (`fitz`), extracción por página; splitter por página (1000/200) |
| Cliente de pruebas | `datatutor-swagger` con Direct Access Grants, solo para scripts de consola |
| Ingesta | Libros completos por `scripts/ingest_corpus.py`; la subida web, para extractos de ~5–30 páginas |
| Despliegue | Frontend en Vercel, backend (`plan: free`) y PostgreSQL+pgvector en Render; demo completa en local (Keycloak y Ollama no son accesibles desde internet). Ver Anexo A |
| Corpus en Git | Los PDFs no se versionan; en el repositorio solo `corpus/.gitkeep` y `corpus/README.md` |
| Equipo | 3 integrantes (máximo permitido por el profesor; difiere del texto original de `trabajo_agente.pdf` §1.3 que indicaba individual o parejas) |

---

## 6. Configuración y parámetros RAG

**Parámetros (unificados en `settings.py` y `.env`):** `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `TOP_K=4`, `SIM_THRESHOLD=0.65`, `SIM_LOW=0.50`, `MAX_UPLOAD_MB=30`.

* **[OBSERVADO]** Un script de diagnóstico imprimió `THRESHOLD: 0.65` leyendo `settings`; `SIM_THRESHOLD` **no** es importable desde `core.py` (vive en `settings`).
* **[IMPLEMENTADO]** `core.py` y `graph.py` consumen `settings.TOP_K`, `settings.SIM_THRESHOLD` y `settings.SIM_LOW` como única fuente.
* **[IMPLEMENTADO]** `app/llm/chat.py` consume `CHAT_MODEL`, `NUM_CTX` y `NUM_PREDICT` desde `settings`, los cuales están declarados con valores por defecto en `backend/app/config/settings.py`.
* **[PROBADO]** `settings.py` incluye `@field_validator("DATABASE_URL")` (`normalize_database_url`), que reescribe prefijos `postgres://` y `postgresql://` a `postgresql+psycopg://` sin alterar la cadena local.

**Archivos de entorno:**

* `TutorDatos/.env`: backend y servicios **locales** (`PostgreSQL` en Docker local); secretos locales; no se versiona.
* `TutorDatos/.env.render`: copia local de referencia con los valores dirigidos a Render; cubierta por la regla `.env.*` de `.gitignore` para no mezclarla con el `.env` de desarrollo.
* `TutorDatos/.env.example`: plantilla sin secretos.
* `TutorDatos/frontend/.env`: variables de Vite; solo públicas con prefijo `VITE_`.
* `TutorDatos/frontend/.env.example`: plantilla de las variables públicas.
* **Regla operativa crítica:** **Nunca** sustituir `DATABASE_URL`, `DB_USER`, `DB_PASSWORD` ni `DB_NAME` del `.env` local por los de Render: si el backend local lee la base vacía de Render, deja de ver los 7 932 chunks locales, `pytest` inserta filas de prueba en la nube y `compose.yml` altera las variables de arranque de Postgres/Keycloak.
* El frontend no necesita contraseñas de PostgreSQL, credenciales de Keycloak admin ni parámetros de Ollama. Backend y frontend se configuran por separado (el backend lee el `.env` raíz mediante `PROJECT_ROOT`).
* `CORS_ORIGINS` es una lista separada por comas (`cors_origins_list` usa `split(",")`); debe incluir `http://localhost:5173` y, en Render, el origen exacto de Vercel sin `/` final (`https://tu-app.vercel.app,http://localhost:5173`).
* Se corrigió en el `.env` raíz una `KEYCLOAK_JWKS_URL` que traía sintaxis Markdown (`[url](url)`) y barras invertidas copiadas de un chat; el esquema resuelto apareció como `http`.

---

## 7. Versiones registradas

Copiadas del estado previo (`uv pip list`). Volver a comprobarlas con los comandos de cada gestor si se actualizan dependencias. No cambiar versiones solo para resolver un problema.

**Backend:** `fastapi==0.142.2`, `uvicorn==0.54.0`, `pydantic==2.13.5`, `pydantic-settings==2.15.0`, `sqlalchemy==2.1.3`, `psycopg==3.3.6`, `pgvector==0.5.0`, `langchain==1.4.3`, `langchain-core==1.6.7`, `langchain-ollama==1.1.0`, `langgraph==1.2.14`, `pymupdf==1.28.2`, `pyjwt==2.15.1`, `cryptography==50.0.2`, `httpx==0.28.1`, `pytest==9.1.1`, `ruff==0.16.10`.

**Frontend:** `react@19.3.1`, `react-dom@19.3.1`, `keycloak-js@26.2.4`, `vite@8.3.4`, `@vitejs/plugin-react@6.1.2`, `oxlint@1.88.0`, `@types/react@19.3.0`, `@types/react-dom@19.3.0`.

* **[OBSERVADO]** El frontend se reinstaló el 16 oct con `npm create vite@latest` + `npm install --ignore-scripts` (25 packages have verified registry signatures, 15 packages have verified attestations) y se añadió `keycloak-js`.

**npm list --depth=0**

```text
frontend@0.0.0 C:\Users\HP\Desktop\2026-2\Integracion e implementacion Soft\TutorDatos\frontend
├── @types/react-dom@19.3.0
├── @types/react@19.3.0
├── @vitejs/plugin-react@6.1.2
├── keycloak-js@26.2.4
├── oxlint@1.88.0
├── react-dom@19.3.1
├── react@19.3.1
└── vite@8.3.4

```

**npm audit signatures**

```text
audited 25 packages in 3s
25 packages have verified registry signatures
15 packages have verified attestations

```

---

## 8. Estructura del repositorio

Confirmar contra el árbol real antes de añadir o mover archivos. Raíz tras el merge `77a6ac2` del 18 oct.

```text
TutorDatos/
├── .env  .env.render (no versionados)  .env.example  .gitignore  .python-version  compose.yml
├── README.md                     # integrado en main (rama del equipo)
├── render.yaml                   # ajustado a plan: free y sync: false (pendiente git add/commit)
├── audit_corpus.py               # script de auditoría de PDFs (resultados no registrados)
├── corpus/                       # PDFs locales; NO se versionan. En Git: .gitkeep y README.md
├── docker/postgres/init/01-keycloak-db.sql
├── docs/
│   ├── 01 … 07                   # 07 = este documento
│   ├── 08_DOCUMENTO_TECNICO.md   # fuente editable del PDF final (14 apartados)
│   ├── 09_GUIA_DESPLIEGUE.md     # Render/Vercel y guion de pruebas manuales
│   ├── Guia_definitiva_TutorDatos.md
│   └── evidencias/aplicacion-actual.png
├── keycloak/import/datatutor-realm.json
├── backend/
│   ├── pyproject.toml  uv.lock
│   ├── app/
│   │   ├── main.py               # lifespan: fail_interrupted_documents; metadatos DataTutor
│   │   ├── agents/               # graph.py, prompts.py, state.py, nodes/core.py
│   │   ├── config/settings.py    # normalize_database_url (pendiente git add/commit)
│   │   ├── controllers/          # chat.py, documents.py
│   │   ├── core/                 # database.py (init_database), deps.py, errors.py, security.py
│   │   ├── llm/                  # chat.py (lee de settings), embeddings.py
│   │   ├── repositories/         # models.py (incluye idx_embedding_hnsw), chat_repo.py, document_repo.py
│   │   ├── schemas/              # chat.py, document.py
│   │   ├── services/             # chat.py, documents.py, ingestion.py
│   │   └── vectorstore/retriever.py
│   ├── eval/questions.jsonl
│   ├── scripts/                  # verificar_entorno, ingest_corpus, chat_cli, test_api, test_documents
│   └── tests/test_api_contracts.py
└── frontend/
    ├── .env (no versionado)  .env.example  package.json  package-lock.json  vite.config.js  index.html  .oxlintrc.json
    ├── vercel.json               # integrado en main: SPA en Vercel
    └── src/  main.jsx  App.jsx  styles.css  services/{auth.js, api.js}

```

---

## 9. Contrato de la API

Prefijo `/api/v1`. Todas las rutas, salvo `/health`, exigen `Authorization: Bearer <JWT>`; el aislamiento usa `owner_id = sub`.

| Método y ruta | Función | Códigos relevantes |
| --- | --- | --- |
| `GET /health` | Salud (pública) | 200 |
| `GET /me` | Perfil del token (`sub`, `preferred_username`, `roles`) | 200, 401 |
| `POST /chat` | Un turno: `{question, conversation_id?}` → `{conversation_id, answer, decision, sources[], latency_ms}` | 200, 401, 422, 503 |
| `GET /conversations` | Conversaciones propias, recientes primero | 200 |
| `GET /conversations/{id}/messages` | Mensajes (`role`, `content`, `decision`, `sources`, `best_score`, `latency_ms`) | 200, 404 |
| `DELETE /conversations/{id}` | Borra conversación y mensajes (cascada) | 204, 404 |
| `POST /documents` | Subida `multipart/form-data`; procesa en segundo plano | 202, 409, 413, 415 |
| `GET /documents` | Documentos propios y globales | 200 |
| `GET /documents/{id}` | Detalle | 200, 404 |
| `DELETE /documents/{id}` | Borra documento propio (no globales) y chunks | 204, 404 |

**Reglas del contrato:**

* Pregunta de 2 a 2000 caracteres; en blanco → 422.
* `decision` ∈ `answered`, `rejected`, `clarify`, `smalltalk`. **Un rechazo del agente es HTTP 200** con `decision = "rejected"`; no es un error de infraestructura.
* Errores: `{ "error": { "code", "message", "request_id" } }`. El 503 `agent_error` incluye `conversation_id` para que el frontend fije la conversación activa y no cree duplicados al reintentar.
* **Limitación conocida:** el envío no es idempotente. Reintentar la misma pregunta tras un 503 reutiliza la conversación pero inserta otro mensaje `user`.
* Conversación ajena o inexistente → 404 (no se revela su existencia).
* Estados de documento: `pending` → `processing` → `ready` | `failed`. `ready` con 0 chunks no existe: un PDF sin texto seleccionable queda `failed`.
* Mensaje obligatorio de rechazo (observado): "No tengo suficiente información en mi base de conocimiento para responder esa pregunta. Te sugiero cargar documentos relacionados con el tema."

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

| Condición | Comportamiento |
| --- | --- |
| `best_score < SIM_LOW` (0.50) | Contexto insuficiente, sin llamar al juez |
| `SIM_LOW ≤ score < SIM_THRESHOLD`, primer intento | Insuficiente, sin juez |
| `SIM_LOW ≤ score < SIM_THRESHOLD`, tras reescribir | El juez LLM evalúa |
| `score ≥ SIM_THRESHOLD` | El juez LLM evalúa; si no responde `true`, entra el respaldo léxico |

* El juez evalúa sobre `state["question"]`. Un JSON inválido o una clave no booleana cuenta como "no suficiente" (nunca como éxito).
* **Respaldo léxico (17 oct) [IMPLEMENTADO, OBSERVADO en logs]:** si el juez no devuelve `sufficient: true`, se acepta el contexto solo si `best_score ≥ SIM_THRESHOLD` **y** `_has_direct_lexical_evidence` es verdadero: al menos 2 términos específicos de la pregunta (≥ 5 letras, sin stopwords ni términos genéricos como "bases" o "datos") presentes en los chunks y que representen ≥ 35 % de los términos específicos de la pregunta.
* **Motivo:** el juez `qwen2.5:3b` rechazaba la pregunta de normalización pese a recuperar fragmentos de Silberschatz (págs. 181, 182, 27, 28; score máx. 0.706). Reescribir `GRADER_PROMPT` no lo corrigió. Los descartes previos fueron: propietario (`owner_id` coincide en documentos y chunks), codificación y falta absoluta de evidencia.
* **Limitaciones [HIPÓTESIS]:** es una heurística léxica; puede aceptar contexto débil con términos coincidentes; con preguntas en español y fragmentos en inglés (p. ej. *Fundamentals of Data Engineering*) rara vez coincidirá, así que no ayuda ahí; no rescata contextos por debajo de `SIM_THRESHOLD`.


* **Recuperación tras carga de PDF [IMPLEMENTADO]:** la búsqueda combina similitud vectorial con coincidencias textuales controladas de términos específicos y solo consulta fragmentos de documentos en estado `ready`. Esto cubre nombres propios, títulos y conceptos breves que pueden quedar por debajo del umbral semántico, sin convertir por sí sola una coincidencia textual en una respuesta válida.
* **[PENDIENTE]** `rewrite_query` sigue produciendo consultas casi idénticas a la original, de modo que el segundo `retrieve` recupera prácticamente lo mismo. No mezclarlo con otro cambio de comportamiento.
* **[PENDIENTE]** La ruta `clarify` por score quedó sustituida por la regla de longitud (≤ 4 palabras). Revisar casos de borde en la calibración.
* Historial: el servicio pasa al agente las últimas 6 interacciones y persiste cada turno (mensaje de usuario antes de invocar el grafo; respuesta después). El título de la conversación es `question[:40]`.
* `save_history` dejó de ser un paso ficticio: la persistencia real ocurre en `services/chat.py` **[OBSERVADO en BD]**.

---

## 11. Modelo de datos e ingesta

**Tablas relevantes:** `documents` (`id`, `filename`, `scope`, `owner_id`, `status`, `pages`, `chunks_count`, `size_bytes`, `error`, `sha256`, `created_at`), `chunks` (texto, página, `embedding vector(1024)`, `embed_model`, `owner_id`, `document_id`), `conversations`, `messages`.

* Restricción `uix_owner_sha256`: el mismo PDF no se duplica **por propietario**. Un mismo archivo sí puede existir como `global` y como `user` a la vez.
* `ON DELETE CASCADE` verificado en `pg_constraint` para `messages_conversation_id_fkey` y `chunks_document_id_fkey` **[PROBADO]**.
* **Índice HNSW confirmado en `models.py` [PROBADO el 18 oct]:** `grep -n "hnsw|Index(" backend/app/repositories/models.py` verificó que `idx_embedding_hnsw` (`postgresql_using="hnsw"`, líneas 108–111) y los índices B-Tree (líneas 66, 103, 150, 200) están declarados en los modelos ORM.
* Búsqueda: `Chunk.owner_id IN ('global', <sub>)`, documento en estado `ready`, distancia coseno, `TOP_K = 4`.
* `fail_interrupted_documents` en `lifespan`: al arrancar marca como fallidos los documentos `pending`/`processing`. Precaución: un reinicio con `--reload` interrumpe una ingesta en curso; no ingerir libros grandes por la web.
* Un PDF que extrae 0 chunks pasa a `failed`.
* **`init_database()` (`core/database.py`) [PROBADO]:** crea la extensión `vector` y las tablas/índices ORM (`Base.metadata.create_all`, incluido `idx_embedding_hnsw`) si la base está vacía. Motivo: una base nueva en Render arrancaba sin tablas y el backend fallaba con `relation does not exist`. Verificado que sobre la base local con datos es inocuo (`pytest` 5/5 en 2.17 s).

**Lección del re-embedding (Fase 1–2):** el campo `embed_model='bge-m3'` no prueba que el vector se haya generado con ese modelo. Los 57 chunks iniciales tenían coseno `-0.056` contra una regeneración fresca; tras regenerarlos en sitio fue `1.000000`. Tras una ingesta grande, validar una muestra (coseno almacenado vs. regenerado, sin nulos ni normas cero) en vez de asumir que está bien.

**Respaldo antes de cambios de BD** (desde `backend/`, PowerShell):

```powershell
$backup = "datatutor_$(Get-Date -Format yyyyMMdd_HHmmss).dump"
docker exec datatutor-postgres pg_dump -U postgres -d datatutor -Fc -f "/tmp/$backup"
docker cp "datatutor-postgres:/tmp/$backup" ".\$backup"

```

Existe `backend/datatutor_pre_reembedding.dump` (298 kB, anterior al re-embedding; no sobrescribir). Los `.dump` no se versionan. Para practicar una restauración, usar una base nueva (`datatutor_restore_test`) y no la activa. **[PENDIENTE]** Hacer un respaldo nuevo del estado actual (7 932 chunks) antes de cualquier cambio de datos.

---

## 12. Corpus

**Plan por olas (según el estado previo):**

* **Ola 1:** Silberschatz (BD, español); *Fundamentals of Data Engineering Concepts* (inglés); *Libro GUIA ingeniería de datos* (español); *Fundamentos de Ingeniería de Datos* (español, ~38 KB, prueba de humo); *Principles of Data Science* (inglés); *Seven ways…* (inglés); *Understanding… failure* (inglés).
* **Ola 2:** *EDR teoría BD*; *Big Book of Data Warehousing and BI*; *Python programming for Data Analysis*; `INTELIGENCIA_ARTIFICIAL`; `Data science route`.
* **Fuera de v1:** *Geometric Data Science book*.
* **Reservada para la demo en vivo:** tesis sobre control predictivo no lineal basado en modelo borroso; usar un extracto de ~30 páginas con texto seleccionable, no el libro completo.
* **[PENDIENTE]** La auditoría consolidada de PDFs (páginas, caracteres por página, texto seleccionable) no está registrada. Existe `audit_corpus.py` en la raíz del repositorio; registrar su salida.

**Indexado hoy (`status = ready`) [OBSERVADO en BD, consulta del 18 oct]:**

| Documento | scope | owner_id | págs | chunks |
| --- | --- | --- | --- | --- |
| Fundamentals-of-Data-Engineering-Concepts | global | `global` | 219 | 693 |
| Silberschatz, Fundamentos de BD 6ª ed. | global | `global` | 673 | 4 957 |
| Fundamentos-de-Ingeniería-de-Datos | global | `global` | 16 | 16 |
| Libro GUIA ingenieria de datos | global | `global` | 544 | 1 320 |
| Python programming for Data analysis | global | `global` | 271 | 535 |
| Seven ways to make a data science project fail | global | `global` | 5 | 41 |
| INTELIGENCIA_ARTIFICIAL | user | `aaaaaaaa-0000-0000-0000-000000000002` (`estudiante`) | 144 | 370 |
| **Total** |  |  |  | **7 932** (global 7 562 + usuario 370) |

* **[OBSERVADO]** El corpus completo está solo en la base local (volumen Docker) y en `corpus/` en disco. No hay PDFs en GitHub; en el repositorio solo existe `corpus/README.md` (más `.gitkeep`).
* **Visibilidad (corrección del 18 oct):** los 6 libros principales (Silberschatz, Fundamentals, Libro GUIA, Python programming for Data analysis, Seven ways y Fundamentos de Ingeniería de Datos) **son globales** (`7 562 chunks`): cualquier cuenta los ve. La nota antigua de "tres libros solo visibles para un usuario" era falsa y quedó corregida. Solo `INTELIGENCIA_ARTIFICIAL` (370 chunks) es `scope = user` y pertenece al `sub` `aaaaaaaa-0000-0000-0000-000000000002` (usuario `estudiante` sembrado en `keycloak/import/datatutor-realm.json`).
* **[OBSERVADO]** `SELECT owner_id, count(*) FROM conversations GROUP BY owner_id` devolvió 3 conversaciones de `aaaaaaaa-0000-0000-0000-000000000002` y 1 de un usuario `pytest-503-user-…`. Es decir, las pruebas de chat en la UI se hicieron con el usuario `estudiante`, dueño del libro de IA, así que el libro **sí era visible** y el rechazo de "automatización en ML" (0.550) **no se explica por visibilidad**. **[PENDIENTE]** revisar los chunks recuperados para decidir si es falso negativo del retriever/juez o una respuesta legítimamente sin evidencia en ese PDF.
* **Riesgo de duplicados (vigente):** si se vuelve a ingerir como `global` un libro ya indexado como `user` (o al revés), el retriever devolvería ambas copias. Hoy solo `INTELIGENCIA_ARTIFICIAL` es de usuario y no existe copia global.
* **Decisión opcional:** convertir `INTELIGENCIA_ARTIFICIAL` a `global` actualizando `documents.scope`, `documents.owner_id` y `chunks.owner_id` de forma coherente, en una transacción y con respaldo previo, para que también lo vea el usuario `admin` o cuentas recién registradas. Requiere autorización explícita.
* Libros del plan que **no aparecen** en la tabla al 18 oct: *Principles of Data Science*, *Understanding… failure*, *EDR teoría BD*, *Big Book of Data Warehousing and BI*. `Data science route.pdf` se eliminó tras comprobar que no tenía texto seleccionable (0 chunks). Documentarlos como fuera de alcance de la v1 o ingerirlos solo si hace falta.
* **Política de repositorio:** los PDFs no se suben a GitHub. La base vive en el volumen Docker y se reproduce con el script; `corpus/README.md` documenta los nombres esperados.

---

## 13. Frontend

* **Auth:** `src/services/auth.js` con instancia `keycloak-js` y `initPromise` singleton (evita el doble `init()` de `React.StrictMode`); `onLoad: "login-required"`, `pkceMethod: "S256"`, `checkLoginIframe: false`; `getValidToken()` llama a `updateToken(30)` antes de cada petición.
* **API:** `src/services/api.js` adjunta el `Bearer`; no fija `Content-Type` cuando el cuerpo es `FormData` (el navegador añade el `boundary`); traduce el sobre de error del backend. Los enlaces Markdown (`[url](url)`) que se colaron en código copiado deben ser URLs simples.
* **App:** barra lateral con usuario, nuevo chat, historial de conversaciones (seleccionar/borrar), subida de PDFs y lista de documentos con estado. Área principal con mensajes, insignias por decisión (`answered` verde, `clarify` azul, `rejected` rojo/ámbar, `smalltalk` gris), fuentes y latencia, banner de errores.
* **Polling y bloqueo durante indexación:** si hay documentos `pending`/`processing`, `GET /documents` cada 3 s hasta que todos sean terminales; mientras un PDF está en `pending` o `processing`, el frontend bloquea el envío de nuevas preguntas y muestra el estado de indexación.
* **Botón de borrar documento:** solo para `scope = user` y estado no activo; la restricción real vive en el backend (404 o 409 en la capa de servicio/repositorio).
* **Historial sin texto (resuelto):** `MessageItem` no exponía `content`. Se añadió `content: str` y `sources` en `schemas/chat.py`; verificado en UI y en pytest. Respaldo en `App.jsx`: `{m.content || m.answer || m.text || "(Mensaje sin contenido de texto)"}` dentro de `<div className="message-body">` **[PROBADO]**.
* **Build:** `vite build` probado después del rediseño ciberpunk y de la mascota (`vite build` correcto; 523 ms en la última corrida). `npm run lint` finaliza sin errores y conserva únicamente advertencias preexistentes.
* **Origen:** acceder siempre por `http://localhost:5173`. `redirectUris` y `webOrigins` del realm solo lo permiten, y la API criptográfica de PKCE requiere contexto seguro. En Vercel, `login-required` redirigiría a un Keycloak público que hoy no existe (Anexo A).

**Mejoras integradas el 18 oct en el merge `77a6ac2` (`frontend/index.html`, `frontend/src/App.jsx`, `frontend/src/styles.css`, `backend/app/main.py`) [IMPLEMENTADO]:**

* Rediseño del frontend con identidad futurista de Ingeniería de Datos: tipografías técnicas, paneles de sistema, flujo visual `INGEST → EMBED → RETRIEVE → ANSWER`, fondo de cuadrícula y estados visuales conservando las funciones existentes.
* Estandarización del nombre visible y técnico del agente como **DataTutor** en interfaz, título del navegador (`index.html`) y metadatos de FastAPI (`main.py`).
* Estados visuales de autenticación y carga con `aria-live`, spinner y mensajes de error con `role="alert"`.
* Etiquetas accesibles y foco visible para controles de chat, subida, eliminación, logout y selección de conversaciones.
* Las conversaciones se pueden seleccionar también con teclado (`Enter` o espacio).
* Estado vacío explícito cuando no hay conversaciones o documentos.
* Layout responsive para pantallas medianas y móviles, y respeto por `prefers-reduced-motion`.
* Se registraron los tres integrantes en `docs/08_DOCUMENTO_TECNICO.md` y se incorporó la captura de la aplicación en `docs/evidencias/aplicacion-actual.png`.
* Se preparó `render.yaml` para Render y `frontend/vercel.json` para la SPA de Vercel.
* Se añadió `docs/09_GUIA_DESPLIEGUE.md` con el procedimiento de Render/Vercel y el guion de pruebas manuales.
* Se evolucionó la identidad visual a un estilo **ciberpunk oscuro** con rojo neón, scanlines, brillos y paneles granate.
* Se añadió una mascota robótica propia de DataTutor, construida con HTML/CSS y animaciones ligeras: antena, pantalla, ojos, chip `DT`, flotación, parpadeo y línea de escaneo.
* Se añadió el estado **“Pensando...”** mientras el backend responde. La mascota compacta aparece en un bloque independiente encima del texto para evitar solapamientos, incluso en pantallas pequeñas.
* Se incorporó una prueba del respaldo léxico para preguntas sobre conceptos específicos, como el principio de Newell; la suite pasó de 5 a 6 pruebas.

---

## 14. Seguridad y cadena de suministro

* **npm (oct 2026):** hay campañas activas de malware y typosquatting en el registro (p. ej. MALFEX, el gusano de `tensorlake`, paquetes que imitan a `nestjs`, `vite` o `keycloak-js`) y un fallo de Trusted Publishing con más de 1 500 paquetes expuestos. No se encontró un aviso contra `react`, `react-dom`, `vite`, `@vitejs/plugin-react` ni `keycloak-js`, pero eso no garantiza que estén limpios.
* **Reglas:** nombres exactos; `npm install --ignore-scripts`; revisar `package-lock.json` en busca de nombres desconocidos; `npm audit` y `npm audit signatures` (esta última no es infalible: un ataque reciente tenía procedencia válida); `npm ci` para reproducir; no tener tokens reales en el entorno de instalación.
* **Secretos:** `.env`, `.env.render`, `frontend/.env` y los `.dump` no se versionan. Las credenciales locales de desarrollo no se copian a documentos ni chats. La guía definitiva menciona valores de desarrollo locales: revisarla antes de hacer público el repositorio.
* **Base de Render:** su cadena de conexión contiene credenciales reales de un servicio en internet. Mantenerla fuera de Git y de los chats (enmascararla al compartir); configurarla en el panel de Render (`sync: false` en `render.yaml`) y localmente solo en `.env.render`. Si alguna vez se pegó sin enmascarar, rotar la contraseña en Render.
* **Keycloak público (si algún día se publica):** el contenedor actual es de desarrollo; no exponer la consola de administración con credenciales por defecto ni usar `start-dev` en producción.
* **Tokens:** el JWT vive en memoria de `keycloak-js` (no en `localStorage`), con renovación preventiva.
* **Autorización:** todo acceso a conversaciones, mensajes y documentos filtra por `owner_id = sub`; un recurso ajeno responde 404.

---

## 15. Validaciones y evidencia

**Por fase:**

* **Fase 0 [PROBADO]:** `scripts/verificar_entorno.py` (PostgreSQL + pgvector, JWKS de Keycloak, Ollama con `qwen2.5:3b` y `bge-m3`).
* **Fases 1–2 [PROBADO]:** ingesta inicial, re-embedding de 57 chunks (coseno 1.000000, 0 nulos, 1024 dim), recuperación (0.7172 en inglés, 0.6825 en español) y CLI `chat_cli.py` con tres casos (pregunta respondible, sin soporte, saludo).
* **Fase 3 [PROBADO]:** `scripts/test_api.py`: JWT, 401 sin token y con token manipulado, `POST /chat` 200, aislamiento 404 entre usuarios.
* **Fase 4 [PROBADO]:** `scripts/test_documents.py`: 202, estado `ready`, listado 200, duplicado 409, validación de embeddings, borrado 204 y cascada.
* **Fase 5 [PROBADO/OBSERVADO]:** `pytest` 5 passed; `vite build` correcto; login OIDC + PKCE, historial con texto, polling, recuperación de documentos interrumpidos y rechazo de PDFs sin texto verificados en UI. El fallo previo de `DataTutorException` sin `conversation_id` se corrigió en `core/errors.py`.
* **Fase 6–7, 18 oct [PROBADO]:**
* Corrida pre-merge con `.env` local restaurado: `5 passed in 2.91s`.
* Prueba del validador `normalize_database_url` en PowerShell (`$env:DATABASE_URL="postgresql://u:p@h/db"`) → imprimió `postgresql+psycopg://u:p@h/db`.
* Verificación de índices en `models.py` (`grep -n "hnsw|Index(" backend/app/repositories/models.py`) → confirmado `idx_embedding_hnsw` (`postgresql_using="hnsw"`, líneas 108–111).
* Corrida de `uv run pytest -v` tras integrar cambios de `settings.py` y la rama del equipo: `5 passed in 2.17s`.
* Corrida posterior a la recuperación híbrida y la prueba de conceptos específicos: `6 passed in 6.88s`.
* Se añadió un respaldo determinista antes del juez LLM: evidencia textual directa en fragmentos `ready` acepta el contexto sin depender de una segunda llamada al modelo.
* Se añadió normalización de tildes y prefijos controlados para recuperar coincidencias como `ingenieria` → `ingeniería`, además de pruebas para preguntas como `ciencia de datos`.
* Se alineó la validación léxica con la búsqueda por prefijos para aceptar variantes morfológicas como `relacional` → `relacionales`; también se corrigió la importación de `json` usada por la clasificación de intención.
* `frontend`: `npm run build` correcto después de la interfaz ciberpunk, la mascota y el estado `Pensando...`; `npm run lint` sin errores.



**Salida de pytest (18 oct, última corrida) [PROBADO]:**

```text
platform win32 -- Python 3.12.7, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\HP\Desktop\2026-2\Integracion e implementacion Soft\TutorDatos\backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\HP\Desktop\2026-2\Integracion e implementacion Soft\TutorDatos\backend
configfile: pyproject.toml
plugins: anyio-4.15.1, langsmith-0.14.4
collected 6 items

tests/test_api_contracts.py::test_health_and_openapi_expose_all_endpoints PASSED                             [ 20%]
tests/test_api_contracts.py::test_protected_endpoints_reject_anonymous PASSED                                [ 40%]
tests/test_api_contracts.py::test_database_foreign_keys_enforce_sql_on_delete_cascade PASSED                 [ 60%]
tests/test_api_contracts.py::test_chat_503_returns_conversation_id_to_avoid_duplicate_conversations PASSED   [ 80%]
tests/test_api_contracts.py::test_conversation_lifecycle_and_cross_user_isolation PASSED                     [100%]

================================ 6 passed in 6.88s ================================

```

**Pruebas de chat del 17 oct (tras el respaldo léxico) [OBSERVADO en UI y en `messages`]:**

| Pregunta | decision | best_score | latencia |
| --- | --- | --- | --- |
| ¿Qué es la normalización… y para qué sirven las formas normales? | answered | 0.706 | 33 039 ms |
| ¿Qué son la segunda y la tercera forma normal? | answered | 0.665 | 32 073 ms |
| ¿Cuál es la mejor receta para preparar sushi? | rejected (fuera de dominio) | 0.000 | 1 295 ms |
| ¿Cómo se configura un clúster de Apache Kafka con ZooKeeper en producción? | rejected | 0.542 | 16 609 ms |
| Que es una automatizacion? | clarify | 0.607 | 13 943 ms |
| Que es una automatizacion en procesos de machine learning? | rejected | 0.550 | 12 617 ms |

* Antes del cambio, la de normalización terminaba en `rejected` (0.678, 29 741 ms). En una corrida anterior Kafka dio 0.614 y 15 540 ms; el `best_score` guardado es el del último intento, tras reescribir, por eso varía.
* **Rechazos correctos:** sushi (sin consultar `pgvector`) y Kafka (sin evidencia en el corpus).
* **Por revisar [HIPÓTESIS]:** "automatización en procesos de machine learning" (0.550). La visibilidad del libro de IA ya está descartada como causa (§12); falta revisar los chunks recuperados.

**Calidad observada del texto generado:**

* Las respuestas **no muestran citas `[n]` en línea**, aunque el prompt de respuesta las exige. Las fuentes aparecen al final, lo que no demuestra que cada afirmación esté respaldada.
* La respuesta de normalización define 1FN y 2FN con contenido que los fragmentos recuperados (por sus extractos) no parecen aportar, y la de 2FN/3FN admite "no hay detalles" para la 2FN. **[HIPÓTESIS]** el modelo de 3B usa conocimiento propio fuera del contexto; verificar con el texto completo de los chunks y una prueba de *grounding*.
* Terminología: en la Guía, una respuesta tradujo mal *unrealistic expectations* ("Realismos inaceptables").

**Latencia:** 12–33 s por consulta en CPU, con varias llamadas al LLM por turno (clasificar, juez, reescribir y responder; el juez puede correr dos veces). Algunas mediciones se hicieron con ingestas en paralelo (se llegó a 42 s). **[PENDIENTE]** medir por nodo y sin carga en paralelo.

**Datos de prueba en la BD de desarrollo [OBSERVADO]:** `conversations` contiene un `owner_id` `pytest-503-user-…` (1 conversación) y `messages` filas asociadas: las pruebas dejan datos en la base real. Pendiente decidir una base de pruebas o limpieza en el teardown; no borrar sin autorización.

**Evidencia visual:** `docs/evidencias/aplicacion-actual.png` (captura inicial). Para el PDF final faltan capturas propias de login, respuesta sustentada, rechazo, carga de documento y despliegue.

---

## 16. Registro de incidencias resueltas

| Incidencia | Causa | Resolución |
| --- | --- | --- |
| `uv` creó el proyecto con Python 3.14 | Versión global distinta de la objetivo | `uv python pin 3.12.7`; no borrar `backend/.venv` |
| Docker no descargaba la imagen | Credenciales guardadas de Docker Hub | `docker logout` y reintento |
| Puerto 5432 ocupado | Servicio `postgresql-x64-17` de Windows | Detenido y deshabilitado |
| Errores de autenticación desde Windows | Discrepancia de credenciales + colisión con PostgreSQL nativo | `ALTER USER` dentro del contenedor; `.env` y `settings.py` sincronizados |
| Ollama fallaba con JSON/GPU | Fallo de inferencia en GPU (la GPU del equipo está dañada) | CPU-only con `CUDA_VISIBLE_DEVICES=-1` y `OLLAMA_LLM_LIBRARY=cpu_avx2` |
| Búsqueda irrelevante con el artículo ya ingerido | Embeddings guardados incompatibles con el modelo actual | Respaldo + re-embedding en sitio de los 57 chunks |
| El CLI ejecutaba el grafo dos veces | Dos bucles sobre `agent_app.stream` | Un solo stream con `stream_mode="updates"` |
| Juez con JSON inválido daba contexto válido | `except` devolvía `context_ok=True` | Ahora `context_ok=False` |
| `clarify` para preguntas claras sin evidencia | Decisión por score tras el reintento | `clarify` solo para consultas de ≤ 4 palabras; resto → `rejected` |
| Pytest: `DataTutorException` sin `conversation_id` | El constructor no lo aceptaba | `errors.py` acepta y serializa el campo |
| Historial sin texto | `MessageItem` sin `content` | Campo añadido en `schemas/chat.py` |
| Documentos atascados en `processing`, `0 págs` | Tareas en segundo plano interrumpidas por `--reload` | `fail_interrupted_documents` en `lifespan`; ingesta de libros por CLI |
| PDF sin texto indexado como `ready` | Extracción con 0 chunks | Se marca `failed` |
| Normalización rechazada con score 0.706 | Falso negativo del juez 3B | Respaldo léxico (§10) |
| `ImportError: SIM_THRESHOLD` en un diagnóstico | La constante vive en `settings`, no en `core.py` | Usar `settings.SIM_THRESHOLD` |
| Código con enlaces Markdown corruptos | Copiado desde un chat | Dejar URLs simples en `api.js`, `.env` y `security.py` |
| `keycloak.js` truncado en un adjunto | Salida cortada | Usar `services/auth.js` completo |
| `npm install` colgado 30 min | Red universitaria | Cambio de red; terminó en 14 s |
| `Remove-Item` no reconocido | Se usaba cmd, no PowerShell | En cmd, `rmdir /s /q` |
| `.gitignore` con `corpus/` y negaciones ineficaces; `.DS_Store*.dump` pegados | Reglas mal formadas | `.gitignore` reparado (`corpus/*` + excepciones); verificado con `git check-ignore -v` |
| Base de Render creada sin tablas | Instalación nueva sin migraciones | `init_database()` (rama del equipo) crea la extensión `vector`, las tablas y el índice HNSW |
| `.env` local apuntaba a la base de Render (18 oct) | Se sustituyeron `DATABASE_URL` y `DB_*` para probar Render | Valores de Render movidos a `.env.render` (ignorado por `.env.*`) y restaurado el `.env` local de Docker |
| `07` afirmaba "tres libros solo visibles para un usuario" | Estado desactualizado frente a la BD | Consulta de `documents` del 18 oct (6 globales = 7 562 chunks; 1 user = 370 chunks); §1, §12 y §17 corregidos |
| URL de Render con prefijo `postgresql://` o `postgres://` | SQLAlchemy intenta cargar `psycopg2` si falta `+psycopg` | Añadido `@field_validator("DATABASE_URL")` (`normalize_database_url`) en `settings.py` y probado en PowerShell |
| Conflicto de merge en `docs/07_PROJECT_STATE.md` (§21) | Marcadores `<<<<<<< HEAD` quedaron dentro del archivo durante la fusión | Resuelto y unificado en esta versión del documento |
| Consulta sobre un PDF recién cargado terminaba en `rejected` después de ~27 s | La recuperación dependía solo de similitud vectorial y el juez podía descartar términos específicos; además, el frontend permitía preguntar durante la indexación | Recuperación híbrida vectorial + textual, filtro de documentos `ready`, respaldo léxico desde `SIM_LOW` y bloqueo de preguntas durante `pending`/`processing` |
| Mascota cubría el mensaje `Pensando...` | El componente compacto estaba en la misma fila que el texto y su transformación salía de su caja visual | Mascota reubicada en un bloque independiente encima del texto, con tamaño reservado y comportamiento responsive |
| Todas las preguntas terminaban rechazadas aunque los PDFs aparecieran `READY` | El respaldo textual solo se evaluaba después del juez LLM; consultas con baja similitud o diferencias de tildes quedaban rechazadas. En el entorno de diagnóstico también se comprobó que Ollama no estaba instalado/activo y la base local tenía 0 documentos y 0 chunks | Evidencia textual directa aceptada antes del juez, búsqueda insensible a tildes/prefijos, pruebas nuevas y diagnóstico explícito de que Ollama debe estar activo con `qwen2.5:3b` y `bge-m3` |
| `¿Qué es una base de datos relacional?` terminaba en `rejected` pese a devolver `200 OK` | La recuperación aceptaba prefijos, pero la validación de evidencia exigía coincidencia exacta; `relacional` no coincidía con `relacionales` en los fragmentos | Validación léxica con prefijos controlados y prueba de regresión para la variante plural |

**Secciones de la guía definitiva que quedaron superadas:** el flujo con el umbral 0.45 para decidir entre aclarar y rechazar (§7), el pendiente de `save_history` ficticio, el de frontend/API sin validar y el de la ruta clara-sin-evidencia → `clarify`. El resto (arranque, respaldo, re-embedding) sigue vigente.

---

## 17. Pendientes y riesgos abiertos

| # | Ítem | Tipo | Acción propuesta |
| --- | --- | --- | --- |
| 1 | Confirmar y subir esta consolidación de `docs/07_PROJECT_STATE.md` a `origin/evilnightmare010-analyze-agent-project` | Alto (inmediato) | Ejecutar `git add`, `git commit` y `git push` sobre la rama de trabajo; no modificar `main` |
| 2 | Verificar el comportamiento visual del estado `Pensando...` en una sesión autenticada | Calidad | Probar una pregunta real y confirmar que la mascota queda encima, sin cubrir el texto |
| 3 | Falta evaluación con métricas (requisito del enunciado y de `docs/08`) | Alto | `scripts/run_eval.py` sobre `eval/questions.jsonl`: aciertos, rechazos correctos, falsos negativos, latencia p50/p95 |
| 4 | Despliegue público en Render y Vercel (Anexo A) | Riesgo / Entrega | Levantar servicios con `render.yaml` y `vercel.json`, verificar `/api/v1/health` desde red externa y documentar con rigor |
| 5 | Documento técnico (`docs/08`): tabla de corpus, evaluación y PDF | Entrega | Añadir corpus/métricas y exportar el documento técnico a PDF |
| 6 | Diagrama gráfico y diapositivas (8–12 láminas en PDF) | Entrega | Convertir el esquema de §3 en diagrama e incluir la secuencia del enunciado §5.4 |
| 7 | Demo: extracto de la tesis y pregunta sobre un documento recién cargado | Entrega | Extracto de ~30 páginas con texto seleccionable; subir desde la UI; preguntar; ensayar en local con rechazo incluido |
| 8 | Respaldo léxico sin pruebas unitarias | Calidad | Pruebas con fakes: normalización acepta; Kafka y sushi rechazan |
| 9 | Sin citas `[n]` en línea; posible conocimiento fuera del contexto | Calidad | Revisar `ANSWER_PROMPT` y añadir prueba de *grounding* |
| 10 | "Automatización en ML" rechazada (0.550) | Calidad | Visibilidad descartada (§12); inspeccionar los chunks recuperados con `chat_cli` |
| 11 | `rewrite_query` casi idéntico a la consulta original | Calidad | Mejorar sin mezclar con otros cambios |
| 12 | Latencia 12–33 s | Rendimiento | Medir por nodo, sin carga en paralelo; revisar `OLLAMA_KEEP_ALIVE` |
| 13 | Las pruebas dejan datos en la BD de desarrollo | Higiene | BD de pruebas o limpieza en teardown |
| 14 | CI | Fase 7 | GitHub Actions con `vite build` y `ruff`; `pytest` solo si hay servicio pgvector |
| 15 | Comparación `bge-m3` vs `nomic-embed-text` | Fase 7, opcional | `nomic-embed-text` suele generar 768 dimensiones **[verificar con `ollama show`]**; no tocar datos hoy |
| 16 | Auditoría de PDFs (texto seleccionable) | Documentación | Ejecutar `audit_corpus.py` y registrar páginas y caracteres por página |
| 17 | Respaldo nuevo de la BD (7 932 chunks) | Higiene | `pg_dump` (§11) antes de cualquier cambio de datos |
| 18 | `INTELIGENCIA_ARTIFICIAL` es `scope user` | Menor | Opcional: convertir a `global` con transacción y respaldo |
| 19 | Respuestas a las 3 preguntas de la Fase 5 | Aprendizaje | Entregar al Gem |

**Resueltos desde la versión anterior:** centralización de `CHAT_MODEL`, `NUM_CTX` y `NUM_PREDICT` en `settings.py`; validador `normalize_database_url` probado; índice `idx_embedding_hnsw` verificado en `models.py`; aislamiento de `.env.render` y restauración del `.env` local; visibilidad real del corpus documentada (§12); recuperación híbrida tras carga de PDF; bloqueo de preguntas durante la indexación; identidad ciberpunk de DataTutor; mascota animada y estado `Pensando...`.

---

## 18. Seguimiento de requisitos del enunciado

Contrastar siempre contra `trabajo_agente.pdf` y `04_API_CONTRATO.md`; esta tabla resume el estado del proyecto.

| Requisito | Estado |
| --- | --- |
| Modalidad del equipo | 3 integrantes (registrados en `docs/08` con aval del profesor; el PDF §1.3 dice 1 o 2) |
| Autenticación OIDC + PKCE con Keycloak (login, registro, logout) | [OBSERVADO] |
| Backend protegido que valida el JWT | [PROBADO] |
| Agente LangChain + LangGraph con modelo local | [OBSERVADO] |
| Respuestas con fuentes (documento, página, similitud, fragmento) | [OBSERVADO] |
| Rechazo explícito sin evidencia, con el mensaje obligatorio | [OBSERVADO] |
| Más de dos estrategias anti-alucinación | [IMPLEMENTADO] (6 listadas en `docs/08` §10) |
| Historial de conversaciones (listar, consultar, borrar) | [PROBADO] |
| Carga de documentos propios con estados asíncronos y borrado | [PROBADO] |
| Aislamiento entre usuarios | [PROBADO] |
| README | [IMPLEMENTADO] (integrado en `main` en commit `77a6ac2`) |
| Documento técnico (14 apartados) | [IMPLEMENTADO] en Markdown (`docs/08`); [PENDIENTE] asignatura, corpus, métricas, URLs y PDF |
| Conjunto de evaluación con métricas | [PENDIENTE] (`eval/questions.jsonl` existe; falta ejecutar el runner y anexar resultados) |
| CI | [PENDIENTE] |
| Despliegue público (Render + Vercel) | [EN CURSO] (`render.yaml`, `settings.py` y `vercel.json` listos; falta levantar en paneles) |
| Diagrama, diapositivas | [PENDIENTE] |
| Ensayo de la sustentación presencial (demo en local) | [PENDIENTE] |

---

## 19. Git y publicación

**Estado (18 oct, noche) [PROBADO en Git Bash]:**

* Repositorio: `https://github.com/IsaksGir4/DataTutor.git`, rama actual `evilnightmare010-analyze-agent-project`.
* La rama de trabajo está sincronizada con `origin/evilnightmare010-analyze-agent-project` hasta `bd3db88`, sin modificar `main`.
* Commits relevantes de esta rama: `22f64a0` (identidad DataTutor), `0553f78` (interfaz ciberpunk), `bb8813d` (recuperación híbrida tras carga de PDF) y `bd3db88` (posición de la mascota durante `Pensando...`).
* `docs/07_PROJECT_STATE.md` es el único archivo pendiente de confirmar después de esta consolidación.



**Comandos exactos para dejar la rama de trabajo limpia y sincronizada en Git Bash:**

```bash
git status
git check-ignore -v .env .env.render frontend/.env corpus/ejemplo.pdf
git add docs/07_PROJECT_STATE.md
git diff --cached --name-only
git commit -m "docs: consolidate DataTutor project state"
git push origin evilnightmare010-analyze-agent-project

```

**Qué se sube y qué no:**

* Sí: código, `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, `.env.example` (raíz y frontend), `docs/`, `keycloak/import/`, `compose.yml`, `render.yaml`, `frontend/vercel.json`, `eval/questions.jsonl`, `corpus/.gitkeep`, `corpus/README.md`.
* **No:** `.env`, `.env.render`, `.env.*` (salvo `.env.example`), `frontend/.env`, `*.dump`, `node_modules/`, `dist/`, `backend/.venv`, **los PDFs del corpus**.

---

## 20. Hoja de ruta

| Fase | Objetivo | Fecha objetivo | Estado |
| --- | --- | --- | --- |
| 0 | Repo, estructura, `pyproject` (`uv`), compose (Postgres + Keycloak), `.env.example`, script de verificación | 5 oct | ✅ |
| 1 | Auditoría del corpus, PyMuPDF, chunking, embeddings, HNSW, ingesta CLI idempotente | 5–6 oct | ✅ |
| 2 | Grafo LangGraph, pruebas con fakes, CLI de chat y evaluación inicial | 6–11 oct | ✅ |
| 3 | FastAPI, JWT de Keycloak, `/chat`, historial, aislamiento | 7–13 oct | ✅ |
| 4 | Subida asíncrona, listar/borrar, estados, cascada | 8–16 oct | ✅ |
| 5 | Frontend: login, chat con fuentes, historial, documentos, errores, logout; corrección de defectos | 9–17 oct | ✅ |
| 6 | Integración local completa, mejoras del frontend, recuperación tras carga de PDF y guion de demo | 17–18 oct | ✅ (`pytest` 6/6 y `vite build` completados; falta ensayo en vivo con tesis) |
| 7 | Evaluación completa, `bge-m3` vs `nomic-embed-text`, CI, despliegue público fuera del campus | 17–18 oct | 🔄 Parcial (`render.yaml`, `settings.py` y `vercel.json` listos; despliegue y eval en curso) |
| 8 | README, diagrama, documento técnico, diapositivas | 17–18 oct | 🔄 Parcial (README y docs 08/09 en `main`; faltan PDF, diagrama y diapositivas) |
| 9 | Ensayo de sustentación y colchón sin funcionalidades nuevas | 18 oct | ⬜ |

---

## 21. Próximas acciones

**Orden unificado para cerrar hoy (18 oct):**

1. **Git (inmediato):** hacer `git add`, `commit` y `push` de `render.yaml`, `backend/app/config/settings.py` y `docs/07_PROJECT_STATE.md` con los comandos de §19; verificar que `.env` y `.env.render` sigan ignorados.
2. **Validación del frontend post-merge:** desde `frontend/`, ejecutar `npm run lint` y `npm run build` para confirmar que el rediseño de Ingeniería de Datos compila sin errores.
3. **Despliegue público (Anexo A):**
* Levantar el Web Service en Render (plan `free`), completando las variables `sync: false` en el panel y usando la *Internal Database URL*.
* Verificar `GET https://datatutor.onrender.com/api/v1/health` desde otra red (datos del celular); el endpoint registrado respondió `200 OK`.
* Mantener `VITE_API_BASE_URL=https://datatutor.onrender.com/api/v1` y actualizar `CORS_ORIGINS` en Render con `https://data-tutor.vercel.app,http://localhost:5173`.


4. **Runner de evaluación y pruebas:** ejecutar `scripts/run_eval.py` sobre `eval/questions.jsonl` (aciertos, rechazos correctos, falsos negativos, latencia p50/p95) y guardar la evidencia en `docs/evidencias/`; añadir pruebas con fakes para el respaldo léxico si da el tiempo.
5. **Documento técnico (`docs/08_DOCUMENTO_TECNICO.md`):**
* La asignatura ya está registrada como **Integración e Implementación de Software** en `docs/08_DOCUMENTO_TECNICO.md`.
* Agregar la tabla del corpus real (los 7 documentos y 7 932 chunks de §12).
* Agregar las métricas de evaluación y actualizar la conclusión (§14).
* Registrar las URLs públicas de Render y Vercel en §12 una vez verificado `/health`, manteniendo la explicación honesta de que Keycloak y Ollama son locales.
* Incluir la captura y evidencia del documento recién cargado en §13 y exportar a PDF (`docs/documento-tecnico.pdf`).


6. **Demo local y sustentación:** preparar el extracto de ~30 páginas de la tesis con texto seleccionable, subirlo en vivo desde `http://localhost:5173` (mientras está en `pending`/`processing`, el frontend muestra el estado y bloquea nuevas preguntas; una vez en `ready`, hacer una pregunta respondible sobre él y una pregunta rechazada).
7. **Diagrama y diapositivas:** exportar el diagrama de arquitectura (`docs/arquitectura.png`) y las diapositivas de 8 a 12 láminas en PDF (`docs/presentacion.pdf`).

---

## 22. Siguiente prompt para el Gem

> Estamos en DataTutor, entrega HOY 18 oct. Usa este `PROJECT_STATE.md` como contexto inicial. La rama actual es `evilnightmare010-analyze-agent-project`; el frontend tiene identidad ciberpunk roja, mascota animada y estado `Pensando...`; la recuperación de PDFs combina similitud vectorial y coincidencia textual, y la última validación fue `6 passed in 6.88s`.
> Reglas: no cambies `SIM_THRESHOLD` ni `SIM_LOW`, no borres ni reingieras datos, no uses `docker compose down -v`, no escribas versiones de memoria, no pegues contraseñas. Dime la terminal (PowerShell, cmd o Git Bash) antes de cada comando y espera mi confirmación entre tareas.
> Tareas, en este orden:
> 1. Confirmar el commit y push de `docs/07_PROJECT_STATE.md` a `evilnightmare010-analyze-agent-project`, sin modificar `main`, y verificar `npm run lint` + `npm run build` en `frontend/`.
> 2. Guiarme en el levantamiento de Render y Vercel siguiendo el Anexo A hasta verificar `/api/v1/health` (`200 OK`).
> 3. Revisar `docs/08_DOCUMENTO_TECNICO.md` para completar la asignatura (`Integración e Implementación de Software`), la tabla de los 7 documentos del corpus (7 932 chunks), la sección de evaluación y las URLs verificadas.
> 4. Escribir `backend/scripts/run_eval.py` (inspeccionando antes `eval/questions.jsonl`) para reportar métricas y guardar la evidencia en `docs/evidencias/`.
>
>

---

## 23. Variables de entorno (nombres; valores locales en `.env`)

`DATABASE_URL`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `OLLAMA_URL`, `OLLAMA_KEEP_ALIVE`, `CHAT_MODEL`, `EMBED_MODEL`, `EMBED_DIM`, `NUM_CTX`, `TEMPERATURE`, `NUM_PREDICT`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`, `SIM_THRESHOLD`, `SIM_LOW`, `MAX_UPLOAD_MB`, `KEYCLOAK_URL`, `KEYCLOAK_JWKS_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_AUDIENCE`, `KC_ADMIN_USER`, `KC_ADMIN_PASSWORD`, `CORS_ORIGINS`, `VITE_API_BASE_URL`, `VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM`, `VITE_KEYCLOAK_CLIENT_ID`, `VITE_MAX_UPLOAD_MB`; solo si se usa un túnel: `NGROK_AUTHTOKEN`.

No copiar valores secretos a este documento, a `.env.example`, a Git ni a un chat nuevo.

---

## 24. Historial de este documento

* **17 oct (tarde):** fusión de la versión del usuario, la guía definitiva y la evidencia del día. Se retiraron textos obsoletos (defectos de UI abiertos, pytest 4/1 fallando, constantes locales de umbral). Se añadieron: runbook condensado, contrato de API, modelo de datos, incidencias resueltas, riesgos priorizados, seguimiento de requisitos, política de Git y corpus, y el respaldo léxico con sus limitaciones.
* **18 oct (compañero):** se añadieron mejoras de frontend (identidad de Ingeniería de Datos, accesibilidad, bloqueo mientras un PDF está en `pending`/`processing`), `render.yaml`, `vercel.json`, documentos 08 y 09, `init_database()` y el cliente de chat configurable.
* **18 oct (noche, pre-merge):** consolidación del corpus real de 7 documentos y 7 932 chunks (consulta a `documents`); corregida la nota de visibilidad (los 6 libros principales son globales); descartada la visibilidad como causa del rechazo de "automatización en ML" (consulta a `conversations`); resultado de `pytest` pre-merge (5 passed en 2.91 s); aislamiento de `.env.render` y restauración del `.env` local; añadido el Anexo A.
* **18 oct (noche, post-merge `77a6ac2`):** integrado el merge de la rama del equipo en `main`; eliminados los marcadores de conflicto en §21; probados `normalize_database_url` en `settings.py`, `idx_embedding_hnsw` en `models.py` y `uv run pytest -v` (`5 passed in 2.17s`); documentados los ajustes de `docs/08` y el flujo de despliegue en Render + Vercel.
* **18 oct (noche, trabajo de Juan José):** se añadió la identidad ciberpunk roja de DataTutor, la mascota robótica animada, el estado `Pensando...` y su corrección de layout; se implementó recuperación híbrida vectorial + textual para consultas sobre PDFs recién indexados, se bloqueó el chat durante `pending`/`processing`, se agregó una prueba del respaldo léxico y se verificó `6 passed`, `vite build` y `npm run lint` sin errores.

---

## Anexo A. Despliegue público (Render + Vercel)

**Estado [IMPLEMENTADO en código / EN CURSO en paneles cloud]:** el equipo despliega el frontend en Vercel y el backend en Render con un PostgreSQL administrado ya creado en Render. `render.yaml` (`plan: free`, `PYTHON_VERSION=3.12.7`, `sync: false`), `backend/app/config/settings.py` (`normalize_database_url`), `frontend/vercel.json` y `docs/09_GUIA_DESPLIEGUE.md` están listos.

**URLs públicas registradas y comprobadas:** [Frontend Vercel](https://data-tutor.vercel.app/) carga correctamente; [Backend Render](https://datatutor.onrender.com) está publicado; y [`GET /api/v1/health`](https://datatutor.onrender.com/api/v1/health) respondió `200 OK`. Estas comprobaciones no sustituyen la validación pública del login, chat RAG y carga de documentos.

**Qué sí se puede demostrar públicamente:** `GET https://datatutor.onrender.com/api/v1/health`, que no requiere token ni depende de Ollama o Keycloak, y la carga del frontend en Vercel.

**Qué no puede funcionar hoy en la nube pública, y por qué:**

| Componente | Limitación |
| --- | --- |
| Login en Vercel | `login-required` redirige a la URL de Keycloak configurada. Con `localhost:8080`, el navegador del visitante intenta su propia máquina. Hace falta un Keycloak público con `iss` coherente |
| Validación del JWT en Render | `KEYCLOAK_JWKS_URL` apunta a `127.0.0.1`: Render no puede alcanzarlo; los endpoints protegidos fallarían |
| Chat en Render | `OLLAMA_URL=http://127.0.0.1:11434` no es alcanzable; `POST /chat` devolvería 503. Además, la base de Render está vacía (con tablas e índice HNSW creados por `init_database()`, sin corpus) |
| Corpus en Render | Los 7 932 chunks viven en la base local; llevarlos exigiría `pg_dump`/`pg_restore` y, sin Ollama accesible, igualmente no se podría consultar |

**Variables del servicio web en Render (panel de Render, nunca en el `.env` local):**

* `DATABASE_URL`: pegar la *Internal Database URL* de la base de Render. El validador `normalize_database_url` de `settings.py` convierte `postgres://` o `postgresql://` a `postgresql+psycopg://` automáticamente. (Si algún día se conecta desde el PC para pruebas, usar la External URL con `?sslmode=require` desde `.env.render`).
* `CORS_ORIGINS`: `https://data-tutor.vercel.app,http://localhost:5173` (separado por coma, sin barra `/` final y sin JSON).
* `OLLAMA_URL`, `KEYCLOAK_URL`, `KEYCLOAK_JWKS_URL`: poner los valores locales de relleno (`http://127.0.0.1:11434`, `http://localhost:8080`, `http://127.0.0.1:8080/realms/datatutor/protocol/openid-connect/certs`) para que la validación de `Settings` permita arrancar el servicio.
* Comando de arranque en `render.yaml`: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
* Si al arrancar en Render fallara `CREATE EXTENSION IF NOT EXISTS vector`, ejecutar una vez `CREATE EXTENSION vector;` en la consola SQL de Render.

**Variables en Vercel (`Root Directory: frontend`, preset Vite):**

* `VITE_API_BASE_URL` = `https://datatutor.onrender.com/api/v1`
* `VITE_KEYCLOAK_URL` = `http://localhost:8080`
* `VITE_KEYCLOAK_REALM` = `datatutor`
* `VITE_KEYCLOAK_CLIENT_ID` = `datatutor-web`
* `VITE_MAX_UPLOAD_MB` = `30`
* Nota: Vite fija las variables en tiempo de compilación (*build time*), por lo que cualquier cambio de variable exige hacer *Redeploy* en Vercel.

**Qué escribir en la entrega (sin afirmar de más):** registrar las URLs reales de Render y Vercel en `docs/08_DOCUMENTO_TECNICO.md` solo después de verificar `/api/v1/health` desde otra red (p. ej. datos del celular); explicar con transparencia que el backend público expone `/api/v1/health` conectado al PostgreSQL con `pgvector` en Render y que la demostración interactiva completa (login OIDC+PKCE, inferencia RAG con `qwen2.5:3b`/`bge-m3` y carga de PDFs) se ejecuta en el entorno local.

```

---

### Qué ejecutar y qué resultado esperar

1. **Guardar este contenido en `docs/07_PROJECT_STATE.md`** y comprobar en **Git Bash** (desde la raíz del repositorio) que no quede ningún marcador de conflicto (`<<<<<<<`) y que `.env` / `.env.render` estén ignorados:
   ```bash
   grep -n "<<<<<<<\|=======\|>>>>>>>" docs/07_PROJECT_STATE.md || echo "OK: sin conflictos en 07_PROJECT_STATE.md"
   git check-ignore -v .env .env.render frontend/.env

```

* **Resultado esperado:** Imprime `OK: sin conflictos en 07_PROJECT_STATE.md` y muestra las reglas de `.gitignore` que protegen tus archivos `.env` y `.env.render`.

2. **Subir `render.yaml`, `backend/app/config/settings.py` y `docs/07_PROJECT_STATE.md` en Git Bash:**
```bash
git add render.yaml backend/app/config/settings.py docs/07_PROJECT_STATE.md
git status
git commit -m "fix(deploy): add free plan render.yaml, normalize DATABASE_URL and consolidate project state"
git push origin main

```


* **Resultado esperado:** El árbol de trabajo queda limpio (`nothing to commit, working tree clean`) y tu rama `main` en GitHub queda lista para conectar el servicio en Render.


3. **Validar el frontend fusionado en PowerShell (`frontend/`):**
```powershell
npm run lint
npm run build

```


* **Resultado esperado:** `oxlint` finaliza sin errores y `vite build` genera `dist/` correctamente con el nuevo diseño de tu compañero. Compárteme la salida para marcarlo como **[PROBADO]** y pasar al despliegue o a las correcciones de `docs/08_DOCUMENTO_TECNICO.md`.



---

### Puntos clave para recordar

* **Aislamiento entre `.env` y `.env.render`:** Como `pydantic-settings` en `settings.py` carga automáticamente `PROJECT_ROOT / ".env"` y Docker Compose también interpola variables desde `.env`, mantener las credenciales de nube en `.env.render` evita contaminar el contenedor local o perder visibilidad sobre los 7 932 chunks.


* **Limpieza de marcadores de conflicto (`<<<<<<< HEAD`):** Git inserta delimitadores textuales cuando dos ramas modifican las mismas líneas de un archivo; si se ejecuta `git add` sin borrar esas marcas, el archivo se sube con las dos versiones superpuestas como ocurrió en la sección 21 del estado anterior.


* **Trazabilidad de `owner_id` en el corpus:** Cruzar `documents.owner_id` con `keycloak/import/datatutor-realm.json` permite verificar que `aaaaaaaa-0000-0000-0000-000000000002` es el identificador fijo (`sub`) del usuario `estudiante`, descartando problemas de permisos sobre `INTELIGENCIA_ARTIFICIAL.pdf` cuando se inicia sesión con esa cuenta.