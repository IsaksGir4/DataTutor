# Guía definitiva — TutorDatos / DataTutor

## Recuperación del entorno local, errores corregidos y validaciones

**Versión:** 1.0**Fecha de corte:** 11 de octubre de 2026**Entorno:** Windows + PowerShell + Docker Desktop + PostgreSQL 16/pgvector + Keycloak + Ollama + Python/uv + LangGraph

> **Propósito.** Esta guía deja una ruta reproducible para volver a levantar TutorDatos después de apagar el PC, documenta los fallos que aparecieron y cómo se corrigieron, y separa los resultados verificados de los asuntos que todavía no están resueltos. Está basada en los comandos y salidas compartidos durante el diagnóstico; no presupone que el frontend ni el servidor HTTP ya estén validados.

## 0. Estado actual en una página

### Arquitectura local

```text
TutorDatos (Windows)
├── backend/ (Python 3.12.7 + uv + FastAPI / LangGraph)
│   ├── CLI validado: scripts/chat_cli.py
│   ├── Embeddings: Ollama bge-m3 (1024 dimensiones)
│   ├── Chat: Ollama qwen2.5:3b
│   └── Agente: receive → classify_intent → retrieve → grade_context
│       ├── contexto suficiente → generate_answer → save_history
│       ├── contexto insuficiente (primer intento) → rewrite_query → retrieve
│       └── saludo / fuera de dominio → smalltalk / refuse
├── Docker Desktop
│   ├── datatutor-postgres: PostgreSQL 16 + pgvector; DB datatutor; puerto 5432
│   └── datatutor-keycloak: Keycloak; puerto 8080
└── Ollama nativo de Windows, servidor local en puerto 11434
```

### Línea base validada

| Componente         | Estado comprobado                                                                                                                               |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Python del backend | `uv run python` utiliza Python 3.12.7, no el Python global 3.14 que se seleccionó inicialmente.                                              |
| PostgreSQL         | La aplicación pudo leer y actualizar los registros desde Windows mediante`SessionLocal`; el proceso de re-embedding terminó con `commit`. |
| Base vectorial     | 57 chunks: 41 del artículo de ciencia de datos y 16 del manual de ingeniería de datos.                                                        |
| Embeddings         | 1024 dimensiones; 0 valores nulos; 0 vectores de norma cero; coseno almacenado contra vector regenerado:`1.000000`.                           |
| Recuperación      | La pregunta inglesa recuperó primero el artículo con score`0.7172`; la española, con `0.6825`.                                           |
| CLI                | El flujo del grafo se ejecuta una vez por pregunta; se probaron pregunta respondible, pregunta sin apoyo suficiente y saludo.                   |
| Ollama             | La ejecución en CPU funcionó con`CUDA_VISIBLE_DEVICES=-1` y `OLLAMA_LLM_LIBRARY=cpu_avx2`.                                                |

**Importante:** “funciona localmente” no significa que todos los componentes estén terminados. La ruta de CLI está probada; el flujo completo frontend → autenticación → API HTTP no está validado por las evidencias recopiladas en esta sesión.

## 1. Carpeta del proyecto y comandos de trabajo

La ruta de trabajo utilizada fue:

```powershell
$root = "C:\Users\HP\Desktop\2026-2\Integracion e implementacion Soft\TutorDatos"
$backend = Join-Path $root "backend"
```

La mayoría de los comandos de Python deben ejecutarse desde `backend`:

```powershell
Set-Location $backend
uv run python --version
```

Resultado esperado: Python 3.12.7. El entorno virtual está en `backend\.venv`; no borres esta carpeta ni regeneres el entorno como primer recurso para resolver errores de dependencias.

## 2. Incidencias que aparecieron y su resolución

