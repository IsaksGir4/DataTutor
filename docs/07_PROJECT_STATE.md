# PROJECT_STATE — DataTutor

> Documento vivo y fuente de contexto del proyecto. Actualizarlo al cerrar cada fase o tras cambios relevantes, y pegarlo al inicio de cada chat nuevo con el Gem. Si el estado pegado difiere de los archivos de conocimiento, prevalece este estado para el contexto de la conversación; los archivos actuales del repositorio siguen siendo la fuente de verdad sobre qué código está realmente implementado.
>
> **Última actualización:** 18 oct 2026 (noche) · **Fase actual:** 6 cerrando; 7 y 8 en curso parcial · **Entrega del trabajo:** 18 oct 2026 (hoy).
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

**Qué es.** DataTutor es el "Trabajo Agente" de la materia de **Integración e Implementación de Software**: una aplicación web con un asistente RAG para ingeniería y ciencia de datos, con agente LangChain + LangGraph, modelo local (Ollama), base vectorial PostgreSQL + pgvector, autenticación Keycloak (OIDC + PKCE), backend FastAPI y frontend React. Responde solo con lo que respalda el corpus, cita sus fuentes y rechaza explícitamente lo que no puede sustentar. Equipo de 3 integrantes (el profesor permite un máximo de 3).

**Qué funciona hoy.**

- **[PROBADO]** Backend protegido con JWT, aislamiento por usuario, subida/listado/borrado de PDFs con estados, historial de conversaciones y `pytest` (5 pruebas; última corrida 18 oct: 5 passed en 2.91 s, antes de mezclar la rama del equipo).
- **[OBSERVADO]** Login con Keycloak, chat con fuentes (documento, página, similitud, fragmento), rechazo de preguntas fuera de dominio, historial recuperable, polling de documentos.
- **[OBSERVADO en BD, 18 oct]** Corpus indexado: **7 documentos, 7 932 chunks** (6 documentos globales con 7 562 chunks y 1 documento de usuario con 370 chunks). Detalle en §12.
- **[PENDIENTE de verificar]** `vite build` y `npm run lint` están reportados como correctos en `docs/08_DOCUMENTO_TECNICO.md` (autoría del compañero), pero no hay salida pegada en el chat.

**Qué cambió el 18 oct (rama del equipo, commit `73cedfd`, 11 archivos, +756/−26).** README raíz, mejoras de accesibilidad y diseño responsive del frontend, `render.yaml`, `frontend/vercel.json`, `docs/08` (documento técnico) y `docs/09` (guía de despliegue), captura en `docs/evidencias/`, `init_database()` en `core/database.py` y `llm/chat.py` leyendo el modelo y los parámetros desde `settings`. Esta rama **aún no está mezclada** en la copia local (§19).

**Qué falta.** Runner de evaluación con métricas, pruebas del respaldo léxico, CI, conversión del documento técnico a PDF con capturas, diagrama gráfico, diapositivas, demo con extracto de la tesis y verificación del despliegue (Anexo A).

**Riesgos principales (detalle en §17).**

1. **El despliegue público no puede ser funcional de extremo a extremo:** Render y Vercel no alcanzan el Ollama ni el Keycloak locales. Solo `GET /api/v1/health` es demostrable públicamente; la demo completa debe ser local (Anexo A).
2. `init_database()` se ejecuta al importar `database.py` (efecto lateral); falta verificar que no rompa pruebas ni scripts sin base y que no omita el índice HNSW.
3. Las respuestas no muestran citas `[n]` en línea y el modelo de 3B puede usar conocimiento propio fuera del contexto.
4. Latencia de 12–33 s por consulta (solo CPU).
5. Falta evaluación con métricas (requisito del enunciado pendiente).

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
- **El `.env` de la raíz es solo para el entorno local.** Los valores de Render se configuran en el panel de Render; no se mezclan en el `.env` local (§16, incidencia del 18 oct).
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
- **Despliegue público planificado (Anexo A):** frontend en Vercel, backend y PostgreSQL con pgvector en Render. Keycloak y Ollama permanecen locales, por lo que la demo completa es local.

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

- **GPU:** el usuario reporta que su GPU está dañada. Ollama falla en GPU (`CUDA error: an illegal instruction was encountered`, Ollama 0.40.0). CPU-only es la configuración definitiva de este equipo, no un workaround temporal.
- **PostgreSQL nativo:** el servicio `postgresql-x64-17` de Windows ocupó el puerto 5432; se dejó detenido y deshabilitado. Si reaparece un fallo de conexión, comprobar primero ese servicio.
- **Credenciales:** contraseñas de desarrollo local solo (laboratorio); viven en `.env` y deben coincidir con `settings.py`. No copiarlas a este documento, a Git ni a un chat.
- **Docker Hub:** si falla un `pull` por credenciales, `docker logout` y reintentar.

---

## 5. Decisiones técnicas vigentes

| Área              | Decisión                                                                                                                                                                                                                                                         |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sistema            | Windows; repo en `C:\Users\HP\Desktop\2026-2\Integracion e implementacion Soft\TutorDatos`                                                                                                                                                                      |
| Backend            | Python 3.12.7 + FastAPI + `uv`, ejecutado desde PyCharm; SQLAlchemy 2.0                                                                                                                                                                                         |
| Agente             | LangChain + LangGraph con `StateGraph` explícito                                                                                                                                                                                                               |
| LLM                | `qwen2.5:3b` en Ollama, CPU (`temperature` 0.0, `num_ctx` 4096, `num_predict` 512; desde la rama del equipo se leen de `settings` mediante `CHAT_MODEL`, `NUM_CTX` y `NUM_PREDICT`)                                                                         |
| Embeddings         | `bge-m3`, 1024 dimensiones                                                                                                                                                                                                                                      |
| Datos              | PostgreSQL 16 + pgvector en Docker; índice HNSW; `ON DELETE CASCADE` en `messages` y `chunks`                                                                                                                                                              |
| Autenticación     | Keycloak 24, OIDC Authorization Code + PKCE S256; cliente público `datatutor-web` (sin Direct Access Grants); backend valida JWT RS256 (`iss` = `http://localhost:8080/realms/datatutor`, `aud` = `datatutor-web`, `exp`) con JWKS por `127.0.0.1` |
| Frontend           | React + Vite + `keycloak-js`; token en memoria (no `localStorage`); linter Oxlint                                                                                                                                                                             |
| PDF                | PyMuPDF (`fitz`), extracción por página; splitter por página (1000/200)                                                                                                                                                                                      |
| Cliente de pruebas | `datatutor-swagger` con Direct Access Grants, solo para scripts de consola                                                                                                                                                                                      |
| Ingesta            | Libros completos por `scripts/ingest_corpus.py`; la subida web, para extractos de ~5–30 páginas                                                                                                                                                               |
| Despliegue         | Frontend en Vercel, backend y PostgreSQL+pgvector en Render; demo completa en local (Keycloak y Ollama no son accesibles desde internet). Ver Anexo A                                                                                                          |
| Corpus en Git      | Los PDFs no se versionan; en el repositorio solo `corpus/.gitkeep` y `corpus/README.md`                                                                                                                                                                       |
| Equipo             | 3 integrantes (máximo permitido por el profesor)                                                                                                                                                                                                                |

