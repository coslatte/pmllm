# Registro de Cambios

Este archivo documenta todos los cambios realizados en el proyecto, especialmente aquellos implementados por agentes.

> Nota: El proyecto estandariza el uso de modelos Gemma servidos desde contenedores locales mediante el
> `pmllm-model-gateway` (API `/v1` compatible con OpenAI). Las menciones históricas a "LM Studio" o
> "Qwen 3" están obsoletas; la configuración activa utiliza modelos containerizados (Gemma) que exponen
> endpoints para embeddings y generación. Revise `EMBEDDING_API_URL`, `LLM_API_URL`, `EMBEDDING_MODEL` y
> `LLM_MODEL` en `.env` para controlar el gateway.

## 2025-12-04

- **Correcciones en contenedores**: Se actualizó `docker-compose.yml` para montar `./data/postgres` en `/var/lib/postgresql`, acorde con Postgres 18+, evitando el ciclo de reinicio del health-check. Antes de recrear la carpeta limpia se resguardó el contenido previo dentro de `data/postgres_legacy_*`.
- **Alineación de endpoints del gateway**: Se ajustaron `EMBEDDING_API_URL`/`EMBEDDING_URL` a `http://127.0.0.1:8081/v1/embeddings` y `LLM_API_URL` a `http://127.0.0.1:8082/v1/chat/completions` dentro de `.env`, de modo que el CLI y el pipeline RAG consuman los contenedores Gemma del `docker compose` en lugar del puerto heredado 1234 de LM Studio.
- **Normalización de delimitadores**: Se añadió el helper `_normalize_delimiter` en `main.py` y se conectó con los comandos `build-data`, `prepare-neo4j`, `prepare-desktop`, `import-neo4j` y el flujo de perfiles, de modo que valores como `\t` en `.env` se transforman en un tab real. Con ello se evita el error de Python "delimiter must be a 1-character string" y todas las fases usan exactamente el mismo separador.
- **Actualización del dataset Neo4j**: Se regeneraron los CSV con el delimitador corregido y se volvió a ejecutar la importación masiva, obteniendo ~515 k nodos muestreados y 2.4 k relaciones en el corte del 1 % más reciente.
- **Muestreo en capas para pruebas**: `db/vector/build_vector_db.py` ahora respeta `TEST_SAMPLE_PERCENT`, de modo que con `TEST_MODE=true` podemos tomar un porcentaje del subconjunto ya reducido (p. ej., 10 % del 1 %). El `.env` queda con `SAMPLE_PERCENT=1` y `TEST_SAMPLE_PERCENT=10` para mantener livianos los flujos demo/test.
- **Puente de consultas para el frontend**: Se creó `server/query_engine.py` y se añadió el endpoint `POST /query` en FastAPI para que el frontend envíe preguntas libres, se ejecute el pipeline RAG y (si se pasa `chat_id`) se almacenen los mensajes. El motor detecta intenciones de tags/géneros como “tags de todos los artistas que son Jesus”, ejecuta Cypher contra Neo4j para listar artistas coincidentes y devuelve tanto la respuesta del LLM como los resultados estructurados listos para la UI. La nueva interfaz está documentada en `docs/API_DOCUMENTATION.md` y `docs/es_ES/API_DOCUMENTATION.md`.
- **Depuración visible y apagado limpio**: Se añadió el flag opcional `debug` a `/query` (y al CLI) para exponer el prompt completo, los fragmentos de contexto, los hits de Milvus y las relaciones Neo4j utilizadas en cada respuesta. Se introdujo el `ContextBundle` para telemetría, se extendieron las respuestas y el CLI imprime dichos detalles. Además, se registró un `atexit` y se simplificaron las consultas Cypher para eliminar advertencias sobre `title` y cerrar Bolt sin excepciones al terminar scripts.

## 2025-12-03

