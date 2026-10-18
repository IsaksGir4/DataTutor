# Guía de despliegue — Render y Vercel

Esta guía corresponde a la decisión del equipo: publicar el frontend y el backend para obtener URLs públicas, pero mantener la demostración funcional completa con Keycloak, Ollama y el corpus local. Por eso, las URLs públicas deben presentarse como evidencia de publicación y salud del servicio, mientras que la demo de login, chat y carga se ejecuta localmente.

## 1. Preparación en GitHub

1. Confirma que el repositorio no incluya `.env`, PDFs del corpus, volcados `.dump` ni `frontend/node_modules`.
2. Revisa estos archivos nuevos:
   - `render.yaml`
   - `frontend/vercel.json`
   - `docs/08_DOCUMENTO_TECNICO.md`
   - `docs/09_GUIA_DESPLIEGUE.md`
   - `docs/evidencias/aplicacion-actual.png`
3. Haz push de la rama con los cambios a GitHub.

## 2. Backend y PostgreSQL en Render

### Crear el servicio

1. Entra a [render.com](https://render.com) y crea una cuenta o inicia sesión con GitHub.
2. Selecciona **New → Blueprint** y elige el repositorio.
3. Render detectará `render.yaml`.
4. Confirma la creación del servicio `datatutor-api` y la base `datatutor-db`.
5. Si Render solicita el plan de la base, usa el plan gratuito disponible para la práctica o el plan que el equipo tenga autorizado.

### Configurar PostgreSQL

Después de crear la base:

1. Abre la base `datatutor-db`.
2. Copia el **PSQL Command** de la página de información.
3. Conéctate desde una terminal con `psql`.
4. Ejecuta:

   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

El backend crea las tablas ORM al iniciar, pero la extensión `vector` debe existir antes de intentar guardar embeddings.

### Variables del backend

En el servicio `datatutor-api`, agrega o revisa:

| Variable | Valor para esta estrategia |
|---|---|
| `DATABASE_URL` | Se completa desde la base de Render |
| `OLLAMA_URL` | URL reservada/no funcional para la publicación técnica; el chat público no se anuncia como operativo |
| `CHAT_MODEL` | `qwen2.5:3b` |
| `EMBED_MODEL` | `bge-m3` |
| `EMBED_DIM` | `1024` |
| `NUM_CTX` | `4096` |
| `NUM_PREDICT` | `512` |
| `CHUNK_SIZE` | `1000` |
| `CHUNK_OVERLAP` | `200` |
| `TOP_K` | `4` |
| `SIM_THRESHOLD` | `0.65` |
| `SIM_LOW` | `0.50` |
| `MAX_UPLOAD_MB` | `30` |
| `KEYCLOAK_URL` | URL local solo para la demo; no permite login desde internet |
| `KEYCLOAK_JWKS_URL` | URL de JWKS correspondiente |
| `KEYCLOAK_REALM` | `datatutor` |
| `KEYCLOAK_CLIENT_ID` | `datatutor-web` |
| `KEYCLOAK_AUDIENCE` | `datatutor-web` |
| `CORS_ORIGINS` | URL pública de Vercel y, si se desea, `http://localhost:5173` |

> No inventes una URL de Keycloak u Ollama. Si se deja el servicio Render publicado sin esas dependencias accesibles, comprueba solamente `/api/v1/health` y documenta la limitación.

### Comprobar Render

Cuando el despliegue termine, abre:

```text
https://<servicio>.onrender.com/api/v1/health
```

El resultado esperado es:

```json
{"status":"ok","service":"datatutor"}
```

## 3. Frontend en Vercel

1. Entra a [vercel.com](https://vercel.com) e inicia sesión con GitHub.
2. Selecciona **Add New → Project**.
3. Importa el repositorio `DataTutor`.
4. Configura **Root Directory** como `frontend`.
5. Vercel detectará Vite.
6. Usa:
   - Build command: `npm run build`
   - Output directory: `dist`
   - Install command: `npm ci`
7. Agrega estas variables:

   ```text
   VITE_API_BASE_URL=https://<servicio>.onrender.com/api/v1
   VITE_KEYCLOAK_URL=<URL pública o documentada de Keycloak>
   VITE_KEYCLOAK_REALM=datatutor
   VITE_KEYCLOAK_CLIENT_ID=datatutor-web
   VITE_MAX_UPLOAD_MB=30
   ```

8. Pulsa **Deploy**.

`frontend/vercel.json` redirige las rutas de la SPA a `index.html`.

## 4. Prueba manual local completa

Para la demostración calificada, abre tres terminales:

### Terminal 1 — servicios

```powershell
docker compose up -d
docker compose ps
```

Comprueba que `datatutor-postgres` esté `healthy` y `datatutor-keycloak` esté `Up`.

### Terminal 2 — Ollama

```powershell
$env:CUDA_VISIBLE_DEVICES="-1"
$env:OLLAMA_LLM_LIBRARY="cpu_avx2"
ollama serve
```

En otra terminal, confirma:

```powershell
ollama list
```

Deben aparecer `qwen2.5:3b` y `bge-m3`.

### Terminal 3 — backend

```powershell
Set-Location .\backend
uv run uvicorn app.main:app --reload
```

### Terminal 4 — frontend

```powershell
Set-Location .\frontend
npm run dev
```

Abre `http://localhost:5173`.

## 5. Guion de pruebas de la sustentación

1. Abrir el frontend local.
2. Iniciar sesión con Keycloak.
3. Formular una pregunta respondible sobre un libro indexado.
4. Verificar que aparecen la respuesta y las fuentes.
5. Preguntar algo ajeno al corpus, por ejemplo una receta de sushi.
6. Verificar el estado `REJECTED` y el mensaje de información insuficiente.
7. Subir un PDF pequeño de prueba.
8. Esperar el estado `READY`.
9. Formular una pregunta cuya respuesta dependa del PDF recién cargado.
10. Abrir una conversación del historial y mostrar sus fuentes.
11. Mostrar brevemente `backend/app/agents/graph.py`.
12. Mostrar las URLs públicas de Vercel y Render, aclarando que la demo completa usa el entorno local por las dependencias de Ollama y Keycloak.

## 6. Evidencias que deben anexarse al PDF

- Captura de login.
- Captura de una respuesta `ANSWERED` con fuentes.
- Captura de un rechazo `REJECTED`.
- Captura de carga `READY` de un documento nuevo.
- Captura de una pregunta respondida con el documento nuevo.
- Captura de `GET /api/v1/health` en Render.
- Captura de la URL pública de Vercel.
- Captura del grafo LangGraph en el repositorio.
