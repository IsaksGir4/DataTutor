# ESTÁNDARES DE CÓDIGO Y PROTOCOLO DE TRABAJO

## 1. Estructura del backend (Anexo A adaptado)

```
backend/
  app/
    main.py                # crea la app, registra routers y manejadores de error
    config/                # settings.py (pydantic-settings), logging.py
    core/                  # security.py (validación JWT), errors.py, deps.py (Depends)
    controllers/           # routers FastAPI: solo validan y delegan
    schemas/               # modelos Pydantic de entrada/salida
    services/              # lógica de negocio: documents, chat, ingestion
    repositories/          # acceso a PostgreSQL (único lugar que usa SQLAlchemy y pgvector)
    agents/                # state.py, nodes/, graph.py, prompts.py
    vectorstore/           # retriever.py (adaptador BaseRetriever sobre repositories)
    llm/                   # fábricas de ChatOllama y OllamaEmbeddings
  tests/  eval/  scripts/  pyproject.toml  uv.lock  Dockerfile
frontend/ docs/ docker-compose.yml .env.example README.md
```

## 2. Patrones y por qué

| Patrón                                   | Dónde                       | Beneficio                                              |
| ----------------------------------------- | ---------------------------- | ------------------------------------------------------ |
| Capas controller → service → repository | Todo el backend              | Rúbrica de arquitectura; pruebas aisladas             |
| Inyección de dependencias (`Depends`)  | `core/deps.py`             | Sustituir LLM, retriever o repositorio por dobles      |
| Adapter                                   | `vectorstore/retriever.py` | Abstraer la búsqueda de pgvector sin acoplar el grafo |
| Factory                                   | `llm/`                     | Cambiar modelo por variable de entorno                 |
| Configuración tipada                     | `config/settings.py`       | Falla al arrancar si falta una variable                |
| State machine                             | `agents/graph.py`          | El grafo explícito que se explica en la sustentación |
| Idempotencia (hash)                       | `services/ingestion.py`    | Reintentos sin duplicar                                |
| Excepciones de dominio                    | `core/errors.py`           | Un solo mapeo a HTTP                                   |

## 3. Reglas de código

- Python 3.12, tipos en todas las firmas, Pydantic v2. Formato y lint con **ruff**.
- Funciones cortas; nombres en inglés para código, mensajes al usuario en español.
- Sin lógica de negocio en controladores; sin uso directo de sesiones de `SQLAlchemy` fuera de `repositories/`.
- Nada de `print`: logging estructurado (JSON) con `request_id`.
- Sin secretos, URLs privadas ni rutas absolutas en el código. Todo por `settings`.
- No usar APIs de LangChain/LangGraph que no estén verificadas en la versión fijada; ante la duda, citar la página de documentación a revisar.
- Dependencias con versión exacta (`uv.lock`).

## 4. Pruebas (pytest)

- Unitarias de servicios y del grafo con LLM y retriever *fake*.
- Pruebas de API con `TestClient`: 401 sin token, 403/404 en recursos ajenos, 413/415 en subida, 409 duplicado.
- Evaluación del RAG (`eval/`): ver `03_GRAFO_AGENTE.md`.
- CI (GitHub Actions): ruff + pytest en cada push.

## 5. Seguridad (lista de verificación)

- [ ] Ningún endpoint sin autenticar salvo `/health`.
- [ ] JWT validado con JWKS (firma, `iss`, `exp`, `aud/azp`).
- [ ] Datos filtrados por `owner_id` en **cada** consulta.
- [ ] Subidas: tamaño, extensión, tipo real; nombre de archivo saneado; nunca ejecutar contenido.
- [ ] CORS limitado al origen del frontend.
- [ ] Límite de peticiones por usuario en `/chat` y `/documents`.
- [ ] Secretos solo en `.env`; `.env`, corpus y `corpus_md/` en `.gitignore`.
- [ ] Contenedor de la API con usuario no root; imágenes con etiqueta fija.
- [ ] Keycloak y Ollama publicados solo en `127.0.0.1`.
- [ ] Swagger deshabilitado o protegido en el despliegue público.

## 6. Git

- Rama `main` estable; ramas `feat/…`, `fix/…`. Commits pequeños con **Conventional Commits** (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Un commit (o más) por fase como mínimo; nunca subir PDFs del corpus ni `.env`.

## 7. Definición de "hecho" por fase

Código ejecutándose en mi máquina · pruebas pasando · `.env.example` actualizado · `PROJECT_STATE.md` actualizado · commit hecho · puedo explicar cada archivo sin mirarlo.

## 8. Protocolo de trabajo con el asistente

1. Una fase por mensaje; archivos completos con su ruta.
2. Antes del código: 3 líneas con qué y por qué. Después: qué ejecutar y qué resultado esperar.
3. Al cerrar la fase: **3 preguntas de comprensión** al estudiante y `PROJECT_STATE.md` actualizado.
4. Dato dudoso (versión, licencia, límite): marcar `[VERIFICAR]` y decir dónde comprobarlo. Nunca inventar funciones, parámetros ni clases.
5. Si algo falla dos veces: no seguir parchando; pedir traceback, versiones y archivo, y razonar la causa raíz.
6. Si lo pedido contradice `01_REQUISITOS.md`, avisar antes de hacerlo.
