# Registro de Cambios

Este archivo documenta todos los cambios realizados en el proyecto, especialmente aquellos implementados por agentes.

## 2025-11-26

- **Simplificación de Colores CLI**: Se eliminó `utils/constants/cli_colors.py` y se actualizó `main.py` para usar `typer.colors` directamente, evitando una capa innecesaria en la experiencia de línea de comandos.
- **Reestructuración del comando Build**: `build` ahora ejecuta toda la cadena (conversión TAR/TSV → preparación CSV → importación Neo4j → construcción vectorial) e incorpora la nueva bandera `--demo` que ajusta automáticamente los parámetros de muestreo. Se agregaron reutilización guiada de conversiones, recordatorios sobre el modelo de embeddings en LM Studio, la deprecación de `demo-build`, y las variables `CSV_CORE_DIR`, `CSV_DERIVED_DIR`, `VECTOR_LABELS` y `DEMO_VECTOR_SAMPLE_PERCENT` con la documentación pertinente (`README.md`, `CLI_USAGE.md`, `ENVIRONMENT.md`, `.env.example`).
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

- **Actualización de Estrategia de Modelos**: Cambió el modelo de embedding de texto a 'text-embedding-embeddinggemma-300m-qat' (Gemma Embedding 300M, Q4_0, 229.09 MB de lmstudio-community). Actualizó el LLM a 'google/gemma-3-1b' (Gemma 3 1B, Q4_0, 720.50 MB). Este cambio refleja nuevas estrategias de LLM para mejorar el rendimiento en el pipeline RAG. Actualizó `plan/PLAN.md` para documentar los nuevos modelos y sus especificaciones.
- **Mejora de Documentación**: Creó `docs/CHANGELOG_es.md` como una versión en español del registro de cambios, reflejando todas las entradas en español. Actualizó `plan/PLAN.md` para incluir documentación en ambos idiomas cuando sea apropiado y agregó `docs/CHANGELOG_es.md` a los deliverables.
- **Actualización de Configuración de Entorno**: Actualizó `.env` y `docs/ENVIRONMENT.md` para reflejar los nuevos modelos Gemma: configuró `QWEN_GENERATE_MODEL` a 'google/gemma-3-1b' y `EMBEDDING_MODEL_PATH` a 'text-embedding-embeddinggemma-300m-qat'.

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

- **Cambio de Proyecto**: Cambió de ajuste fino de modelos a Generación Aumentada por Recuperación (RAG) usando Qwen 3 como generador de LLM. Actualizó `README.md`, `plan/PLAN.md` y `plan/original_plan.md` para reflejar este cambio.
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
- **Generador Qwen**: Actualizó el pipeline RAG para llamar `qwen/qwen3-1.7b` para generación y `text-embedding-qwen3-embedding-0.6b` para embeddings, incluyendo módulos auxiliares y documentación.

## 2025-11-20

- **Preparación CSV Amigable con Muestreo**: `utils/files_manager/csv_helper.py` ahora soporta muestreo determinístico de filas con banderas CLI `--sample-percent` y `--sample-seed`, recortando tanto nodos como relaciones consistentemente para importaciones parciales de Neo4j.
- **Modo de Importación Neo4j Heredado**: Agregó `--legacy-import` a `cli.py import-neo4j`, más detección robusta de directorio de datos (derivada de bin-path, anulaciones env, rutas Docker) dentro de `db/neo4j/neo4j_importer.py` para que los flujos de trabajo más antiguos de `neo4j-admin import` sigan siendo soportados.
- **Seguridad de Tipos y Herramientas**: Introdujo un `mypy.ini` a nivel de proyecto, resolvió brechas de anotación en `db/neo4j/neo4j_handler.py`, `utils/files_manager/reader.py`, auxiliares de embedding y pipeline RAG. `uvx mypy` ahora pasa con bases de paquetes explícitas y supresión de importaciones faltantes para SDKs de terceros.
- **Mejoras de Fiabilidad RAG**: Endureció `db/vector/rag_pipeline.py` y `db/vector/helper/embedder.py` con validación de respuesta estructurada, tiempos de espera de solicitud y embeddings basados en listas explícitas para evitar discrepancias de forma en tiempo de ejecución.
- **Alineación de Plan**: Actualizó `plan/PLAN.md` para marcar Etapa 2.1 (importación KG Neo4j) como en progreso y registrar las nuevas capacidades de muestreo/importación heredada requeridas para la aceptación de Etapa 2.
 
 
 
 
 
 