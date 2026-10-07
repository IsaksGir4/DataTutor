# GRAFO DEL AGENTE (LangGraph)

Construido en código con `StateGraph`. **No** usar un agente ReAct genérico: el enunciado exige nodos explícitos de validación, evaluación de suficiencia y rechazo.

## 1. Estado (`AgentState`, TypedDict o Pydantic)

| Campo               | Tipo                                                           | Uso                                                |
| ------------------- | -------------------------------------------------------------- | -------------------------------------------------- |
| `question`        | str                                                            | Pregunta original                                  |
| `owner_id`        | str                                                            | `sub` del JWT; filtra la recuperación           |
| `conversation_id` | str                                                            | Hilo                                               |
| `history`         | list[msg]                                                      | Últimos N turnos (N=6)                            |
| `intent`          | `explain` / `exercise` / `smalltalk` / `out_of_domain` | Resultado del nodo de intención                   |
| `query`           | str                                                            | Consulta usada para recuperar (puede reescribirse) |
| `retrieved`       | list[Chunk]                                                    | Fragmentos con`text, document, page, score`      |
| `best_score`      | float                                                          | Mejor puntaje de similitud                         |
| `context_ok`      | bool                                                           | Veredicto de suficiencia                           |
| `retries`         | int                                                            | Reescrituras realizadas (máx. 1)                  |
| `answer`          | str                                                            | Respuesta final                                    |
| `sources`         | list[Source]                                                   | `document, page, snippet, score`                 |
| `decision`        | `answered` / `rejected` / `clarify` / `smalltalk`      | Para la API y el frontend                          |

## 2. Nodos

1. **`receive`**: normaliza la pregunta, recorta historial, valida longitud.
2. **`classify_intent`**: salida estructurada `{intent, language}`. Reglas baratas primero (saludos, preguntas de una palabra); LLM solo si hace falta. Un falso "fuera de dominio" es peor que dejar pasar: **ante la duda, recuperar**.
3. **`retrieve`**: embebe `query` y ejecuta una búsqueda de similitud con `pgvector` mediante SQLAlchemy con filtro `owner_id ∈ {global, sub}`; devuelve top-K (`TOP_K=4`) calculando el score como `1 - distancia_coseno`.
4. **`grade_context`** (*nodo anti-alucinación*): (a) umbral determinista `best_score >= SIM_THRESHOLD`; (b) juez LLM con salida estructurada `{sufficient: bool, reason}` sobre pregunta + fragmentos. `context_ok = (a) and (b)`. Si el modelo pequeño falla al estructurar, degradar a solo (a).
5. **`rewrite_query`**: si el puntaje está en zona gris (entre `SIM_LOW` y `SIM_THRESHOLD`) y `retries < 1`, reescribe la consulta (p. ej. traducir ES↔EN o expandir términos) y vuelve a `retrieve`.
6. **`generate_answer`**: prompt restrictivo (ver §4); cita con `[n]`.
7. **`refuse`**: devuelve el mensaje exacto de rechazo + sugerencia de cargar documentos.
8. **`clarify`**: pide precisar cuando la pregunta es vaga y hay contexto parcial.
9. **`save_history`**: persiste mensaje del usuario y respuesta con `decision`, `sources`, `best_score`, `latency_ms`.

## 3. Aristas

```
START → receive → classify_intent
classify_intent --smalltalk--> generate_smalltalk → save_history → END
classify_intent --(explain|exercise|out_of_domain)--> retrieve → grade_context
grade_context --context_ok--> generate_answer → save_history → END
grade_context --zona gris y retries<1--> rewrite_query → retrieve
grade_context --vaga con contexto parcial--> clarify → save_history → END
grade_context --else--> refuse → save_history → END
```

Todos los caminos terminan en `save_history`. Sin ciclos sin tope (máx. 1 reescritura).

## 4. Prompt de generación (reglas, no texto literal)

- Responde **solo** con el CONTEXTO numerado. No uses conocimiento externo.
- Si el contexto no alcanza: responde exactamente "No tengo suficiente información en mi base de conocimiento para responder esa pregunta."
- Cita con `[n]` las afirmaciones. No inventes citas.
- Responde en el **idioma de la pregunta**; si el contexto está en otro idioma, tradúcelo fielmente.
- Intención `exercise`: propón un ejercicio **basado únicamente en el material recuperado** (enunciado + pista + solución solo si aparece en el contexto).
- Temperatura 0. `num_ctx=4096`. `num_predict=512`.

## 5. Estrategias anti-alucinación implementadas (meta: 5 de 6)

1. Umbral mínimo de similitud (`SIM_THRESHOLD`) calibrado con el conjunto de evaluación.
2. Nodo `grade_context` dedicado a validar suficiencia.
3. Prompt que obliga a responder solo con lo recuperado.
4. Rechazo explícito con mensaje fijo.
5. Fuentes y fragmentos visibles en cada respuesta.
6. (Opcional, `VERIFY_ANSWER=false` por costo en CPU) verificación posterior de que cada afirmación está respaldada.

## 6. Conjunto de evaluación (`eval/questions.jsonl`)

30–40 preguntas: ~50% respondibles (con documento y página esperados), ~25% fuera de dominio, ~25% plausibles pero ausentes del corpus (p. ej. Kafka, Spark). Métricas: % respondidas bien, % rechazos correctos, % falsos rechazos, latencia p50/p95. El script de evaluación barre `SIM_THRESHOLD` y compara `bge-m3` vs `nomic-embed-text`.

## 7. Pruebas del grafo

Unitarias con LLM y retriever *fake* (inyección de dependencias): ruta de respuesta, ruta de rechazo, ruta de reescritura, ruta de aclaración, y que `save_history` siempre se ejecute.
