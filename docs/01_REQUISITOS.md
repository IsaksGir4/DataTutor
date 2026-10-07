# REQUISITOS — Trabajo Agente (resumen fiel del enunciado)

> Fuente de verdad: `trabajo_agente.pdf`. Si este resumen contradice el PDF, manda el PDF.
> Entrega: **18 de octubre de 2026**. Modalidad: individual o parejas.

## 1. Qué hay que construir
Aplicación web completa cuyo núcleo es un **agente inteligente con LangChain + LangGraph** que responde preguntas sobre un dominio a partir de una **base de conocimiento propia en una base vectorial** (arquitectura RAG). Cada respuesta debe sustentarse en información **recuperada**, no en el conocimiento paramétrico del modelo.

Componentes obligatorios: backend con API protegida · frontend funcional · autenticación · agente LangChain+LangGraph · modelo de lenguaje **local** (Ollama o Hugging Face) · base vectorial · carga de archivos · despliegue en la nube (backend y frontend con URL pública).

## 2. Requisitos funcionales
**Autenticación:** registro/login; frontend solo para autenticados; API solo con autorización; sesión activa; logout. Keycloak recomendado. **Ningún endpoint expuesto sin autenticación.**

**Backend (REST o GraphQL):** autenticar/validar usuarios · enviar preguntas al agente · subir archivos · procesar documentos y guardar embeddings · historial de conversaciones del usuario · listar y eliminar documentos. Código con separación clara: controladores, servicios, configuración, lógica del agente, acceso a datos.

**Frontend:** registro/login · chat con el agente · enviar preguntas y ver respuestas · subir archivos · consultar documentos cargados · **mostrar errores cuando el agente no pueda responder** · logout.

**Carga de documentos (flujo):** recibir archivo → extraer contenido → dividir en fragmentos → generar embeddings → almacenar en la base vectorial → confirmar al usuario. Formatos sugeridos: PDF, TXT, MD, CSV, DOCX, multimedia (JPG, MP4, MP3).

## 3. Requisitos técnicos
**Grafo del agente (referencia):** recibir pregunta → validar intención → buscar en la base vectorial → evaluar si lo recuperado es suficiente → responder con base en lo encontrado → rechazar o pedir aclaración si es insuficiente → guardar en historial.
Si no hay información suficiente, responder explícitamente: **"No tengo suficiente información en mi base de conocimiento para responder esa pregunta."** (puede sugerir cargar documentos).

**Modelo local:** obligatorio; no depender solo de modelos comerciales en la nube. En el documento técnico: qué modelo, por qué, cómo se ejecuta localmente, limitaciones.

**Base vectorial:** debe guardar fragmentos, asociarlos a su documento original, buscar por la pregunta y recuperar el contexto. (Elegida: **PostgreSQL + pgvector**, que figura en la lista del enunciado.)

**Control de alucinaciones (criterio clave): al menos 2 estrategias** de: umbral de similitud · verificación del contexto antes de responder · prompt que obligue a usar solo lo recuperado · nodo LangGraph que valide suficiencia · rechazo explícito · mostrar fuentes/fragmentos. (Nuestro objetivo: implementar 5.)

**Despliegue:** frontend (Vercel, Netlify, GitHub Pages, Azure Static Web Apps, Firebase) y backend (Render, Railway, Azure, AWS, GCP Cloud Run, Fly.io, DigitalOcean) con URL pública. Documentar URLs, variables de entorno, proceso y problemas.

## 4. Restricción
Prohibido construir el flujo del agente con herramientas visuales / drag & drop (n8n, Zapier, Make, Flowise, Botpress visual…). Debe ser **código** con LangChain y LangGraph.

## 5. Entregables
| Entregable | Contenido | Formato |
|---|---|---|
| Repositorio GitHub | Código, configuración, README, diagramas | Enlace público |
| Documento técnico | 14 apartados (abajo) | PDF |
| Sustentación | Demo en vivo de 7 a 10 min | Presencial |
| Diapositivas | 8 a 12 láminas | PDF |

**Repositorio:** commits significativos y frecuentes; backend + frontend; configuración del agente; README completo (ejecución local y despliegue); archivo `.env.example`; capturas y diagrama de arquitectura.

**Documento técnico (14 apartados):** 1 Nombre e integrantes · 2 Tema y problema · 3 Arquitectura y diagrama · 4 Tecnologías · 5 Backend · 6 Frontend · 7 Agente y flujo LangGraph · 8 Modelo local y base vectorial · 9 Carga de documentos · 10 Estrategias anti-alucinación · 11 Seguridad y autenticación · 12 Despliegue · 13 Evidencias · 14 Problemas y conclusiones.

**Sustentación (checklist de la demo):** tema y arquitectura · login y frontend · preguntas bien respondidas · **preguntas rechazadas por falta de información** · **carga de un documento nuevo y pregunta que dependa de él** · revisión rápida del código y explicación del grafo · evidencia del despliegue.

**Diapositivas (secuencia):** 1 Nombre/integrantes · 2 Problema · 3 Arquitectura · 4 Tecnologías · 5 Agente LangChain+LangGraph · 6 Base vectorial y carga · 7 Seguridad y usuarios · 8 Demostración · 9 Conclusiones.

## 6. Evaluación
**Mínimos para aprobar (todos obligatorios):** backend y frontend funcionales · autenticación · agente con LangChain+LangGraph · modelo local funcionando · base vectorial + carga de documentos operativa · respuestas ancladas al contexto · rechazo explícito sin información suficiente · despliegue en la nube + repositorio documentado.

| Criterio | Peso | Evidencia |
|---|---|---|
| Arquitectura general | 10% | Documento técnico |
| Backend y API | 15% | Repositorio |
| Frontend e interfaz | 5% | Demostración |
| Autenticación y seguridad | 10% | Demostración |
| Uso correcto de LangChain y LangGraph | 15% | Repositorio |
| Modelo local | 8% | Documento técnico |
| Base vectorial y RAG | 10% | Repositorio |
| Carga y procesamiento de documentos | 7% | Demostración |
| Control de alucinaciones | 10% | Demostración |
| Despliegue en la nube | 2% | URL pública |
| Documentación y sustentación | 8% | Documento y diapositivas |

**Calidad esperada:** código limpio y separado (front/back/agente) · variables de entorno · manejo de errores y validación de formularios · seguridad en endpoints · README claro y commits frecuentes · interfaz usable y respuestas coherentes · evidencia clara de LangGraph y despliegue funcional.

## 7. Estructura de repo sugerida (Anexo A)
`backend/{app,agents,services,controllers,vectorstore,requirements.txt,Dockerfile,README.md}` · `frontend/{src,public,package.json,Dockerfile,README.md}` · `docs/{arquitectura.png,documento-tecnico.pdf,presentacion.pdf}` · `docker-compose.yml` · `.env.example` · `README.md`.

## 8. Pregunta abierta para el profesor (solo antes de la Fase 7)
Si el backend se expone con un túnel desde el portátil, ¿se acepta como "despliegue en la nube"? (El frontend en Vercel o Netlify sí lo está.)