| Síntoma                                                                                                                   | Diagnóstico / causa establecida                                                                                                                                                                                                                                             | Resolución y prevención                                                                                                                                                                                                                                                                                                                                                                              |
| -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `uv` llegó a crear el proyecto con Python 3.14.                                                                         | La versión global detectada inicialmente no era la versión objetivo del backend.                                                                                                                                                                                           | Se reconstruyó la configuración del proyecto backend y se fijó Python 3.12.7 con`uv python pin 3.12.7`. La validación actual es `uv run python --version`.                                                                                                                                                                                                                                     |
| Docker fallaba al descargar la imagen por un problema de credenciales de Docker Hub.                                       | El acceso local guardado a Docker Hub interfería con el pull de la imagen pública.                                                                                                                                                                                         | `docker logout` permitió limpiar esas credenciales; después se pudo continuar con la descarga. Si vuelve a ocurrir, primero confirma que Docker Desktop esté iniciado y reintenta el pull desde la carpeta que contiene el Compose. No elimines volúmenes.                                                                                                                                       |
| El contenedor PostgreSQL no podía usar correctamente el puerto 5432 del host.                                             | El servicio nativo de Windows`postgresql-x64-17` había ocupado el puerto antes que el contenedor.                                                                                                                                                                         | Se detuvo el servicio y se configuró como deshabilitado al inicio de Windows. El puerto 5432 queda destinado al PostgreSQL del contenedor. Si necesitas volver a ejecutar la corrección, usa PowerShell como administrador y verifica primero el estado del servicio.                                                                                                                                |
| La contraseña funcionaba dentro del contenedor, pero los scripts de Windows habían presentado errores de autenticación. | Había una discrepancia entre el acceso al PostgreSQL esperado y los parámetros/servicio utilizados desde el host. Se detectó además la colisión con el PostgreSQL nativo.                                                                                               | Dentro del contenedor se ejecutó`ALTER USER postgres WITH PASSWORD 'postgres';`. Más adelante, el script de re-embedding ejecutado desde Windows leyó y confirmó actualizaciones de los 57 chunks mediante `SessionLocal`, lo que verifica que el backend volvió a conectarse a la base. Mantén sincronizados `.env` y `settings.py`; estas credenciales son solo para desarrollo local. |
| Ollama generaba un error de ejecución al pedir salida JSON estructurada mediante el backend GPU.                          | En este equipo, Ollama 0.40.0 falló durante inferencia acelerada (se observó el error`CUDA error: an illegal instruction was encountered`; los registros también mostraban el backend Vulkan). La causa interna exacta no quedó aislada.                               | El workaround probado fue detener Ollama Desktop/otro servidor, arrancar`ollama serve` con `CUDA_VISIBLE_DEVICES=-1` y `OLLAMA_LLM_LIBRARY=cpu_avx2`. `ollama ps` indicó CPU y la llamada JSON con LangChain respondió. Hay que establecer las variables cada vez que se vuelva a arrancar el servidor desde una nueva terminal.                                                             |
| Los resultados vectoriales parecían irrelevantes aunque el artículo pertinente ya estaba ingerido.                       | Para un texto almacenado, el coseno entre el embedding guardado y otro recién generado con el modelo actual era`-0.056097`, pese a que dos generaciones nuevas coincidían. La columna indicaba `bge-m3`, pero el vector persistido no concordaba con el modelo actual. | Se hizo un respaldo de PostgreSQL y se regeneraron en sitio los embeddings de los 57 chunks. Después, el coseno guardado vs. nuevo fue`1.000000` y la recuperación encontró el artículo correcto. La procedencia exacta de los vectores antiguos no se pudo demostrar; sí se comprobó que eran incompatibles con la generación actual.                                                        |
| Cada pregunta del CLI ejecutaba el grafo dos veces.                                                                        | `chat_cli.py` contenía dos bucles independientes sobre `agent_app.stream(state_input)`.                                                                                                                                                                                 | El CLI se reescribió para consumir un solo stream con`stream_mode="updates"` y acumular el estado final en esa única ejecución.                                                                                                                                                                                                                                                                   |
| Si el juez de contexto devolvía JSON inválido, el código podía dar por válido el contexto.                            | El bloque`except` de `grade_context()` devolvía `context_ok=True`, favoreciendo una respuesta incluso sin evaluación interpretable.                                                                                                                                  | Se cambió la recuperación ante`JSONDecodeError`/`TypeError` a `context_ok=False`, para que el flujo no acepte automáticamente un contexto por una respuesta mal formada del juez.                                                                                                                                                                                                             |