- **Perfiles del comando build**: Se añadió un enum `BuildProfile` con perfiles seleccionables mediante `--profile/-p` (o un menú interactivo que por defecto usa `full` en entornos no interactivos). Ahora existen flujos dedicados para demo, solo importación Neo4j, solo embeddings y solo conversión, y `_execute_full_build` omite pasos según el plan, valida directorios cuando se reutilizan artefactos y mejora los avisos previos.
- **Actualizaciones de documentación**: `docs/CLI_USAGE.md` y `docs/es_ES/CLI_USAGE.md` describen la nueva bandera y resumen cada perfil disponible.
- **Límite mínimo de muestreo demo**: Se actualizaron las variables de `.env` para que los modos demo/prueba mantengan al menos el 1 % de las filas, evitando importaciones diminutas en Neo4j y Milvus.
- **Guardia previa a la importación**: `main.py` ahora valida que los CSV etiquetados tengan datos antes de ejecutar el neo4j-admin bulk import, deteniendo la ejecución si el muestreo no produjo nodos.
- **Rutas en los logs de conversión**: Se acortó la salida de `utils/files_manager/converter.py` para que los mensajes de conversión TSV→CSV muestren únicamente los últimos directorios (con prefijo `...\`) en lugar de las rutas absolutas completas.

## 2025-12-02

- **Constructor de datos en una llamada**: Se añadió `utils/data_builder.py` junto con el comando Typer `build-data` para convertir dumps TAR/TSV, generar los conjuntos CSV y ejecutar la preparación para Neo4j en un solo paso. `main.py` expone el comando y se agregaron pruebas en `tests/test_data_builder.py`.
- **Salvaguardas del prompt de recomendaciones**: Se extendieron `docs/RECOMMENDATION_SYSTEM.md` y su versión en español con criterios de calidad que cubren personalización, umbrales de confianza, cobertura mínima y manejo de ambigüedad.
- **Documentación de CLI**: `docs/CLI_USAGE.md` y `docs/es_ES/CLI_USAGE.md` ahora incluyen el flujo `build-data`, ejemplos rápidos, tablas de opciones y correcciones de lint.
- **Arranque de stack desde CLI**: Se añadió el subcomando `start` a `main.py` para ejecutar `docker compose up -d`, verificar Neo4j/Milvus/gateway y lanzar el servidor FastAPI con opciones `--skip-compose`, `--no-server`, `--host/--port` y `--reload`. Las guías de CLI en EN/ES se actualizaron con instrucciones de uso y resolución de problemas.
- **Contenedor de Postgres y gateway de modelos**: Se incorporó el servicio `pmllm-user-db` (PostgreSQL 15) más variables de entorno para que el servidor FastAPI persista usuarios/chats vía SQLAlchemy por defecto. Se creó el proyecto `model_gateway` (FastAPI + Transformers) que expone `/v1/embeddings` y `/v1/chat/completions`, se añadieron healthchecks/volúmenes en `docker-compose.yml`, se actualizaron `.env.example`, README y `docs/ENVIRONMENT.md` (EN/ES), y se agregó `psycopg2-binary` a las dependencias de Python.

## 2025-12-01

- **Gateway de Modelos y Stack de Contenedores**: Se agregó el servicio FastAPI `model_gateway` (embeddings + chat completions) con su Dockerfile, requirements y orquestación en `docker-compose.yml`, además del contenedor `pmllm-recommender-api` respaldado por una ruta SQLite configurable. Se actualizaron `.env`, `.env.example`, docker-compose, helpers del CLI, pruebas y toda la documentación (README, ENVIRONMENT, CLI_USAGE, DISTRIBUCION_DATOS, planes, instrucciones de Copilot en EN/ES) para describir la topología de tres contenedores (Milvus, gateway de modelos, base de chats) y los valores predeterminados de Gemma.
- **Integración de LLM Local**: Se implementó la interacción directa con modelos LLM usando la biblioteca Transformers en lugar de la API de LM Studio. Se agregó `db/vector/helper/llm_handler.py` para cargar y generar con modelos locales. Se actualizó `rag_pipeline.py` para usar el LLM local. Se agregaron nuevas variables de entorno: `USE_LOCAL_LLM`, `LLM_MODEL_NAME`, `LLM_DEVICE`, `LLM_MAX_NEW_TOKENS`, `LLM_TEMPERATURE`. Se actualizaron las dependencias en `pyproject.toml` para incluir `transformers`, `torch`, `accelerate`.
- **CLI de paquete Neo4j Desktop**: Se agregó el comando `prepare-desktop` en `main.py`, junto con `utils/helpers/desktop_bundle_handler.py`, para fusionar encabezados y datos en CSV listos para Neo4j Desktop (nodos y relaciones) dentro de `output/neo4j_desktop`, facilitando importaciones con solo arrastrar y soltar.
- **Documentación de Distribución de Datos**: Se agregó `docs/DISTRIBUCION_DATOS.md` documentando la arquitectura de datos para la base de datos de chats, preferencias de usuario y sistema de recomendaciones, incluyendo el esquema SQLite, flujo de datos y patrones de distribución.

## 2025-11-29

- **Especificación de Recomendaciones**: Se agregó `docs/RECOMMENDATION_SYSTEM.md` con el prompt base, el esquema JSON y el flujo para planes de álbumes que combinan Neo4j (cerebro lógico) con Milvus (cerebro intuitivo) y Gemma 3. El documento describe los insumos requeridos, el manejo de fallos y cómo entregar de 5 a 10 recomendaciones explicables.

## 2025-11-26

- **Simplificación de Colores CLI**: Se eliminó `utils/constants/cli_colors.py` y se actualizó `main.py` para usar `typer.colors` directamente, evitando una capa innecesaria en la experiencia de línea de comandos.
- **Reestructuración del comando Build**: `build` ahora ejecuta toda la cadena (conversión TAR/TSV → preparación CSV → importación Neo4j → construcción vectorial) e incorpora la nueva bandera `--demo` que ajusta automáticamente los parámetros de muestreo. Se agregaron reutilización guiada de conversiones, recordatorios sobre el uso del gateway de modelos (contenedores locales) para embeddings, la deprecación de `demo-build`, y las variables `CSV_CORE_DIR`, `CSV_DERIVED_DIR`, `VECTOR_LABELS` y `DEMO_VECTOR_SAMPLE_PERCENT` con la documentación pertinente (`README.md`, `CLI_USAGE.md`, `ENVIRONMENT.md`, `.env.example`).
- **Eliminación de `demo-build`**: Se retiró el comando heredado `demo-build` para que la ayuda solo muestre subcomandos soportados. Toda la documentación ahora indica `build --demo` para los escenarios rápidos.
- **Robustez en embeddings**: Ahora se espera a que Bolt esté disponible antes del Paso 4, se cargan automáticamente las colecciones de Milvus, se actualizó la búsqueda y TEST_MODE procesa el 100% del subconjunto ya muestreado en lugar de volver a reducirlo al 1%.
- **Confiabilidad en la etapa vectorial**: Se agregó un aviso para reiniciar Neo4j antes del Paso 4, se cargan automáticamente las colecciones de Milvus y `vector_query.py` ahora envía los parámetros obligatorios del nuevo SDK, evitando errores cuando Neo4j o Milvus todavía se están inicializando.
- **Escalado automático de workers**: El asistente de `build-vector` ahora propone usar el 75% de los núcleos disponibles, configurable con `VECTOR_BUILD_WORKER_PERCENT` y `VECTOR_BUILD_MAX_CORES`. Se actualizó `.env.example` y `docs/ENVIRONMENT.md` para reflejarlo.

## 2025-11-24

- **Optimización de Memoria en Preparación de Datos**: Corrigió el agotamiento de memoria durante la preparación de CSV al prevenir la acumulación de IDs de nodos retenidos cuando sample_fraction >= 0.9999 (conjunto de datos completo). Modificó `utils/files_manager/csv_helper.py` para crear condicionalmente sets de kept_ids solo durante el muestreo.
- **Corrección del Pipeline RAG**: Corrigió la recuperación de contexto gráfico en `db/vector/rag_pipeline.py` cambiando `n.id IN $ids` a `elementId(n) IN $ids` en la consulta Cypher, asegurando la coincidencia adecuada de IDs de elementos de Neo4j desde Milvus.
- **Refactorización de Configuración de Modelos**: Renombró `QWEN_GENERATE_MODEL` a `LLM_MODEL` en `.env` y código para mayor claridad. Aseguró que todos los modelos sean configurables vía variables de entorno sin valores predeterminados hardcodeados.
- **Estandarización de Modelos**: Confirmó el uso de `google/gemma-3-1b` para LLM y `text-embedding-embeddinggemma-300m-qat` para embeddings, alineado con el plan del proyecto.

## 2025-11-22

- **Actualización de Estrategia de Modelos**: Cambió el modelo de embedding de texto a 'text-embedding-embeddinggemma-300m-qat' (Gemma Embedding 300M, Q4_0) y actualizó el LLM a 'google/gemma-3-1b' (Gemma 3 1B, Q4_0). Estos pesos se administran como artefactos locales servidos por el `pmllm-model-gateway` (contenedores locales) y no dependen de servicios externos como LM Studio. Actualizó `plan/PLAN.md` para documentar los nuevos modelos y sus especificaciones.
- **Mejora de Documentación**: Creó `docs/CHANGELOG_es.md` como una versión en español del registro de cambios, reflejando todas las entradas en español. Actualizó `plan/PLAN.md` para incluir documentación en ambos idiomas cuando sea apropiado y agregó `docs/CHANGELOG_es.md` a los deliverables.
- **Actualización de Configuración de Entorno**: Actualizó `.env` y `docs/ENVIRONMENT.md` para reflejar los nuevos modelos Gemma: se establecieron `LLM_MODEL` a 'google/gemma-3-1b' y `EMBEDDING_MODEL` a 'text-embedding-embeddinggemma-300m-qat', y se documentó el uso del `pmllm-model-gateway` para exponer `EMBEDDING_API_URL` y `LLM_API_URL` hacia el resto del sistema.

## 2025-11-21

- **Actualizaciones de Documentación**: Agregó instrucciones para el acceso a la base de datos en Neo4j Browser después de la importación. Corrigió referencias de archivos CLI de `cli.py` a `main.py`. Eliminó contenido duplicado en `CLI_USAGE.md`. Actualizó los deliverables en `PLAN.md` para reflejar los archivos reales del proyecto.
- **Verificación de Metadatos Completa**: Validación integral de todos los 7 tipos de nodos y 9 tipos de relaciones en el pipeline MusicBrainz-to-Neo4j. Todos los encabezados, mapeos de columnas y conexiones de datos verificados para su corrección.
- **Arquitectura de Grafo Validada**: Confirmó 100% de consistencia entre los encabezados de Neo4j y las funciones de preparación de CSV. Todas las relaciones conectan correctamente entidades musicales lógicas (Artist→Recording, Recording→Work, etc.).
- **Integridad de Esquema**: Validó mapeos de columnas contra el esquema TSV de MusicBrainz. Todos los 7 tipos de nodos y 9 tipos de relaciones tienen recuentos de campos y tipos de datos correctos.
- **Expansión de Relaciones**: Agregó relaciones integrales incluyendo etiquetas de género (3 conexiones), áreas geográficas (2 conexiones) y jerarquías de obras. Excluyó puntos de datos excesivamente específicos según lo solicitado.
- **Mejora de Importación Neo4j**: Actualizó `neo4j_importer.py` para incluir todos los nuevos tipos de relaciones (nodos ReleaseGroup, Tag + 6 archivos de relaciones adicionales) en el comando de importación masiva.
- **Garantía de Calidad de Datos**: Verificó compatibilidad de muestreo, integridad referencial y exclusión de puntos de datos excesivamente específicos. Grafo optimizado para casos de uso de recomendación musical.
- **Verificación de Metadatos Completa**: Validación integral de todos los 7 tipos de nodos y 9 tipos de relaciones en el pipeline MusicBrainz-to-Neo4j. Todos los encabezados, mapeos de columnas y conexiones de datos verificados para su corrección.
- **Arquitectura de Grafo Validada**: Confirmó 100% de consistencia entre los encabezados de Neo4j y las funciones de preparación de CSV. Todas las relaciones conectan correctamente entidades musicales lógicas (Artist→Recording, Recording→Work, etc.).
- **Integridad de Esquema**: Validó mapeos de columnas contra el esquema TSV de MusicBrainz. Todos los 7 tipos de nodos y 9 tipos de relaciones tienen recuentos de campos y tipos de datos correctos.
- **Expansión de Relaciones**: Agregó relaciones integrales incluyendo etiquetas de género (3 conexiones), áreas geográficas (2 conexiones) y jerarquías de obras. Excluyó puntos de datos excesivamente específicos según lo solicitado.
- **Mejora de Importación Neo4j**: Actualizó `neo4j_importer.py` para incluir todos los nuevos tipos de relaciones (nodos ReleaseGroup, Tag + 6 archivos de relaciones adicionales) en el comando de importación masiva.
- **Garantía de Calidad de Datos**: Verificó compatibilidad de muestreo, integridad referencial y exclusión de puntos de datos excesivamente específicos. Grafo optimizado para casos de uso de recomendación musical.

- **Cambio de Proyecto (aclaración)**: Las notas históricas que mencionan un cambio a Qwen 3 están supersedidas. El proyecto utiliza modelos Gemma servidos localmente a través del `pmllm-model-gateway` (contenedor) para embeddings y generación. La documentación y los scripts se han ajustado para depender de las APIs del gateway en lugar de servicios externos.
- **Base de Datos Vectorial**: Seleccionó Milvus como la base de datos vectorial de producción para embeddings y recuperación.
- **Fuente de Datos**: Agregó soporte para conjunto de datos fragmentado de MusicBrainz (de exportaciones PostgreSQL + Neo4j) como fuente primaria de datos para documentos y relaciones KG.
- **Desarrollo CLI**: Creó `cli.py` con una clase CLI para extraer archivos tar, verificar formatos TSV y convertir a CSV. Maneja directorios con archivos tar y TSV mixtos.
- **Expansión de Utilidades**: Extendió `utils/reader.py` (ahora `utils/files_manager/reader.py`) con funciones para detección de delimitadores, validación tabular, conversión CSV y extracción tar.
- **Documentación**: Creó directorio `docs/` para registros de cambios y documentación adicional.
- **Soporte para Campos Grandes**: Actualizó `utils/reader.py` para levantar el límite de tamaño de campo CSV para que los archivos de anotaciones de MusicBrainz se conviertan sin errores.

## 2025-11-19

- **Modularización CLI**: Refactorizó `cli.py` para delegar la conversión TSV-a-CSV a `utils/files_manager/converter.py` y agregar subcomandos (`convert`, `prepare-neo4j`, `import-neo4j`).
- **CLI de Preparación MusicBrainz**: Extendió `utils/files_manager/csv_helper.py` y el subcomando `prepare-neo4j` para parametrizar directorios de fuente MusicBrainz, encabezado, etiqueta y relación vía banderas CLI.
- **Ayudante de Importación Neo4j**: Agregó `db/neo4j/neo4j_importer.py` para envolver `neo4j-admin database import full` y consultas de verificación `cypher-shell`.
- **CLI de Importación Neo4j**: Agregó subcomando `import-neo4j` a `cli.py` para ejecutar importación masiva usando encabezados/etiquetas/relaciones generados, con banderas para directorios, nombre de base de datos y consultas de verificación opcionales.
- **Actualizaciones de Documentación**: Actualizó `README.md` y `plan/PLAN.md` para reflejar las nuevas capacidades CLI y renombró `docs/CHANGES.md` a `docs/CHANGELOG.md`.
- **Nota sobre generadores legacy**: Cualquier referencia anterior a pipelines basados en Qwen se considera histórica/experimental; la configuración activa usa Gemma y el gateway de modelos en contenedores.

## 2025-11-20

- **Preparación CSV Amigable con Muestreo**: `utils/files_manager/csv_helper.py` ahora soporta muestreo determinístico de filas con banderas CLI `--sample-percent` y `--sample-seed`, recortando tanto nodos como relaciones consistentemente para importaciones parciales de Neo4j.
- **Modo de Importación Neo4j Heredado**: Agregó `--legacy-import` a `cli.py import-neo4j`, más detección robusta de directorio de datos (derivada de bin-path, anulaciones env, rutas Docker) dentro de `db/neo4j/neo4j_importer.py` para que los flujos de trabajo más antiguos de `neo4j-admin import` sigan siendo soportados.
- **Seguridad de Tipos y Herramientas**: Introdujo un `mypy.ini` a nivel de proyecto, resolvió brechas de anotación en `db/neo4j/neo4j_handler.py`, `utils/files_manager/reader.py`, auxiliares de embedding y pipeline RAG. `uvx mypy` ahora pasa con bases de paquetes explícitas y supresión de importaciones faltantes para SDKs de terceros.
- **Mejoras de Fiabilidad RAG**: Endureció `db/vector/rag_pipeline.py` y `db/vector/helper/embedder.py` con validación de respuesta estructurada, tiempos de espera de solicitud y embeddings basados en listas explícitas para evitar discrepancias de forma en tiempo de ejecución.
- **Alineación de Plan**: Actualizó `plan/PLAN.md` para marcar Etapa 2.1 (importación KG Neo4j) como en progreso y registrar las nuevas capacidades de muestreo/importación heredada requeridas para la aceptación de Etapa 2.
