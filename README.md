# DataTutor

DataTutor es una aplicación web educativa que responde preguntas sobre bases de datos, ingeniería de datos y ciencia de datos usando RAG. El agente recupera fragmentos desde PostgreSQL con `pgvector` y genera respuestas con un modelo local de Ollama. Cuando el contexto no es suficiente, rechaza la pregunta explícitamente en lugar de completar la respuesta con conocimiento externo.

## Arquitectura

```text
React + Vite + keycloak-js
          │ OIDC / PKCE
       Keycloak
          │ JWT
      FastAPI
       ├── LangGraph: intención → recuperación → evaluación → respuesta/rechazo
       ├── Ollama: qwen2.5:3b + bge-m3
       └── PostgreSQL + pgvector
```

El código del backend está organizado por controladores, servicios, agentes, repositorios, esquemas y configuración. El frontend está en `frontend/`. La configuración de Docker levanta PostgreSQL/pgvector y Keycloak; Ollama se ejecuta nativamente en el equipo para aprovechar el modelo local.

## Requisitos

- Windows 10/11 con Docker Desktop.
- Python 3.12.7 y `uv`.
- Node.js y npm.
- Ollama con los modelos `qwen2.5:3b` y `bge-m3`.

## Configuración local

1. Copia `.env.example` como `.env` en la raíz y revisa los valores locales.
2. Inicia Docker Desktop.
3. Desde la raíz, levanta PostgreSQL y Keycloak:

   ```powershell
   docker compose up -d
   docker compose ps
   ```

4. En una terminal separada inicia Ollama en modo CPU si el equipo no tiene GPU disponible:

   ```powershell
   $env:CUDA_VISIBLE_DEVICES="-1"
   $env:OLLAMA_LLM_LIBRARY="cpu_avx2"
   ollama serve
   ```

   Verifica que existan los modelos:

   ```powershell
   ollama list
   ```

5. Inicia el backend:

   ```powershell
   Set-Location .\backend
   uv sync
   uv run uvicorn app.main:app --reload
   ```

   La API queda en `http://127.0.0.1:8000`. El endpoint público de salud es `GET /api/v1/health`; el resto requiere un JWT de Keycloak.

6. Inicia el frontend en otra terminal:

   ```powershell
   Set-Location .\frontend
   npm ci
   npm run dev
   ```

   Abre `http://localhost:5173`. Usa `localhost`, no `127.0.0.1`, porque el cliente OIDC está configurado para ese origen.

## Corpus e ingesta

Los PDFs del corpus no se versionan por su tamaño y licencia. Colócalos localmente en `corpus/` y utiliza el script de ingesta documentado en `backend/scripts/ingest_corpus.py`. La carga desde la interfaz acepta PDFs de hasta `MAX_UPLOAD_MB` y procesa el archivo en segundo plano; la interfaz muestra los estados `pending`, `processing`, `ready` o `failed`.

No borres el volumen de PostgreSQL para diagnosticar problemas. Antes de modificar el esquema o reingerir documentos, crea un respaldo con `pg_dump` y verifica el propietario (`owner_id`) de los documentos para conservar el aislamiento por usuario.

## Flujo del agente y control de alucinaciones

El grafo explícito de LangGraph ejecuta:

1. Normalización de la pregunta.
2. Clasificación de intención.
3. Recuperación por similitud coseno en `pgvector`.
4. Evaluación de suficiencia del contexto.
5. Reescritura limitada de la consulta cuando procede.
6. Generación con prompt restrictivo o rechazo explícito.
7. Persistencia del historial.

Se combinan umbral de similitud, juez de contexto, prompt basado únicamente en los fragmentos recuperados, rechazo fijo y fuentes visibles en la interfaz.

## Pruebas y calidad

Desde `backend/`:

```powershell
uv run pytest -v
```

Desde `frontend/`:

```powershell
npm run lint
npm run build
```

La documentación de requisitos, arquitectura, grafo, contrato de API, modelo de datos, estándares y estado del proyecto está en `docs/`.

## Seguridad y límites conocidos

- Keycloak gestiona el registro, login, sesión y logout mediante OIDC Authorization Code + PKCE.
- La API valida el JWT y filtra conversaciones, documentos y fragmentos por `owner_id`.
- Los tokens del frontend permanecen en memoria; no se guardan en `localStorage`.
- Los secretos y el corpus local deben permanecer fuera de Git.
- El modelo `qwen2.5:3b` funciona en CPU, pero la latencia puede ser alta. La disponibilidad de Ollama y PostgreSQL es necesaria para responder preguntas.

## Despliegue

El plan de despliegue es:

- **Vercel:** frontend Vite desde `frontend/`, con las variables `VITE_API_BASE_URL`, `VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM` y `VITE_KEYCLOAK_CLIENT_ID`.
- **Render:** backend FastAPI desde `backend/`, usando `render.yaml` y PostgreSQL administrado con `pgvector`.

Publicar únicamente Vercel y Render no es suficiente para el flujo completo: Render no puede acceder al Ollama instalado en el computador ni al Keycloak local. Para una demo pública se necesita además una URL accesible de Keycloak y un servicio Ollama/inferencia accesible desde Render. `OLLAMA_URL=http://127.0.0.1:11434` solo es válido en la demostración local.

Después de crear los servicios, configura en Render `OLLAMA_URL`, `KEYCLOAK_URL`, `KEYCLOAK_JWKS_URL` y `CORS_ORIGINS`. En Vercel configura la URL real de Render como `VITE_API_BASE_URL` y la URL pública de Keycloak como `VITE_KEYCLOAK_URL`. El archivo `frontend/vercel.json` conserva el acceso correcto a la SPA.

No se deben publicar URLs, credenciales ni afirmaciones de despliegue hasta haber verificado login, chat, carga de documentos y protección de endpoints desde una red externa.

La guía paso a paso está en [`docs/09_GUIA_DESPLIEGUE.md`](docs/09_GUIA_DESPLIEGUE.md). Para la estrategia actual del equipo, la demo completa permanece local porque Keycloak y Ollama locales no son accesibles desde internet; Render y Vercel se presentan con sus URLs reales y se verifica al menos la salud pública del backend.