### Servicio PostgreSQL 17 de Windows: comprobación

```powershell
Get-Service -Name postgresql-x64-17 -ErrorAction SilentlyContinue
Get-CimInstance Win32_Service -Filter "Name='postgresql-x64-17'" |
    Select-Object Name, State, StartMode
```

El estado esperado para el servicio nativo, con la configuración que se dejó, es detenido/deshabilitado. Si el servicio no existe, no es un error por sí solo. Para detener/deshabilitarlo de nuevo, PowerShell debe ejecutarse como administrador:

```powershell
Stop-Service -Name postgresql-x64-17
Set-Service -Name postgresql-x64-17 -StartupType Disabled
```

No ejecutes estos dos últimos comandos sin confirmar primero que ese es el servicio que está ocupando el puerto y que el servicio nativo no es algo que necesites para otro proyecto.

## 3. Cómo volver a levantar TutorDatos después de apagar el PC

Sigue este orden cada vez. Usa una terminal separada para el servidor Ollama y otra para los comandos del backend.

### Paso A. Abrir Docker Desktop

1. Abre Docker Desktop y espera a que indique que el motor está en ejecución.
2. Abre PowerShell y ejecuta:

```powershell
docker info
docker ps -a --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"
```

Deben aparecer los contenedores `datatutor-postgres` y `datatutor-keycloak`. Si existen pero están detenidos, inicia esos mismos contenedores:

```powershell
docker start datatutor-postgres datatutor-keycloak
```

Si Docker dice que alguno no existe, **no lo elimines ni recrees a ciegas**. Comprueba el archivo Compose del proyecto con `Get-ChildItem $root -Force` y revisa la configuración antes de crear contenedores nuevos.

### Paso B. Verificar PostgreSQL y el puerto 5432

```powershell
docker exec datatutor-postgres pg_isready -U postgres -d datatutor
Test-NetConnection 127.0.0.1 -Port 5432
```

Esperado: `pg_isready` informa que acepta conexiones y `TcpTestSucceeded` es `True`. También puedes comprobar el puerto y los contenedores con:

```powershell
docker ps --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"
```

Si falla el puerto, verifica primero el servicio nativo de Windows descrito en la sección 2. No cambies el puerto de Docker ni recrees la base para solucionar una colisión local sin comprobarla.

### Paso C. Iniciar Ollama con la configuración estable probada

Ollama debe estar escuchando en `http://127.0.0.1:11434`. La configuración estable que funcionó en este equipo fue CPU-only, porque la ruta GPU produjo fallos al solicitar JSON.

1. Cierra Ollama Desktop por completo, incluido su icono de la bandeja del sistema, para que no ocupe el puerto ni arranque otro servidor.
2. En una nueva terminal PowerShell, comprueba si queda algún proceso escuchando:

```powershell
Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, OwningProcess
```

Si aparece un `OwningProcess`, identifica ese PID antes de detenerlo:

```powershell
Get-Process -Id <PID>
```

Sustituye `<PID>` por el número real. Detén el proceso solo si confirmas que pertenece al servidor de Ollama que quieres cerrar. No uses un PID antiguo: cambia entre sesiones.

```PowerShell
Stop-Process -Id <PID>
```

3. En esa misma terminal, establece las variables y arranca el servidor:

```powershell
$env:CUDA_VISIBLE_DEVICES = "-1"
$env:OLLAMA_LLM_LIBRARY = "cpu_avx2"
ollama serve
```

**Deja abierta esta terminal.** `ollama serve` mantiene el servidor en primer plano. Si dice que el puerto ya está en uso, otro servidor sigue activo; no abras varias instancias en paralelo.

4. En otra terminal, comprueba que los modelos estén instalados:

```powershell
ollama list
```

