# PROJECT_STATE — DataTutor

> Documento vivo. Se actualiza al cerrar cada fase y se **pega al inicio de cada chat nuevo** con el Gem (si lo pegado difiere de los archivos de conocimiento, manda lo pegado).
> Última actualización: 5 oct 2026 · Fase actual: **0**

## Decisiones vigentes
- Backend: Python 3.12 + FastAPI + uv, ejecutado desde PyCharm en el host · IDE frontend: WebStorm o VS Code
- Agente: LangChain + LangGraph (`StateGraph` explícito)
- Chat: `qwen2.5:3b` (por defecto; 7B/8B solo si la RAM lo permite tras medir) · Embeddings: `bge-m3` (comparar con `nomic-embed-text`) · Ollama nativo en Windows
- Datos: PostgreSQL 16 + pgvector (Docker), SQLAlchemy 2.0. Keycloak usa **su propia base** (`keycloak`) en el mismo contenedor de Postgres
- Auth: Keycloak (OIDC + PKCE); el backend valida el JWT con JWKS
- Frontend: React + Vite + `keycloak-js`
- Extracción PDF: PyMuPDF por página
- Fases 0 a 6: todo en localhost, **sin ngrok ni proxy**. El despliegue público es solo la Fase 7, hecha fuera del campus

## Versiones fijadas
Las fija `uv.lock` al terminar la Fase 0 (se instalan las versiones vigentes compatibles y luego se congelan). **No se copian de memoria del asistente.** Pegar aquí la salida de `uv pip list` de los paquetes principales.

## Estructura actual del repo
(pegar el árbol real tras cada fase)

## Corpus
- Ola 1: Silberschatz (BD, es) · Fundamentals of Data Engineering Concepts (en) · Libro GUIA ingeniería de datos (es) · Fundamentos de Ingeniería de Datos (es, 38 KB, prueba de humo) · Principles of Data Science (en) · Seven ways… (en) · Understanding… failure (en)
- Ola 2: EDR teoría BD · Big Book of Data Warehousing and BI · Python programming for Data analysis · INTELIGENCIA_ARTIFICIAL · Data science route
- Fuera de la v1: Geometric Data Science book
- Reservada para la demo (subida en vivo): tesis sobre control predictivo no lineal basado en modelo borroso (usar un extracto de ~30 páginas)
- Auditoría de PDFs (páginas, caracteres por página): (pegar resultado)

## Hoja de ruta
| Fase | Objetivo | Fechas | Estado |
|---|---|---|---|
| 0 | Repo, estructura, `pyproject` (uv), compose (Postgres + Keycloak), `.env.example`, script de verificación (Postgres con pgvector, Ollama chat y embedding, JWKS de Keycloak) | 5 oct | ⬜ |
| 1 | Auditoría del corpus, extracción por página, chunking, embeddings, índice HNSW, ingesta idempotente por CLI (ola 1) | 5–6 oct | ⬜ |
| 2 | Grafo LangGraph completo + pruebas con fakes + CLI de chat + conjunto de evaluación inicial | 6–7 oct | ⬜ |
| 3 | FastAPI + validación del JWT de Keycloak + `/chat` + historial | 7–8 oct | ⬜ |
| 4 | Subida de documentos asíncrona, listar y borrar, estados | 8–9 oct | ⬜ |
| 5 | Frontend: login Keycloak, chat con fuentes, documentos, errores, logout | 9–10 oct | ⬜ |
| 6 | Integración completa en local, guion de la demo (rechazo + subida de la tesis) y primera calibración del umbral | 11 oct | ⬜ |
| 7 | Evaluación completa (umbral, bge-m3 vs nomic), CI y **despliegue público** (Vercel/Netlify + ngrok) fuera del campus, con capturas y video | 12–14 oct | ⬜ |
| 8 | README, diagrama, documento técnico, diapositivas | 15–16 oct | ⬜ |
| 9 | Ensayo de la sustentación y colchón (sin funcionalidades nuevas) | 17–18 oct | ⬜ |

## Hecho
(vacío)

## Pendiente inmediato
- Crear el repo en GitHub y abrirlo en PyCharm con uv
- Levantar Postgres y Keycloak con Docker Compose (usar el `compose.yml` corregido)
- Descargar modelos en Ollama (`qwen2.5:3b`, `bge-m3`)
- Reutilizar el `realm-export.json` de Keycloak que ya funcionó (sin secretos)
- Ejecutar la auditoría de PDFs y pegar el resultado

## Problemas conocidos
(vacío)

## Variables de entorno (nombres; los valores van en `.env`)
`DATABASE_URL`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `OLLAMA_URL`, `OLLAMA_KEEP_ALIVE`, `CHAT_MODEL`, `EMBED_MODEL`, `EMBED_DIM`, `NUM_CTX`, `TEMPERATURE`, `NUM_PREDICT`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`, `SIM_THRESHOLD`, `SIM_LOW`, `MAX_UPLOAD_MB`, `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_AUDIENCE`, `KC_ADMIN_USER`, `KC_ADMIN_PASSWORD`, `CORS_ORIGINS`, `VITE_API_BASE_URL`, `VITE_KEYCLOAK_URL`; solo en la Fase 7: `NGROK_AUTHTOKEN`

## Siguiente prompt para el Gem
(escribir aquí la instrucción de la próxima fase)
