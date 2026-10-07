# CONTRATO DE LA API (v1)

Prefijo: `/api/v1`. JSON salvo la subida (multipart). **Todo protegido con Bearer JWT de Keycloak salvo `GET /health`.**

## Autenticación
- El frontend inicia sesión con `keycloak-js` (Authorization Code + PKCE). El backend **no** maneja contraseñas.
- Header: `Authorization: Bearer <access_token>`.
- Variables: `KEYCLOAK_URL` (por defecto `http://localhost:8080`), `KEYCLOAK_REALM` (`datatutor`), `KEYCLOAK_CLIENT_ID` (`datatutor-web`).
- Emisor esperado: `{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}`. Claves: `{emisor}/protocol/openid-connect/certs`.
- Validación: firma RS256, `iss`, `exp` y `aud`/`azp`. `owner_id = sub`.
- Rol `admin` (opcional): puede borrar documentos `scope=global`.

## Endpoints
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/health` | No | Estado de API, PostgreSQL y Ollama (sin datos sensibles) |
| GET | `/me` | Sí | `sub`, `preferred_username`, roles |
| POST | `/chat` | Sí | Un turno del agente |
| POST | `/chat/stream` | Sí | (Opcional) SSE con pasos y tokens |
| GET | `/conversations` | Sí | Lista las del usuario (paginada) |
| GET | `/conversations/{id}/messages` | Sí | Historial de una conversación |
| DELETE | `/conversations/{id}` | Sí | Borra conversación propia |
| POST | `/documents` | Sí | Sube archivo; responde **202** |
| GET | `/documents` | Sí | Lista propios + globales (con `status`) |
| GET | `/documents/{id}` | Sí | Estado y metadatos |
| DELETE | `/documents/{id}` | Sí | Borra propio (chunks incluidos) |
| POST | `/search` | Sí (dev/admin) | Recuperación sin LLM, para calibrar el umbral |

## Esquemas principales
**POST `/chat`** → request `{ "question": str (1..2000), "conversation_id": str|null }`
```json
{
  "conversation_id": "…",
  "answer": "…",
  "decision": "answered | rejected | clarify | smalltalk",
  "sources": [{"document": "Silberschatz 6ed", "page": 123, "snippet": "…", "score": 0.78}],
  "latency_ms": 18432
}
```
Un rechazo del agente es **HTTP 200** con `decision="rejected"` (no es un error del sistema).

**POST `/documents`** → multipart `file`. Reglas: tamaño ≤ `MAX_UPLOAD_MB` (30), extensión en {pdf, txt, md} (v1), verificación del tipo real. Respuesta **202**: `{ "id": "…", "status": "pending" }`. Si el hash ya existe para ese usuario → **409** con el `id` existente.

**GET `/documents`** → `[{id, filename, scope, status, pages, chunks_count, size_bytes, created_at, error}]`.

## Errores (formato único)
```json
{ "error": { "code": "document_too_large", "message": "…", "request_id": "…" } }
```
| HTTP | Cuándo |
|---|---|
| 401 | Falta token o es inválido/vencido |
| 403 | Sin permiso (borrar documento global sin rol) |
| 404 | Recurso inexistente **o ajeno** (no revelar su existencia) |
| 409 | Documento duplicado |
| 413 | Archivo demasiado grande |
| 415 | Tipo de archivo no permitido |
| 422 | Validación de entrada |
| 429 | Demasiadas solicitudes (límite por usuario en `/chat` y `/documents`) |
| 503 | Ollama o PostgreSQL no disponibles |

## Reglas transversales
- `request_id` en cada respuesta y en los logs.
- Los controladores solo validan y delegan en servicios; sin lógica de negocio.
- Excepciones de dominio (`DocumentTooLarge`, `DuplicateDocument`, `LLMUnavailable`…) mapeadas a HTTP en un único manejador.
- CORS: solo el origen del frontend (`CORS_ORIGINS`).
- OpenAPI (`/docs`) activo en desarrollo; protegerlo o desactivarlo en el despliegue público.