Deben estar disponibles `qwen2.5:3b` y `bge-m3`. Si ya están descargados, no es necesario volver a descargarlos.

### Paso D. Validar el entorno desde el backend

Abre una segunda terminal PowerShell:

```powershell
$root = "C:\Users\HP\Desktop\2026-2\Integracion e implementacion Soft\TutorDatos"
Set-Location (Join-Path $root "backend")
uv run python --version
```

Confirma Python 3.12.7. Si el proyecto conserva el script de diagnóstico, ejecútalo:

```powershell
uv run python .\scripts\verificar_entorno.py
```

Este script se utilizó para comprobar PostgreSQL, el endpoint JWKS de Keycloak y Ollama/modelos. Si indica un error, usa el detalle de su salida para aislar el servicio; no reinstales todo como primer intento.

### Paso E. Arrancar y probar el CLI

Desde `backend`, ejecuta:

```powershell
uv run python .\scripts\chat_cli.py
```

Prueba, en este orden:

1. `Hola` — debe mostrar la ruta `generate_smalltalk` y terminar con `decision=smalltalk`.
2. `¿Cuáles son las siete formas en que puede fracasar un proyecto de ciencia de datos?` — debe recuperar el artículo y generar una respuesta.
3. `¿Qué es una base de datos?` — con el corpus actual puede acabar en aclaración o rechazo, porque los documentos cargados no ofrecen soporte directo suficiente para esa definición. No tomes una respuesta sin evidencia como válida solo porque el agente la generó.

Escribe `salir` para terminar el CLI.

**Importante:** `scripts/chat_cli.py` es el punto de entrada que se probó de extremo a extremo. Esta guía no inventa un comando de Uvicorn ni uno de Vite: el comando correcto para el servidor HTTP y el frontend debe confirmarse en los archivos de entrada reales cuando se retome esa parte del desarrollo.

## 4. Apagar el entorno sin perder el trabajo

- En el CLI, escribe `salir`.
- En la terminal donde corre `ollama serve`, usa `Ctrl+C` si deseas detener el servidor antes de apagar Windows.
- Puedes dejar los contenedores en ejecución hasta que Windows se apague, o detenerlos explícitamente:

```powershell
docker stop datatutor-keycloak datatutor-postgres
```

- Luego apaga Windows normalmente.

Los datos de PostgreSQL persisten en el volumen Docker `datatutor-pgdata`; el contenedor puede detenerse sin borrar el volumen. **Nunca ejecutes `docker compose down -v` ni `docker volume rm datatutor-pgdata` como rutina de apagado.** La opción `-v` elimina volúmenes y puede borrar la base local.

## 5. PostgreSQL, credenciales y respaldo

### Configuración de desarrollo que debe coincidir

| Parámetro                       | Valor usado en este entorno   |
| -------------------------------- | ----------------------------- |
| Contenedor                       | `datatutor-postgres`        |
| Base                             | `datatutor`                 |
| Usuario                          | `postgres`                  |
| Contraseña local de desarrollo  | `postgres`                  |
| Host desde Windows               | `127.0.0.1` / `localhost` |
| Puerto publicado                 | `5432`                      |
| PostgreSQL dentro del contenedor | 16.x con pgvector             |
| Volumen de datos                 | `datatutor-pgdata`          |

Estos valores son propios del entorno de desarrollo, no una configuración segura para un sistema desplegado. Asegúrate de que las variables que lee `settings.py` y el `.env` local coincidan. No publiques ni compartas un `.env` que contenga secretos reales.

### Si reaparece el error de contraseña

Primero confirma que te conectas al contenedor correcto y no al servicio nativo:

```powershell
docker exec -it datatutor-postgres psql -U postgres -d datatutor
```

Dentro de `psql`, el comando que se utilizó fue:

```sql
ALTER USER postgres WITH PASSWORD 'postgres';
\q
```

Haz esto solo si el error es realmente de autenticación y el usuario/contraseña de la aplicación deben ser esos. No cambies credenciales al azar: la contraseña en PostgreSQL debe coincidir con la configuración leída por el backend.