---

## 6. Configuración y parámetros RAG

**Parámetros (unificados en `settings.py` y `.env`):** `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `TOP_K=4`, `SIM_THRESHOLD=0.65`, `SIM_LOW=0.50`, `MAX_UPLOAD_MB=30`.

- **[OBSERVADO]** Un script de diagnóstico imprimió `THRESHOLD: 0.65` leyendo `settings`; `SIM_THRESHOLD` **no** es importable desde `core.py` (vive en `settings`).
- **[IMPLEMENTADO]** `core.py` y `graph.py` consumen `settings.TOP_K`, `settings.SIM_THRESHOLD` y `settings.SIM_LOW` como única fuente (verificar el archivo si se toca).
- **[IMPLEMENTADO en la rama del equipo]** `app/llm/chat.py` consume `CHAT_MODEL`, `NUM_CTX` y `NUM_PREDICT` desde `settings` (cierra el pendiente de centralización). **[PENDIENTE]** tras el merge, comprobar con `grep -n "CHAT_MODEL\|NUM_CTX\|NUM_PREDICT" backend/app/config/settings.py backend/app/llm/chat.py` que `settings.py` define las tres variables (el commit no modifica `settings.py`).

**Archivos de entorno:**

- `TutorDatos/.env`: backend y servicios **locales**; secretos locales; no se versiona.
- `TutorDatos/.env.example`: plantilla sin secretos.
- `TutorDatos/frontend/.env`: variables de Vite; solo públicas con prefijo `VITE_`.
- `TutorDatos/frontend/.env.example`: plantilla de las variables públicas.
- Para trabajar con la base de Render sin tocar el entorno local, guardar esos valores como `.env.render` (el `.gitignore` ya cubre `.env.*`) o configurarlos en el panel de Render. **Nunca** sustituir `DATABASE_URL`, `DB_USER`, `DB_PASSWORD` ni `DB_NAME` del `.env` local por los de Render: `DB_*` también alimentan el `compose.yml`.
- El frontend no necesita contraseñas de PostgreSQL, credenciales de Keycloak admin ni parámetros de Ollama. Backend y frontend se configuran por separado (el backend lee el `.env` raíz mediante `PROJECT_ROOT`).
- `CORS_ORIGINS` debe incluir `http://localhost:5173` (y, en Render, el origen exacto de Vercel sin `/` final).
- Se corrigió en el `.env` raíz una `KEYCLOAK_JWKS_URL` que traía sintaxis Markdown (`[url](url)`) y barras invertidas copiadas de un chat; el esquema resuelto apareció como `http`.

---

## 7. Versiones registradas

Copiadas del estado previo (`uv pip list`). Volver a comprobarlas con los comandos de cada gestor si se actualizan dependencias. No cambiar versiones solo para resolver un problema.

**Backend:** `fastapi==0.142.2`, `uvicorn==0.54.0`, `pydantic==2.13.5`, `pydantic-settings==2.15.0`, `sqlalchemy==2.1.3`, `psycopg==3.3.6`, `pgvector==0.5.0`, `langchain==1.4.3`, `langchain-core==1.6.7`, `langchain-ollama==1.1.0`, `langgraph==1.2.14`, `pymupdf==1.28.2`, `pyjwt==2.15.1`, `cryptography==50.0.2`, `httpx==0.28.1`, `pytest==9.1.1`, `ruff==0.16.10`.

**Frontend:** `react@19.3.1`, `react-dom@19.3.1`, `keycloak-js@26.2.4`, `vite@8.3.4`, `@vitejs/plugin-react@6.1.2`, `oxlint@1.88.0`, `@types/react@19.3.0`, `@types/react-dom@19.3.0`.

- **[OBSERVADO]** El frontend se reinstaló el 16 oct con `npm create vite@latest` + `npm install --ignore-scripts` (25 packages have verified registry signatures, 15 packages have verified attestations) y se añadió `keycloak-js`.

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

Confirmar contra el árbol real antes de añadir o mover archivos. Raíz tal como se ve en GitHub (18 oct) más los archivos de la rama del equipo.

