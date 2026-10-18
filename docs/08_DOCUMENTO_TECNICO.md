# Documento técnico — DataTutor

> **Nota:** este archivo es la fuente editable para construir el PDF final. Los campos entre corchetes deben completarse con datos reales del equipo y del despliegue; no deben reemplazarse por información inventada.

## 1. Nombre del proyecto e integrantes

**Proyecto:** DataTutor — Tutor inteligente RAG para datos.  
**Integrantes:** Michelle Ruiz Segura; Isaac Camilo Giraldo Gómez; Juan José Ramírez Pulgarín.  
**Asignatura:** [Nombre de la asignatura].  
**Fecha:** 18 de octubre de 2026.

## 2. Tema y problema

DataTutor se enfoca en bases de datos, ingeniería de datos y ciencia de datos. El problema abordado es la dificultad de consultar de forma rápida y confiable material técnico extenso. Una respuesta generada únicamente con el conocimiento paramétrico de un modelo puede ser imprecisa o no corresponder con los documentos estudiados.

La solución permite cargar documentos, convertirlos en fragmentos vectorizados y hacer preguntas sobre ellos. El agente responde con base en la información recuperada, muestra las fuentes utilizadas y rechaza la consulta cuando no encuentra evidencia suficiente.

## 3. Arquitectura general

La interfaz React se autentica con Keycloak mediante OIDC Authorization Code con PKCE. Las peticiones autorizadas llegan a FastAPI, que valida el JWT, filtra los datos por `owner_id` y delega la pregunta al grafo LangGraph. El grafo utiliza Ollama para clasificación, evaluación y generación; utiliza `bge-m3` para embeddings y PostgreSQL con pgvector para recuperar fragmentos.

```text
Usuario
  │
  ▼
Frontend React + Vite ─── OIDC/PKCE ─── Keycloak
  │ Bearer JWT
  ▼
FastAPI ─── LangGraph ─── Ollama qwen2.5:3b
  │              │
  │              └──── Ollama bge-m3
  ▼
PostgreSQL 16 + pgvector
```

## 4. Tecnologías utilizadas

| Capa | Tecnología | Propósito |
|---|---|---|
| Frontend | React, Vite, CSS | Chat, documentos, historial y estados de la aplicación |
| Autenticación | Keycloak, `keycloak-js` | Login, sesión, logout y tokens OIDC |
| Backend | Python 3.12, FastAPI | API REST y validación de solicitudes |
| Agente | LangChain y LangGraph | Flujo explícito de recuperación y respuesta |
| Modelo local | Ollama, `qwen2.5:3b` | Clasificación, evaluación y generación |
| Embeddings | Ollama, `bge-m3` | Representación vectorial de fragmentos |
| Persistencia | PostgreSQL 16 + pgvector | Metadatos, historial y búsqueda vectorial |
| Contenedores | Docker Compose | PostgreSQL y Keycloak en desarrollo |

## 5. Backend

La API se encuentra bajo el prefijo `/api/v1`. Los controladores reciben y validan las solicitudes; los servicios coordinan la lógica de negocio; los repositorios concentran el acceso a SQLAlchemy y pgvector; y los módulos `agents` contienen el estado, nodos y grafo.

Endpoints principales:

- `GET /health`: comprobación pública de disponibilidad.
- `GET /me`: perfil del usuario autenticado.
- `POST /chat`: pregunta al agente y respuesta con decisión, fuentes y latencia.
- `GET/DELETE /conversations`: historial propio del usuario.
- `POST/GET/DELETE /documents`: carga, consulta y eliminación de documentos propios.

La subida devuelve `202` y procesa el PDF en segundo plano. Los estados de ingesta son `pending`, `processing`, `ready` y `failed`.

## 6. Frontend

El frontend ofrece:

- Inicio de sesión y cierre de sesión con Keycloak.
- Chat con mensajes de usuario y agente.
- Insignias de decisión: `answered`, `rejected`, `clarify` y `smalltalk`.
- Fuentes recuperadas con documento, página, fragmento y similitud.
- Historial seleccionable y eliminable.
- Carga y eliminación de documentos propios.
- Mensajes de error y estados de carga visibles.

La interfaz conserva una identidad oscura y azul, incluye foco visible, navegación por teclado en conversaciones, etiquetas accesibles, estados vacíos y adaptación para pantallas pequeñas.

## 7. Agente y flujo LangGraph

El grafo implementado en `backend/app/agents/graph.py` sigue este flujo:

1. `receive` normaliza la entrada y prepara el estado.
2. `classify_intent` clasifica saludo, pregunta técnica o consulta fuera de dominio.
3. `retrieve` genera el embedding y recupera los fragmentos más cercanos.
4. `grade_context` evalúa el puntaje y la suficiencia semántica.
5. `rewrite_query` permite un único intento de reescritura en zona gris.
6. `generate_answer` responde usando el contexto numerado.
7. `refuse` devuelve el rechazo explícito cuando no hay evidencia.
8. `clarify` solicita precisión en preguntas ambiguas.
9. `save_history` cierra el flujo; la persistencia del turno se completa en el servicio de chat.

Todos los caminos terminan en persistencia y no existe un ciclo sin límite.

## 8. Modelo local y base vectorial

El modelo de chat es `qwen2.5:3b`, ejecutado con Ollama en el equipo local. Se seleccionó por su tamaño compatible con una máquina sin GPU y por permitir una demostración sin depender de un proveedor comercial externo. La limitación principal es la latencia en CPU.