### Crear un nuevo respaldo antes de cambios de base de datos

El respaldo previo a regenerar embeddings se guardó en:

`backend\datatutor_pre_reembedding.dump`

La copia desde el contenedor indicó `Successfully copied 298kB`. Conserva ese archivo; es anterior a la regeneración de embeddings y permite preservar el estado previo de la base.

Para crear respaldos adicionales desde PowerShell, ubicado en `backend`:

```powershell
$backup = "datatutor_$(Get-Date -Format yyyyMMdd_HHmmss).dump"
docker exec datatutor-postgres pg_dump -U postgres -d datatutor -Fc -f "/tmp/$backup"
docker cp "datatutor-postgres:/tmp/$backup" ".\$backup"
Get-Item ".\$backup" | Select-Object Name, Length, LastWriteTime
```

No sobrescribas el respaldo histórico `datatutor_pre_reembedding.dump`. Haz una copia del archivo en otro disco o ubicación fuera del PC si necesitas protección frente a una falla física.

**Restauración:** un `pg_dump -Fc` se puede restaurar con `pg_restore`, pero no lo restaures encima de la base activa por ensayo y error. Si necesitas practicar, crea una base nueva y restaura allí; primero verifica que haya suficiente espacio y que el nombre de la base de prueba no exista:

```powershell
# Solo práctica de restauración; no reemplaza la base activa.
docker exec datatutor-postgres createdb -U postgres datatutor_restore_test
docker cp .\datatutor_pre_reembedding.dump datatutor-postgres:/tmp/datatutor_pre_reembedding.dump
docker exec datatutor-postgres pg_restore -U postgres -d datatutor_restore_test --no-owner --no-privileges /tmp/datatutor_pre_reembedding.dump
```

Este ejemplo crea otra base llamada `datatutor_restore_test`. No uses ese nombre si ya existe. Revisa los mensajes de `pg_restore` y valida el contenido antes de considerar una recuperación real.

## 6. Embeddings: qué se corrigió exactamente

### El síntoma reproducible

La búsqueda inicial no encontraba el artículo de forma adecuada. La causa práctica quedó expuesta al comparar un texto almacenado con el embedding que generaba el modelo actual:

- Dos generaciones nuevas del mismo texto eran deterministas.
- El embedding almacenado y uno nuevo para ese mismo texto tenían coseno `-0.056097`.
- Ambos vectores tenían 1024 dimensiones.

Esto demostró que el vector guardado era inconsistente con el modelo que la aplicación estaba usando en ese momento. No se pudo demostrar con certeza si los vectores antiguos provenían de otra configuración, una ejecución problemática del backend GPU u otra causa previa; no debe afirmarse una causa interna que no fue verificada.

### Respaldo hecho antes de tocar los vectores

```powershell
docker exec datatutor-postgres pg_dump -U postgres -d datatutor -Fc -f /tmp/datatutor_pre_reembedding.dump
docker cp datatutor-postgres:/tmp/datatutor_pre_reembedding.dump .\datatutor_pre_reembedding.dump
```

### Regeneración que sí se ejecutó

Se seleccionaron los 57 registros `Chunk`, se generaron embeddings en lotes de 16 mediante el modelo configurado por `get_embeddings_model()` y se actualizaron únicamente:

- `Chunk.embedding`
- `Chunk.embed_model` (a `settings.EMBED_MODEL`, configurado como `bge-m3`)

La transacción hizo un único `commit` al terminar. No se borraron y recrearon los documentos ni los chunks; se conservaron el texto, las páginas, los índices, los IDs y las relaciones.

> **Precisión terminológica:** no se hizo *rechunking* en esta reparación. Se hizo una **regeneración de embeddings / re-embedding**. El chunking original se configura con `CHUNK_SIZE=1000` y `CHUNK_OVERLAP=200`; además, `process_pdf()` extrae el texto por página y aplica el splitter dentro de cada página. No se cambiaron los límites de los chunks en esta operación.

### Validaciones obtenidas después