```text
TutorDatos/
├── .env  .env.example  .gitignore  .python-version  compose.yml
├── README.md                     # nuevo (rama del equipo)
├── render.yaml                   # nuevo (rama del equipo): API + PostgreSQL en Render
├── audit_corpus.py               # script de auditoría de PDFs (commit inicial; resultados no registrados)
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
│   │   ├── main.py               # lifespan: fail_interrupted_documents
│   │   ├── agents/               # graph.py, prompts.py, state.py, nodes/core.py
│   │   ├── config/settings.py
│   │   ├── controllers/          # chat.py, documents.py
│   │   ├── core/                 # database.py (init_database), deps.py, errors.py, security.py
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
    ├── vercel.json               # nuevo (rama del equipo): SPA en Vercel
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
- **`init_database()` (rama del equipo, `core/database.py`, +13/−1) [IMPLEMENTADO]:** crea la extensión `vector` y las tablas ORM si la base está vacía; se invoca al importar el módulo. Motivo: una base nueva (p. ej. la de Render) arrancaba sin tablas y el backend fallaba con `relation does not exist`. **[PENDIENTE verificar tras el merge]:** (a) que importar `database.py` sin Postgres disponible no rompa `pytest` ni scripts; (b) que `create_all` también cree el índice HNSW y `uix_owner_sha256` en una base vacía (si el HNSW se creó fuera del ORM, una base nueva quedaría con búsqueda secuencial); (c) que sobre la base local con datos sea inocuo (debería no hacer nada).

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

- **Ola 1:** Silberschatz (BD, español); *Fundamentals of Data Engineering Concepts* (inglés); *Libro GUIA ingeniería de datos* (español); *Fundamentos de Ingeniería de Datos* (español, ~38 KB, prueba de humo); *Principles of Data Science* (inglés); *Seven ways…* (inglés); *Understanding… failure* (inglés).
- **Ola 2:** *EDR teoría BD*; *Big Book of Data Warehousing and BI*; *Python programming for Data Analysis*; `INTELIGENCIA_ARTIFICIAL`; `Data science route`.
- **Fuera de v1:** *Geometric Data Science book*.
- **Reservada para la demo en vivo:** tesis sobre control predictivo no lineal basado en modelo borroso; usar un extracto de ~30 páginas con texto seleccionable, no el libro completo.
- **[PENDIENTE]** La auditoría consolidada de PDFs (páginas, caracteres por página, texto seleccionable) no está registrada. Existe `audit_corpus.py` en la raíz del repositorio; registrar su salida.

**Indexado hoy (`status = ready`) [OBSERVADO en BD, consulta del 18 oct]:**

| Documento                                          | scope  | owner_id                     | págs | chunks |
| -------------------------------------------------- | ------ | ---------------------------- | ----- | ------ |
| Fundamentals-of-Data-Engineering-Concepts          | global | `global`                   | 219   | 693    |
| Silberschatz, Fundamentos de BD 6ª ed.            | global | `global`                   | 673   | 4 957  |
| Fundamentos-de-Ingeniería-de-Datos                | global | `global`                   | 16    | 16     |
| Libro GUIA ingenieria de datos                     | global | `global`                   | 544   | 1 320  |
| Python programming for Data analysis               | global | `global`                   | 271   | 535    |
| Seven ways to make a data science project fail     | global | `global`                   | 5     | 41     |
| INTELIGENCIA_ARTIFICIAL                            | user   | `aaaaaaaa-…-000000000002` | 144   | 370    |
| **Total**                                          |        |                              |       | **7 932** (global 7 562 + usuario 370) |

- **[OBSERVADO]** El corpus completo está solo en la base local (volumen Docker) y en `corpus/` en disco. No hay PDFs en GitHub; en el repositorio solo existe `corpus/README.md` (más `.gitkeep`).
- **Visibilidad (corrección del 18 oct):** los libros grandes (Silberschatz, Fundamentals, Libro GUIA, Python) **son globales**: cualquier cuenta los ve. La nota anterior de "tres libros solo visibles para un usuario" estaba desactualizada. Solo `INTELIGENCIA_ARTIFICIAL` (370 chunks) es de usuario y únicamente la ve el `sub` `aaaaaaaa-…-0002`.
- **[OBSERVADO]** `SELECT owner_id, count(*) FROM conversations GROUP BY owner_id` devolvió 3 conversaciones de `aaaaaaaa-…-0002` y 1 de un usuario `pytest-503-user-…`. Es decir, las pruebas de chat en la UI se hicieron con el usuario dueño del libro de IA, así que el libro **sí era visible** y el rechazo de "automatización en ML" (0.550) **no se explica por visibilidad**. **[PENDIENTE]** revisar los chunks recuperados para decidir si es falso negativo del retriever/juez o una respuesta legítimamente sin evidencia.
- **Riesgo de duplicados (vigente):** si se vuelve a ingerir como `global` un libro ya indexado como `user` (o al revés), el retriever devolvería ambas copias. Hoy solo `INTELIGENCIA_ARTIFICIAL` es de usuario y no existe copia global.
- **Decisión opcional:** convertir `INTELIGENCIA_ARTIFICIAL` a `global` actualizando `documents.scope`, `documents.owner_id` y `chunks.owner_id` de forma coherente, en una transacción y con respaldo previo, para que todas las cuentas la vean. Requiere autorización explícita.
- Libros del plan que **no aparecen** en la tabla al 18 oct: *Principles of Data Science*, *Understanding… failure*, *EDR teoría BD*, *Big Book of Data Warehousing and BI*. `Data science route.pdf` se eliminó tras comprobar que no tenía texto seleccionable (0 chunks). Decidir si se ingieren o se documentan como fuera de alcance.
- **Procedimiento para ingerir libros adicionales:** colocar los PDFs en `corpus/`, respaldar la BD, ejecutar `scripts/ingest_corpus.py` (consultar su `--help`; no asumir flags), con Ollama en CPU y sin otras cargas pesadas. Comparar luego `documents` y `chunks` contra lo esperado y validar una muestra de embeddings. Los libros largos tardan; no lanzar dos ingestas a la vez.
- **Política de repositorio:** los PDFs no se suben a GitHub. La base vive en el volumen Docker y se reproduce con el script; `corpus/README.md` documenta los nombres esperados.

---

## 13. Frontend

- **Auth:** `src/services/auth.js` con instancia `keycloak-js` y `initPromise` singleton (evita el doble `init()` de `React.StrictMode`); `onLoad: "login-required"`, `pkceMethod: "S256"`, `checkLoginIframe: false`; `getValidToken()` llama a `updateToken(30)` antes de cada petición. **[PENDIENTE]** verificar contra el archivo real.
- **API:** `src/services/api.js` adjunta el `Bearer`; no fija `Content-Type` cuando el cuerpo es `FormData` (el navegador añade el `boundary`); traduce el sobre de error del backend. Los enlaces Markdown (`[url](url)`) que se colaron en código copiado deben ser URLs simples.
- **App:** barra lateral con usuario, nuevo chat, historial de conversaciones (seleccionar/borrar), subida de PDFs y lista de documentos con estado. Área principal con mensajes, insignias por decisión (`answered` verde, `clarify` azul, `rejected` rojo/ámbar, `smalltalk` gris), fuentes y latencia, banner de errores.
- **Polling:** si hay documentos `pending`/`processing`, `GET /documents` cada 3 s hasta que todos sean terminales. Un documento huérfano mantendría activo el polling (se mitiga con `fail_interrupted_documents`).
- **Botón de borrar documento:** solo para `scope = user` y estado no activo; la restricción real vive en el backend (404 o rechazo en la capa de servicio/repositorio).
- **Historial sin texto (resuelto):** `MessageItem` no exponía `content`. Se añadió `content: str` y `sources` en `schemas/chat.py`; verificado en UI y en pytest. Respaldo en `App.jsx`: `{m.content || m.answer || m.text || "(Mensaje sin contenido de texto)"}` dentro de `<div className="message-body">` **[IMPLEMENTADO si se aplicó; verificar]**.
- **Build:** `vite build` compila sin errores (391 ms) **[PROBADO el 17 oct]**; `npm run lint` y `npm run build` reportados correctos el 18 oct en `docs/08` **[PENDIENTE de verificar con salida]**.
- **Origen:** acceder siempre por `http://localhost:5173`. `redirectUris` y `webOrigins` del realm solo lo permiten, y la API criptográfica de PKCE requiere contexto seguro. En Vercel, `login-required` redirigiría a un Keycloak público que hoy no existe (Anexo A).
- **[PENDIENTE]** Respuestas del usuario a las 3 preguntas de comprensión de la Fase 5 (StrictMode e `initPromise`; `FormData` sin `Content-Type` manual; qué capa frena un `DELETE` a un documento global o en proceso).