Los embeddings se generan con `bge-m3` en 1024 dimensiones. PostgreSQL almacena cada fragmento, su documento de origen, página, propietario y vector. La recuperación usa distancia coseno y devuelve un puntaje normalizado como `1 - distancia`.

## 9. Carga y procesamiento de documentos

El flujo de carga es:

1. El usuario selecciona un PDF en el frontend.
2. El backend valida extensión, tamaño y duplicados.
3. PyMuPDF extrae el texto por página.
4. El texto se divide en fragmentos con solapamiento.
5. Ollama genera un embedding por fragmento.
6. Se almacenan documento, fragmentos y vectores en PostgreSQL.
7. El frontend consulta el estado hasta mostrar `ready` o `failed`.

El corpus de libros se mantiene fuera de GitHub. Esto protege materiales con derechos de autor y evita incluir archivos grandes en el repositorio.

## 10. Estrategias anti-alucinación

DataTutor implementa más de las dos estrategias mínimas solicitadas:

1. Umbral mínimo de similitud (`SIM_THRESHOLD` y `SIM_LOW`).
2. Nodo dedicado `grade_context`.
3. Prompt que limita la generación a los fragmentos recuperados.
4. Rechazo explícito con mensaje fijo.
5. Fuentes y fragmentos visibles en la interfaz.
6. Respaldo léxico conservador para reducir falsos rechazos cuando existe evidencia directa.

El rechazo utilizado por el agente es: “No tengo suficiente información en mi base de conocimiento para responder esa pregunta. Te sugiero cargar documentos relacionados con el tema.”

## 11. Seguridad y autenticación

Keycloak gestiona las credenciales y emite tokens mediante OIDC Authorization Code + PKCE S256. FastAPI valida firma, emisor, expiración y audiencia del JWT. Excepto `/health`, los endpoints requieren autorización.

Las consultas filtran por `owner_id = sub`, de modo que un usuario no puede consultar conversaciones o documentos ajenos. Los tokens del frontend se mantienen en memoria. Los secretos viven en `.env`, que no se versiona. CORS se limita al origen configurado del frontend.

## 12. Despliegue

**Entorno local verificado:**

- Frontend: `http://localhost:5173`
- Backend: `http://127.0.0.1:8000`
- Keycloak: `http://localhost:8080`
- PostgreSQL: `127.0.0.1:5432`
- Ollama: `http://127.0.0.1:11434`

**Despliegue público planificado:**

- Frontend: Vercel, desde la carpeta `frontend/`.
- Backend: Render, como servicio web de Python desde la carpeta `backend/`.
- Base vectorial: PostgreSQL administrado por Render con la extensión `vector`.
- Autenticación: Keycloak debe estar publicado en una URL accesible desde el navegador y desde Render.
- Modelo local: Ollama debe ejecutarse en un servicio accesible desde Render. El Ollama instalado en el computador solo sirve para la demo local; `http://127.0.0.1:11434` no funciona desde Render.

**URL pública del frontend:** [Completar después de publicar en Vercel].  
**URL pública del backend:** [Completar después de publicar en Render].  
**URL pública de Keycloak:** [Completar después de publicar o elegir el servicio de autenticación].  
**URL pública de Ollama:** [Completar después de alojar el modelo o definir el servicio de inferencia].

Render permite PostgreSQL con `pgvector`; Vercel puede construir y servir el frontend Vite. Sin embargo, para que el despliegue público sea realmente funcional no basta con publicar solo dos servicios: el backend también necesita acceso público a Keycloak y a Ollama. Las URLs y variables deben completarse únicamente después de probar login, chat, carga y protección de endpoints desde internet.

No se debe presentar una URL pública como evidencia hasta comprobar login, chat, carga de documentos y protección de endpoints desde una red externa.

## 13. Evidencias de funcionamiento

Durante la validación local del 18 de octubre de 2026:

- Docker levantó PostgreSQL/pgvector y Keycloak.
- PostgreSQL quedó con las tablas `documents`, `chunks`, `conversations` y `messages`.
- El backend ejecutó `5 passed` en `backend/tests/test_api_contracts.py`.
- `npm run lint` terminó correctamente con advertencias informativas de código preexistente.
- `npm run build` terminó correctamente con Vite.
- La interfaz contiene evidencia visual de respuestas, rechazos, fuentes, historial y documentos. La captura inicial se conserva en [`docs/evidencias/aplicacion-actual.png`](evidencias/aplicacion-actual.png).

Para el PDF final se deben anexar capturas propias de login, respuesta sustentada, rechazo, carga de documento y despliegue público.

## 14. Problemas encontrados y conclusiones

El entorno local depende de Docker, Keycloak, PostgreSQL y Ollama; si alguno no está disponible, la aplicación no puede completar el flujo. El modelo pequeño ejecutado en CPU puede producir latencias de varios segundos. Además, la calidad de las respuestas depende de la extracción textual de los PDFs y de la correcta calibración del umbral.

Durante la verificación se encontró que una base PostgreSQL recién creada no tenía tablas. Se corrigió el arranque del backend para crear la extensión `vector` y las tablas ORM cuando la base está vacía. Esto permite reproducir una instalación local limpia sin borrar volúmenes existentes.

DataTutor cumple la arquitectura solicitada: API protegida, frontend, autenticación, agente codificado con LangChain y LangGraph, modelo local, RAG con pgvector, carga de documentos y rechazo explícito. Antes de la entrega final todavía deben agregarse las URLs públicas verificadas, las capturas definitivas del despliegue y la evidencia de una pregunta dependiente de un documento recién cargado.