| Prueba                                          | Resultado comprobado                                |
| ----------------------------------------------- | --------------------------------------------------- |
| Cantidad procesada                              | 57/57                                               |
| Embeddings nulos                                | 0                                                   |
| Vectores de norma cero                          | 0                                                   |
| Dimensión almacenada / nueva                   | 1024 / 1024                                         |
| Coseno almacenado vs. nuevo para el mismo texto | `1.000000`                                        |
| Consulta inglesa                                | Artículo correcto en primer lugar, score`0.7172` |
| Consulta española                              | Artículo correcto en primer lugar, score`0.6825` |

La recuperación semántica volvió a traer fragmentos del artículo con el título «Seven ways to fail», incluidos los siete modos enumerados. No fue necesario borrar la base ni reingerir los PDFs.

## 7. Agentes: flujo y cambios realizados

### Flujo actual

```text
START
  → receive
  → classify_intent
      ├── smalltalk → generate_smalltalk → save_history → END
      ├── out_of_domain → refuse → save_history → END
      └── explain / exercise / fallback → retrieve → grade_context
          ├── suficiente → generate_answer → save_history → END
          └── insuficiente
              ├── retries < 1 → rewrite_query → retrieve → grade_context
              ├── falló y score >= 0.45 → clarify → save_history → END
              └── falló y score < 0.45 → refuse → save_history → END
```

Valores actuales observados en `nodes/core.py`:

- `SIM_THRESHOLD = 0.65`: a partir de aquí se llama al juez LLM de suficiencia.
- `SIM_LOW = 0.50`: por debajo, el contexto se marca insuficiente sin llamar al juez.
- Entre 0.50 y 0.65, el contexto se marca insuficiente.
- La búsqueda devuelve `top_k=4` fragmentos.
- El grafo permite un reintento de consulta (`retries < 1`).
- Después del reintento, la ruta usa el score `0.45` para decidir entre aclarar y rechazar.

### Corrección del CLI

El CLI antiguo llamaba dos veces a `agent_app.stream(state_input)`: una para imprimir nodos y otra para recopilar la respuesta. La versión corregida usa un único stream:

```python
final_state = {}
for event in agent_app.stream(state_input, stream_mode="updates"):
    for node, node_state in event.items():
        print(f"  [>] Nodo ejecutado: {node}")
        if isinstance(node_state, dict):
            final_state.update(node_state)
```

Así se evita repetir clasificación, embeddings, búsqueda, llamadas al LLM y cualquier otro efecto del grafo por la misma pregunta.

### Corrección de fallback del juez LLM

En `grade_context()`, un JSON inválido no debe equivaler a un contexto suficiente. El fallback aplicado fue:

```python
except (json.JSONDecodeError, TypeError):
    return {"context_ok": False}
```

Esta es una regla conservadora: si no se puede interpretar la evaluación, el flujo vuelve a la rama de contexto insuficiente en vez de autorizar una respuesta por defecto.

## 8. Pruebas funcionales observadas

### A. Pregunta cubierta por el artículo

Pregunta:

`¿Cuáles son las siete formas en que puede fracasar un proyecto de ciencia de datos?`

Nodos observados:

`receive → classify_intent → retrieve → grade_context → generate_answer → save_history`

La consulta obtuvo respuesta y las cuatro fuentes correspondieron al artículo, con scores `0.683`, `0.653`, `0.628` y `0.608` aproximadamente. Es una validación de la ruta de recuperación y generación. Sin embargo, la salida incluía «Realismos inaceptables», traducción poco fiel de *unrealistic expectations*. La fidelidad terminológica y las citas dentro del texto siguen requiriendo una prueba y ajuste de prompt; listar las fuentes al final no demuestra por sí solo que cada afirmación esté correctamente citada.

### B. Pregunta sin soporte documental suficiente

Pregunta:

`¿Qué es una base de datos?`

Nodos observados:

`receive → classify_intent → retrieve → grade_context → rewrite_query → retrieve → grade_context → clarify → save_history`