**Mejoras aplicadas el 18 oct por el compañero [IMPLEMENTADO; diff de `App.jsx` +52/−…, `styles.css` +134; sin verificar visualmente en local]:**

- Se conservaron la identidad oscura/azul y el contrato existente de la API.
- Estados visuales de autenticación y carga con `aria-live`, spinner y mensajes de error con `role="alert"`.
- Etiquetas accesibles y foco visible para controles de chat, subida, eliminación, logout y selección de conversaciones.
- Las conversaciones se pueden seleccionar también con teclado (`Enter` o espacio).
- Estado vacío explícito cuando no hay conversaciones o documentos.
- Layout responsive para pantallas medianas y móviles, y respeto por `prefers-reduced-motion`.
- Se registraron los tres integrantes en `docs/08_DOCUMENTO_TECNICO.md` y se incorporó la captura de la aplicación en `docs/evidencias/aplicacion-actual.png`.
- Se preparó `render.yaml` para Render (API + PostgreSQL con pgvector) y `frontend/vercel.json` para la SPA de Vercel.
- Se añadió `docs/09_GUIA_DESPLIEGUE.md` con el procedimiento de Render/Vercel y el guion de pruebas manuales.

---

## 14. Seguridad y cadena de suministro

- **npm (oct 2026):** hay campañas activas de malware y typosquatting en el registro (p. ej. MALFEX, el gusano de `tensorlake`, paquetes que imitan a `nestjs`, `vite` o `keycloak-js`) y un fallo de Trusted Publishing con más de 1 500 paquetes expuestos. No se encontró un aviso contra `react`, `react-dom`, `vite`, `@vitejs/plugin-react` ni `keycloak-js`, pero eso no garantiza que estén limpios.
- **Reglas:** nombres exactos; `npm install --ignore-scripts`; revisar `package-lock.json` en busca de nombres desconocidos; `npm audit` y `npm audit signatures` (esta última no es infalible: un ataque reciente tenía procedencia válida); `npm ci` para reproducir; no tener tokens reales en el entorno de instalación.
- **Secretos:** `.env`, `frontend/.env` y los `.dump` no se versionan. Las credenciales locales de desarrollo no se copian a documentos ni chats. La guía definitiva menciona valores de desarrollo locales: revisarla antes de hacer público el repositorio.
- **Base de Render:** su cadena de conexión contiene credenciales reales de un servicio en internet. Mantenerla fuera de Git y de los chats (enmascararla al compartir); configurarla solo en el panel de Render. Si alguna vez se pegó sin enmascarar, rotar la contraseña.
- **Keycloak público (si algún día se publica):** el contenedor actual es de desarrollo; no exponer la consola de administración con credenciales por defecto ni usar `start-dev` en producción.
- **Tokens:** el JWT vive en memoria de `keycloak-js` (no en `localStorage`), con renovación preventiva.
- **Autorización:** todo acceso a conversaciones, mensajes y documentos filtra por `owner_id = sub`; un recurso ajeno responde 404.

---

## 15. Validaciones y evidencia

**Por fase:**

- **Fase 0 [PROBADO]:** `scripts/verificar_entorno.py` (PostgreSQL + pgvector, JWKS de Keycloak, Ollama con `qwen2.5:3b` y `bge-m3`).
- **Fases 1–2 [PROBADO]:** ingesta inicial, re-embedding de 57 chunks (coseno 1.000000, 0 nulos, 1024 dim), recuperación (0.7172 en inglés, 0.6825 en español) y CLI `chat_cli.py` con tres casos (pregunta respondible, sin soporte, saludo).
- **Fase 3 [PROBADO]:** `scripts/test_api.py`: JWT, 401 sin token y con token manipulado, `POST /chat` 200, aislamiento 404 entre usuarios.
- **Fase 4 [PROBADO]:** `scripts/test_documents.py`: 202, estado `ready`, listado 200, duplicado 409, validación de embeddings, borrado 204 y cascada.
- **Fase 5 [PROBADO/OBSERVADO]:** `pytest` 5 passed; `vite build` correcto; login OIDC + PKCE, historial con texto, polling, recuperación de documentos interrumpidos y rechazo de PDFs sin texto verificados en UI. El fallo previo de `DataTutorException` sin `conversation_id` se corrigió en `core/errors.py`.
- **Fase 6, 18 oct [PROBADO]:** `uv run pytest -v` con el `.env` local restaurado y **antes** de mezclar la rama del equipo: 5 passed in 2.91 s. **[PENDIENTE]** repetir tras el merge (para validar `init_database()`).

**Salida de pytest (18 oct, pre-merge) [PROBADO]:**