El agente no inventó una definición, pero terminó pidiendo aclaración. La pregunta original es comprensible; el problema está en que el grafo usa el score posterior al reintento para decidir `clarify` frente a `refuse`, sin medir directamente la ambigüedad lingüística. Este comportamiento **todavía no se corrigió**. El siguiente desarrollo debería separar “pregunta ambigua” de “pregunta clara sin evidencia suficiente”.

### C. Saludo

Pregunta: `Hola`

Nodos observados:

`receive → classify_intent → generate_smalltalk → save_history`

El saludo funcionó sin recuperación vectorial.

## 9. Qué no hacer y cómo evitar perder el entorno

- No ejecutes `docker compose down -v` ni `docker volume rm datatutor-pgdata` para “reiniciar” un servicio.
- No borres `backend\.venv` ni recrees el proyecto uv por una advertencia de un import sin diagnosticar primero.
- No ejecutes dos servidores Ollama escuchando en el puerto 11434. Si está ocupado, identifica el PID y comprueba qué proceso es antes de detenerlo.
- No vuelvas a ejecutar una ingesta masiva solo para reparar vectores si los textos y chunks son correctos. El re-embedding en sitio fue suficiente para este incidente.
- No bajes los umbrales de similitud solo para forzar una respuesta. Primero comprueba que el embedding y el contexto recuperado sean correctos.
- No interpretes `embed_model='bge-m3'` como prueba de que un vector fue realmente generado con ese modelo; valida el vector contra una generación fresca cuando haya sospecha de inconsistencia.
- No guardes credenciales reales en el repositorio ni compartas el archivo `.env`.

## 10. Pendientes conocidos para continuar el desarrollo

1. **Ruta de aclaración/rechazo:** la pregunta clara pero no documentada sobre bases de datos acaba en `clarify`; separar ambigüedad real de falta de evidencia.
2. **Fidelidad de respuesta:** mejorar la traducción de términos técnicos y exigir mayor correspondencia con el contexto fuente.
3. **Citas:** comprobar que las afirmaciones de la respuesta incluyan las referencias `[1]`, `[2]` exigidas por `ANSWER_PROMPT`, y que correspondan a fuentes reales.
4. **Pruebas automatizadas:** crear pruebas para intención, scores límites, JSON inválido del juez, reintento y decisión terminal.
5. **Persistencia de conversación:** `save_history()` sigue siendo un paso dummy en la Fase 2; no implica que el historial esté persistido en PostgreSQL.
6. **Frontend/API HTTP:** solo se documenta aquí el CLI validado. Confirmar y probar los entrypoints reales de FastAPI y React/Vite cuando se retome esa etapa.
7. **Ollama GPU:** CPU es el workaround validado; no se ha solucionado de manera definitiva la ruta GPU/Vulkan. No quites las variables de CPU hasta probarlo explícitamente.

## 11. Lista rápida al iniciar una sesión de desarrollo

- [ ] Docker Desktop abierto y motor listo.
- [ ] `datatutor-postgres` y `datatutor-keycloak` en ejecución.
- [ ] `pg_isready` pasa para la base `datatutor` y el puerto 5432 responde.
- [ ] El PostgreSQL nativo `postgresql-x64-17` no ha vuelto a ocupar el puerto.
- [ ] Ollama sirve en el puerto 11434 con las variables CPU-only en la terminal del servidor.
- [ ] `ollama list` muestra `qwen2.5:3b` y `bge-m3`.
- [ ] `uv run python --version` indica Python 3.12.7 desde `backend`.
- [ ] `uv run python .\scripts\chat_cli.py` responde a `Hola`.
- [ ] Antes de cambiar esquema, ingesta o vectores, se creó un respaldo nuevo.

---

**Criterio para esta guía:** los valores, comandos, salidas y problemas señalados como comprobados provienen de las validaciones compartidas. Las causas internas que no pudimos aislar, los arreglos futuros y los componentes que todavía no se probaron se identifican expresamente como hipótesis o pendientes, en vez de presentarse como hechos resueltos.