```text
platform win32 -- Python 3.12.7, pytest-9.1.1, pluggy-1.6.0
rootdir: ...\TutorDatos\backend
configfile: pyproject.toml
plugins: anyio-4.15.1, langsmith-0.14.4
collected 5 items

tests/test_api_contracts.py::test_health_and_openapi_expose_all_endpoints PASSED                 [ 20%]
tests/test_api_contracts.py::test_protected_endpoints_reject_anonymous PASSED                    [ 40%]
tests/test_api_contracts.py::test_database_foreign_keys_enforce_sql_on_delete_cascade PASSED     [ 60%]
tests/test_api_contracts.py::test_chat_503_returns_conversation_id_to_avoid_duplicate_conversations PASSED [ 80%]
tests/test_api_contracts.py::test_conversation_lifecycle_and_cross_user_isolation PASSED         [100%]

5 passed in 2.91s
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
- **Por revisar [HIPÓTESIS]:** "automatización en procesos de machine learning" (0.550). La visibilidad del libro de IA ya está descartada como causa (§12); falta revisar los chunks recuperados.

**Calidad observada del texto generado:**

- Las respuestas **no muestran citas `[n]` en línea**, aunque el prompt de respuesta las exige. Las fuentes aparecen al final, lo que no demuestra que cada afirmación esté respaldada.
- La respuesta de normalización define 1FN y 2FN con contenido que los fragmentos recuperados (por sus extractos) no parecen aportar, y la de 2FN/3FN admite "no hay detalles" para la 2FN. **[HIPÓTESIS]** el modelo de 3B usa conocimiento propio fuera del contexto; verificar con el texto completo de los chunks y una prueba de *grounding*.
- Terminología: en la Guía, una respuesta tradujo mal *unrealistic expectations* ("Realismos inaceptables").

**Latencia:** 12–33 s por consulta en CPU, con varias llamadas al LLM por turno (clasificar, juez, reescribir y responder; el juez puede correr dos veces). Algunas mediciones se hicieron con ingestas en paralelo (se llegó a 42 s). **[PENDIENTE]** medir por nodo y sin carga en paralelo.

**Datos de prueba en la BD de desarrollo [OBSERVADO]:** `conversations` contiene un `owner_id` `pytest-503-user-…` (1 conversación) y `messages` filas asociadas: las pruebas dejan datos en la base real. Pendiente decidir una base de pruebas o limpieza en el teardown; no borrar sin autorización.

**Evidencia visual:** `docs/evidencias/aplicacion-actual.png` (captura inicial). Para el PDF final faltan capturas propias de login, respuesta sustentada, rechazo, carga de documento y despliegue.

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
| `.gitignore` con `corpus/` y negaciones ineficaces; `.DS_Store*.dump` pegados | Reglas mal formadas                     | `.gitignore` reparado (`corpus/*` + excepciones); verificado con `git check-ignore -v` |
| Base de Render creada sin tablas                       | Instalación nueva sin migraciones                              | `init_database()` (rama del equipo) crea la extensión y las tablas             |
| `.env` local apuntaba a la base de Render (18 oct)     | Se sustituyeron `DATABASE_URL` y `DB_*` para probar Render      | Restaurados los valores locales (usuario y clave de laboratorio); la configuración de Render va en el panel o en `.env.render` |
| `07` afirmaba "tres libros solo visibles para un usuario" | Estado desactualizado frente a la BD                          | Consulta de `documents` del 18 oct; §1, §12 y §17 corregidos                 |

**Secciones de la guía definitiva que quedaron superadas:** el flujo con el umbral 0.45 para decidir entre aclarar y rechazar (§7), el pendiente de `save_history` ficticio, el de frontend/API sin validar y el de la ruta clara-sin-evidencia → `clarify`. El resto (arranque, respaldo, re-embedding) sigue vigente.

---

## 17. Pendientes y riesgos abiertos

| #  | Ítem                                                                | Tipo           | Acción propuesta                                                                                                                                                                                                                           |
| -- | -------------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | Mezclar la rama del equipo sin perder el entorno local               | Alto           | Procedimiento de §19: respaldo de rama, vista previa con `--no-commit`, pytest y chat de humo, y recién entonces commit o `--abort`                                                                                                      |
| 2  | `init_database()` al importar: efecto lateral y posible falta de HNSW | Medio          | Verificar import sin base, que `create_all` cree HNSW y `uix_owner_sha256`; moverlo al `lifespan` solo si hay un problema real                                                                                                        |
| 3  | Falta evaluación con métricas (requisito del enunciado)             | Alto           | `scripts/run_eval.py` sobre `eval/questions.jsonl`: aciertos, rechazos correctos, falsos negativos, latencia p50/p95; guardar la salida en `docs/evidencias/`                                                                     |
| 4  | Respaldo léxico sin pruebas unitarias                               | Calidad        | Pruebas con fakes: normalización acepta; Kafka y sushi rechazan                                                                                                                                                                           |
| 5  | Sin citas `[n]` en línea; posible conocimiento fuera del contexto | Calidad        | Revisar `ANSWER_PROMPT` y añadir prueba de *grounding*                                                                                                                                                                                  |
| 6  | Despliegue público no funcional de extremo a extremo                | Riesgo         | Anexo A: verificar `/health` en Render, documentar honestamente; demo completa en local                                                                                                                                                   |
| 7  | Documento técnico: PDF, URLs verificadas, capturas, asignatura, corpus | Entrega        | Completar `[Nombre de la asignatura]` = Integración e Implementación de Software; agregar corpus y evaluación; exportar a PDF                                                                                                           |
| 8  | Diagrama gráfico, diapositivas                                       | Entrega        | Convertir el esquema ASCII de §3 en diagrama; slides con arquitectura, flujo del agente, anti-alucinación y demo                                                                                                                          |
| 9  | Demo: extracto de la tesis y pregunta sobre un documento recién cargado | Entrega        | Extracto de ~30 páginas con texto seleccionable; subir desde la UI; preguntar; ensayar con rechazo incluido                                                                                                                              |
| 10 | "Automatización en ML" rechazada (0.550)                            | Calidad        | Visibilidad descartada (§12); inspeccionar los chunks recuperados con `chat_cli`                                                                                                                                                          |
| 11 | `rewrite_query` casi idéntico a la consulta original              | Calidad        | Mejorar sin mezclar con otros cambios                                                                                                                                                                                                      |
| 12 | Latencia 12–33 s                                                    | Rendimiento    | Medir por nodo, sin carga en paralelo; revisar `OLLAMA_KEEP_ALIVE`                                                                                                                                                                        |
| 13 | Las pruebas dejan datos en la BD de desarrollo                       | Higiene        | BD de pruebas o limpieza en teardown                                                                                                                                                                                                       |
| 14 | CI                                                                   | Fase 7         | GitHub Actions con `vite build` y `ruff`; `pytest` solo si hay servicio pgvector (las pruebas usan la base real)                                                                                                                         |
| 15 | Comparación `bge-m3` vs `nomic-embed-text`                      | Fase 7, opcional | `nomic-embed-text` suele generar 768 dimensiones **[verificar con `ollama show`]**; la columna es de 1024: otra columna o tabla y re-embedding completo en CPU. No hacerlo hoy                                                         |
| 16 | Auditoría de PDFs (texto seleccionable)                             | Documentación | Ejecutar `audit_corpus.py` y registrar páginas y caracteres por página                                                                                                                                                                    |
| 17 | Respaldo nuevo de la BD (7 932 chunks)                               | Higiene        | `pg_dump` (§11) antes de cualquier cambio de datos                                                                                                                                                                                         |
| 18 | `INTELIGENCIA_ARTIFICIAL` es `scope user`                           | Menor          | Opcional: convertir a `global` con transacción y respaldo                                                                                                                                                                                  |
| 19 | Respuestas a las 3 preguntas de la Fase 5                            | Aprendizaje    | Entregar al Gem                                                                                                                                                                                                                            |
| 20 | Versiones reales del frontend registradas el 16 oct                  | Documentación | Repetir `npm list --depth=0` solo si cambian dependencias                                                                                                                                                                                  |

**Resueltos desde la versión anterior:** centralizar modelo, `num_ctx` y `num_predict` en `settings.py` (rama del equipo, a verificar tras el merge); visibilidad del corpus (§12); README raíz; guía de despliegue; documento técnico (fuente).

---

## 18. Seguimiento de requisitos del enunciado

Contrastar siempre contra `trabajo_agente.pdf` y `04_API_CONTRATO.md`; esta tabla resume el estado del proyecto.

| Requisito                                                         | Estado                                                        |
| ----------------------------------------------------------------- | ------------------------------------------------------------- |
| Equipo de máximo 3 personas                                       | Cumplido (3 integrantes, según `docs/08`)                      |
| Autenticación OIDC + PKCE con Keycloak (login, registro, logout) | [OBSERVADO]                                                   |
| Backend protegido que valida el JWT                               | [PROBADO]                                                     |
| Agente LangChain + LangGraph con modelo local                     | [OBSERVADO]                                                   |
| Respuestas con fuentes (documento, página, similitud, fragmento) | [OBSERVADO]                                                   |
| Rechazo explícito sin evidencia, con el mensaje obligatorio      | [OBSERVADO]                                                   |
| Más de dos estrategias anti-alucinación                          | [IMPLEMENTADO] (6 listadas en `docs/08` §10)                   |
| Historial de conversaciones (listar, consultar, borrar)           | [PROBADO]                                                     |
| Carga de documentos propios con estados asíncronos y borrado     | [PROBADO]                                                     |
| Aislamiento entre usuarios                                        | [PROBADO]                                                     |
| README                                                            | [IMPLEMENTADO] (rama del equipo; sin mezclar aún)             |
| Documento técnico (14 apartados)                                  | [IMPLEMENTADO] en Markdown; [PENDIENTE] PDF, URLs y capturas  |
| Conjunto de evaluación con métricas                             | [PENDIENTE] (`eval/questions.jsonl` existe; falta el runner)   |
| CI                                                                | [PENDIENTE]                                                   |
| Despliegue público (opcional si el campus lo bloquea)            | [PENDIENTE] (Render y Vercel en curso; ver Anexo A)            |
| Diagrama, diapositivas                                            | [PENDIENTE]                                                   |
| Ensayo de la sustentación presencial (demo en local)             | [PENDIENTE]                                                   |

---

## 19. Git y publicación

**Estado (18 oct) [OBSERVADO en GitHub y en `git diff --stat`]:** repositorio `https://github.com/IsaksGir4/DataTutor.git`. La captura de GitHub muestra 6 commits; los de configuración (`chore(repo): reforzar .gitignore, actualizar .env.example y reservar corpus/…`) datan de "ayer", y el último, `73cedfd` "Documentación técnica y despliegue" (EvilNightmare010 y Copilot), de hace ~1 hora. Rama del compañero: `evilnightmare010-analyze-agent-project`. `git diff --stat main origin/evilnightmare010-analyze-agent-project` lista exactamente 11 archivos (README.md, `database.py`, `chat.py`, `docs/07`, `docs/08`, `docs/09`, `docs/evidencias/aplicacion-actual.png`, `App.jsx`, `styles.css`, `vercel.json`, `render.yaml`; +756/−26), lo que indica que `main` local no tiene diferencias adicionales respecto de su base.

**Qué se sube y qué no:**

- Sí: código, `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, `.env.example` (raíz y frontend), `docs/`, `keycloak/import/`, `compose.yml`, `render.yaml`, `frontend/vercel.json`, `eval/questions.jsonl`, `corpus/.gitkeep`, `corpus/README.md`.
- **No:** `.env`, `.env.*` (salvo `.env.example`), `frontend/.env`, `*.dump`, `node_modules/`, `dist/`, `backend/.venv`, **los PDFs del corpus**.

**Reglas del `.gitignore` vigentes** (verificadas con `git check-ignore -v`): `.env`, `.env.*`, `!.env.example`, `corpus/*` con `!corpus/.gitkeep` y `!corpus/README.md`, `*.dump`, `node_modules/`, `dist/`, `.venv/`, entre otras.

**Por qué mezclar la rama no pone en riesgo el entorno local.** `git merge` solo modifica archivos **versionados** que difieren entre las dos ramas. No toca `.env`, `corpus/`, `.venv`, `node_modules`, el volumen de Docker ni la base de datos. Si algún archivo local sin commit fuera a sobrescribirse, Git se detiene con un error y no hace nada. Además, `git merge --abort` deshace una mezcla sin confirmar.

**Procedimiento seguro (Git Bash, desde la raíz del repositorio):**

```bash
git status                                   # debe estar limpio; si no, commit o stash antes
git branch --show-current                    # confirmar que estás en main
git branch backup-antes-merge-18oct          # red de seguridad (solo un puntero, no copia archivos)
git fetch origin
git log --oneline main..origin/evilnightmare010-analyze-agent-project
git merge-base --is-ancestor main origin/evilnightmare010-analyze-agent-project && echo "FAST-FORWARD posible"
git merge --no-commit --no-ff origin/evilnightmare010-analyze-agent-project
git status                                   # revisar qué se va a incorporar
```

Luego, antes de confirmar:

1. `grep -n "CHAT_MODEL\|NUM_CTX\|NUM_PREDICT" backend/app/config/settings.py backend/app/llm/chat.py`.
2. Desde `backend/`: `uv run pytest -v` (debe dar `5 passed`; valida `init_database()`).
3. Desde `frontend/`: `npm run lint` y `npm run build`.
4. Arrancar backend y frontend en local y probar login, un chat respondido, un rechazo y una subida.

Si todo está bien: `git commit -m "merge: rama del equipo (README, despliegue, frontend, docs)"` y `git push`. Si algo falla: `git merge --abort` y la copia local queda exactamente como estaba. Si hay conflicto en `docs/07_PROJECT_STATE.md`, quedarse con la versión de este documento.

**Plan de commits pendientes (si se agregan cambios propios):** pequeños y por carpeta (`git add backend/…`, `git add docs/…`); revisar `git status` y `git diff --cached --name-only` antes de cada commit; no usar `git add .` a ciegas.

**Comprobaciones habituales:**

```bash
git check-ignore -v .env frontend/.env corpus/ejemplo.pdf
git ls-files | grep -E '\.(pdf|dump)$|(^|/)\.env$' || echo "OK: nada sensible versionado"
```

- Si `git ls-files corpus` lista PDFs que ya estaban versionados, `git rm --cached <archivo>` los saca del índice sin borrarlos del disco. Si ya se empujaron a GitHub, siguen en el historial: reescribirlo es un paso aparte que no debe hacerse a la ligera.

---

## 20. Hoja de ruta

| Fase | Objetivo                                                                                                           | Fecha objetivo | Estado                       |
| ---- | ------------------------------------------------------------------------------------------------------------------ | -------------- | ---------------------------- |
| 0    | Repo, estructura, `pyproject` (`uv`), compose (Postgres + Keycloak), `.env.example`, script de verificación | 5 oct          | ✅                           |
| 1    | Auditoría del corpus, PyMuPDF, chunking, embeddings, HNSW, ingesta CLI idempotente                                | 5–6 oct       | ✅                           |
| 2    | Grafo LangGraph, pruebas con fakes, CLI de chat y evaluación inicial                                              | 6–11 oct      | ✅                           |
| 3    | FastAPI, JWT de Keycloak, `/chat`, historial, aislamiento                                                        | 7–13 oct      | ✅                           |
| 4    | Subida asíncrona, listar/borrar, estados, cascada                                                                 | 8–16 oct      | ✅                           |
| 5    | Frontend: login, chat con fuentes, historial, documentos, errores, logout; corrección de defectos                 | 9–17 oct      | ✅                           |
| 6    | Integración local completa, guion de demo (rechazo + subida de la tesis), calibración                            | 17–18 oct     | 🔄 Cerrando (falta merge y ensayo) |
| 7    | Evaluación completa, `bge-m3` vs `nomic-embed-text`, CI, despliegue público fuera del campus                 | 17–18 oct     | 🔄 Parcial (`render.yaml`, `vercel.json` y Postgres de Render listos; backend en Render en curso; evaluación, CI y embeddings pendientes) |
| 8    | README, diagrama, documento técnico, diapositivas                                                                 | 17–18 oct     | 🔄 Parcial (README y documento técnico en Markdown; faltan PDF, diagrama y diapositivas) |
| 9    | Ensayo de sustentación y colchón sin funcionalidades nuevas                                                      | 18 oct         | ⬜                           |

---

## 21. Próximas acciones

**Orden sugerido para cerrar hoy (la entrega es el 18 oct):**

1. **Mezclar la rama del equipo** con el procedimiento de §19 (respaldo, `--no-commit`, `pytest`, `lint`, `build`, prueba de humo), y `git push`.
2. **Verificar `init_database()`** (§11): import sin base, HNSW y restricción única en una base vacía.
3. **Runner de evaluación** (`scripts/run_eval.py`) con métricas guardadas en `docs/evidencias/` (requisito pendiente).
4. **Pruebas del respaldo léxico** con fakes (sin LLM) y registrar `uv run pytest -v` completo.
5. **Despliegue (Anexo A):** terminar backend en Render y frontend en Vercel; verificar solo `/health` desde una red externa; no declarar URLs ni funcionalidades que no se hayan comprobado.
6. **Documento técnico:** completar la asignatura, agregar la sección de corpus y de evaluación, anexar capturas propias, exportar a PDF.
7. **Demo:** extracto de la tesis con texto seleccionable, subida desde la UI y pregunta sobre su contenido; guion con rechazo incluido; ensayar en local con Ollama en CPU y precalentar el modelo.
8. **Diagrama y diapositivas.**
9. **Después de entregar o si sobra tiempo:** revisar "automatización en ML", citas `[n]` y *grounding*, `rewrite_query`, CI, latencia por nodo, convertir `INTELIGENCIA_ARTIFICIAL` a `global`, comparación de embeddings.

---

## 22. Siguiente prompt para el Gem

> Estamos en DataTutor, entrega HOY 18 oct. Usa este `PROJECT_STATE.md` como contexto inicial, pero inspecciona los archivos reales que te comparta antes de asumir que algo está aplicado. El `.env` local usa PostgreSQL de Docker; la base de Render NO va en ese archivo. Mi compañero propuso una rama (README raíz, `render.yaml`, `frontend/vercel.json`, docs 08 y 09, `init_database()` en `backend/app/core/database.py`, `chat.py` leyendo settings, mejoras de `App.jsx` y `styles.css`) que voy a mezclar con el procedimiento de §19.
>
> Reglas: no cambies `SIM_THRESHOLD` ni `SIM_LOW`, no borres ni reingieras datos, no uses `docker compose down -v`, no escribas versiones de memoria, no pegues contraseñas. Dime la terminal (PowerShell, cmd o Git Bash) antes de cada comando y espera mi confirmación entre tareas.
>
> Tareas, en este orden:
> 1. Revisar `init_database()`: ¿se ejecuta al importar? ¿rompe `pytest` o scripts si Postgres está caído? ¿crea el índice HNSW y `uix_owner_sha256` en una base vacía? Propón un cambio mínimo solo si hay un problema real.
> 2. Escribir `backend/scripts/run_eval.py`: lee `eval/questions.jsonl` (pídeme el formato), llama al agente y reporta aciertos, rechazos correctos, falsos negativos y latencia p50/p95; guarda los resultados en `docs/evidencias/`.
> 3. Pruebas unitarias de `_has_direct_lexical_evidence` y `grade_context` con fakes, sin LLM.
> 4. Un workflow de GitHub Actions con `vite build` y `ruff` (sin `pytest` si requiere la base real).
> 5. Revisar `render.yaml` y `docs/09_GUIA_DESPLIEGUE.md`: comando de arranque con `$PORT`, prefijo `postgresql+psycopg://` en `DATABASE_URL` y `CORS_ORIGINS` con el origen de Vercel.
> 6. Actualizar `PROJECT_STATE.md` con lo que se logre.

---

## 23. Variables de entorno (nombres; valores locales en `.env`)

`DATABASE_URL`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `OLLAMA_URL`, `OLLAMA_KEEP_ALIVE`, `CHAT_MODEL`, `EMBED_MODEL`, `EMBED_DIM`, `NUM_CTX`, `TEMPERATURE`, `NUM_PREDICT`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`, `SIM_THRESHOLD`, `SIM_LOW`, `MAX_UPLOAD_MB`, `KEYCLOAK_URL`, `KEYCLOAK_JWKS_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_AUDIENCE`, `KC_ADMIN_USER`, `KC_ADMIN_PASSWORD`, `CORS_ORIGINS`, `VITE_API_BASE_URL`, `VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM`, `VITE_KEYCLOAK_CLIENT_ID`, `VITE_MAX_UPLOAD_MB`; solo si se usa un túnel: `NGROK_AUTHTOKEN`.

No copiar valores secretos a este documento, a `.env.example`, a Git ni a un chat nuevo.

---

## 24. Historial de este documento

- **17 oct (tarde):** fusión de la versión del usuario, la guía definitiva y la evidencia del día. Se retiraron textos obsoletos (defectos de UI abiertos, pytest 4/1 fallando, constantes locales de umbral). Se añadieron: runbook condensado, contrato de API, modelo de datos, incidencias resueltas, riesgos priorizados, seguimiento de requisitos, política de Git y corpus, y el respaldo léxico con sus limitaciones.
- **18 oct (compañero):** se añadieron mejoras de frontend, `render.yaml`, `vercel.json`, documentos 08 y 09, `init_database()` y el cliente de chat configurable; no se actualizaron §1, §8, §12, §17, §18, §19 ni §22.
- **18 oct (noche):** consolidación. Corpus real de 7 documentos y 7 932 chunks (consulta a `documents`); corregida la nota de visibilidad (los libros grandes son globales); descartada la visibilidad como causa del rechazo de "automatización en ML" (consulta a `conversations`); resultado de `pytest` pre-merge (5 passed en 2.91 s); incidencia del `.env` local apuntando a Render; procedimiento seguro de merge; estructura, requisitos, riesgos, hoja de ruta, próximas acciones y prompt del Gem actualizados; añadido el Anexo A.

---

## Anexo A. Despliegue público (Render + Vercel)

**Estado [OBSERVADO/REPORTADO]:** el equipo está desplegando el frontend en Vercel (compañeros) y el backend en Render (usuario). Se creó un PostgreSQL administrado en Render. `render.yaml`, `frontend/vercel.json` y `docs/09_GUIA_DESPLIEGUE.md` están en la rama del compañero.

**Qué sí se puede demostrar públicamente:** `GET https://<servicio-render>/api/v1/health`, que no requiere token ni depende de Ollama o Keycloak.

**Qué no puede funcionar hoy, y por qué:**

| Componente | Limitación |
| ---------- | ---------- |
| Login en Vercel | `login-required` redirige a la URL de Keycloak configurada. Con `localhost:8080`, el navegador del visitante intenta su propia máquina. Hace falta un Keycloak público con `redirectUris`, `webOrigins` e `iss` coherentes |
| Validación del JWT en Render | `KEYCLOAK_JWKS_URL` apunta a `127.0.0.1`: Render no puede alcanzarlo; los endpoints protegidos fallarían |
| Chat en Render | `OLLAMA_URL=http://127.0.0.1:11434` no es alcanzable; `POST /chat` devolvería 503. Además, la base de Render está vacía (sin corpus) |
| Corpus en Render | Los 7 932 chunks viven en la base local; llevarlos exigiría `pg_dump`/`pg_restore` y, sin Ollama accesible, igualmente no se podría consultar |

**Variables del servicio web en Render (panel de Render, no `.env` local):**

- `DATABASE_URL`: usar la *Internal Database URL* de Render y cambiar el prefijo `postgresql://` por `postgresql+psycopg://` (sin `+psycopg`, SQLAlchemy busca psycopg2). Desde una máquina externa (solo para pruebas) la URL externa necesita `?sslmode=require`.
- `CORS_ORIGINS`: `http://localhost:5173` y el origen exacto de Vercel, sin barra final.
- `OLLAMA_URL`, `KEYCLOAK_URL`, `KEYCLOAK_JWKS_URL`: no tienen un destino alcanzable; no declarar que funcionan.
- Comando de arranque: debe escuchar en `0.0.0.0` y en `$PORT` (comprobar en `render.yaml`).
- Si el backend importa `init_database()`, la extensión `vector` debe poder crearse en la base de Render (Render permite `pgvector`).

**Variables en Vercel:** `VITE_API_BASE_URL` = URL de Render + `/api/v1`; `VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM`, `VITE_KEYCLOAK_CLIENT_ID`; `frontend/vercel.json` conserva el acceso a las rutas de la SPA.

**Qué escribir en la entrega (sin afirmar de más):** las URLs reales de Render y Vercel solo si se verificaron desde una red externa; indicar que la demo completa (login, chat, carga) corre en local porque Keycloak y Ollama locales no son accesibles desde internet; verificar y mostrar `/health` público. No presentar una URL como evidencia hasta comprobar login, chat, carga y protección de endpoints.