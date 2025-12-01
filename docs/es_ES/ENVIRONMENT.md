````markdown
# Visión General

El sistema pmllm utiliza variables de entorno para toda la configuración. Copie `.env.example` a `.env` y modifíquelo según sea necesario:

```bash
cp .env.example .env
# Edite .env con sus valores específicos
```

## Categorías de Variables

### Configuración de Conexión Neo4j

| Variable               | Predeterminado          | Descripción                                                                                                                                              |
| ---------------------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `NEO4J_URI`            | `bolt://localhost:7687` | URI de conexión Neo4j. Use `bolt://` para conexiones seguras o `neo4j://` para clustering                                                                |
| `NEO4J_USER`           | `neo4j`                 | Nombre de usuario de la base de datos Neo4j                                                                                                              |
| `NEO4J_PASSWORD`       | `your_password_here`    | Contraseña de la base de datos Neo4j. Requerida para autenticación                                                                                       |
| `NEO4J_DATABASE`       | `pmllmdb`               | Nombre de la base de datos Neo4j utilizada por este proyecto                                                                                             |
| `NEO4J_ALLOW_INSECURE` | `false`                 | Permitir conexiones con contraseña predeterminada. Solo para desarrollo/pruebas                                                                          |
| `NEO4J_DATA_DIR`       | -                       | Ruta al directorio de datos de Neo4j para importaciones masivas locales. Si se establece NEO4J_BIN_PATH, esto puede dejarse vacío. Ejemplo: ~/.Neo4jDesktop2/Data/dbmss/dbms-\*/data |
| `NEO4J_BIN_PATH`       | -                       | Ruta al directorio bin de Neo4j para la herramienta de importación masiva. Ejemplo: ~/.Neo4jDesktop2/Data/dbmss/dbms-\*/bin                                                       |

### Configuración de Base de Datos Vectorial Milvus

| Variable      | Predeterminado | Descripción                                |
| ------------- | -------------- | ------------------------------------------ |
| `MILVUS_HOST` | `127.0.0.1`    | Nombre de host o dirección IP del servidor Milvus |
| `MILVUS_PORT` | `19530`        | Número de puerto del servidor Milvus       |

### Almacenamiento de Objetos MinIO

| Variable           | Predeterminado | Descripción                         |
| ------------------ | -------------- | ----------------------------------- |
| `MINIO_ACCESS_KEY` | `minioadmin`   | Clave de acceso MinIO para autenticación |
| `MINIO_SECRET_KEY` | `minioadmin`   | Clave secreta MinIO para autenticación |

**Advertencia de Seguridad:** ¡Cambie las credenciales de MinIO para uso en producción!

### Almacén de Chats y Preferencias

| Variable           | Predeterminado              | Descripción                                                                                   |
| ------------------ | --------------------------- | --------------------------------------------------------------------------------------------- |
| `CHAT_DB_URL`      | _(vacío)_                   | URL compatible con SQLAlchemy para almacenar chats/preferencias (SQLite, Postgres, etc.).     |
| `CHAT_DB_PATH`     | `./storage/local_app.db`    | Ruta de archivos para SQLite cuando `CHAT_DB_URL` no está definido.                           |
| `CHAT_SERVICE_URL` | `http://localhost:8080`     | URL base del servicio FastAPI de recomendaciones (usada por frontend u otros clientes).       |

### Pasarela de Modelos y API

| Variable                        | Predeterminado                              | Descripción                                                                                   |
| ------------------------------- | ------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `MODEL_GATEWAY_EMBEDDING_MODEL` | `text-embedding-embeddinggemma-300m-qat`    | Variante de Gemma cargada por el gateway para `/v1/embeddings`.                               |
| `MODEL_GATEWAY_LLM_MODEL`       | `gemma-3-1b-it-qat`                         | Variante conversacional servida en `/v1/chat/completions`.                                    |
| `MODEL_GATEWAY_DEVICE`          | `cpu`                                       | Dispositivo usado dentro del contenedor (`cpu`, `cuda`, etc.).                                |
| `MODEL_GATEWAY_DTYPE`           | `float32`                                   | Tipo de dato Torch usado al cargar Gemma dentro del gateway.                                  |
| `EMBEDDING_API_URL`             | `http://localhost:9000/v1/embeddings`       | URL (vista desde el host) para solicitar embeddings al gateway.                               |
| `EMBEDDING_MODEL`               | `text-embedding-embeddinggemma-300m-qat`    | Nombre del modelo enviado en los payloads de la API.                                          |
| `EMBEDDING_API_TIMEOUT`         | `60`                                        | Tiempo de espera (segundos) para peticiones de embeddings.                                    |
| `LLM_API_URL`                   | `http://localhost:9000/v1/chat/completions` | URL (vista desde el host) para solicitudes de chat.                                           |
| `LLM_MODEL`                     | `gemma-3-1b-it-qat`                         | Nombre del modelo de chat usado en los payloads.                                              |
| `LLM_MAX_NEW_TOKENS`            | `512`                                       | Máximo de tokens nuevos para generación.                                                     |
| `LLM_TEMPERATURE`               | `0.7`                                       | Temperatura de muestreo predeterminada.                                                       |
| `LLM_API_TIMEOUT`               | `120`                                       | Tiempo de espera (segundos) para completions.                                                 |
| `MODEL_API_KEY`                 | _(vacío)_                                   | Token opcional de autenticación si se securiza el gateway.                                    |

> **Recordatorio de contenedores:** Los modelos Gemma (embeddings y chat) viven ahora dentro del contenedor `pmllm-model-gateway`. Mantén este servicio activo durante las construcciones y consultas. Si llamas desde otro contenedor en la misma red Docker, usa `http://pmllm-model-gateway:9000/...` en las variables `_API_URL`.

## Configuración del Proceso de Construcción

### Directorios de Entrada/Salida

| Variable          | Predeterminado             | Descripción                                                                                      |
| ----------------- | -------------------------- | ------------------------------------------------------------------------------------------------ |
| `OUTPUT_DIR`      | `output`                   | Directorio base de salida. Crea automáticamente subdirectorios `core/` y `derived/`              |
| `TSV_CORE_DIR`    | `music_metadata`           | Directorio que contiene volcados TSV/TAR principales de MusicBrainz (artistas, grabaciones, lanzamientos, etc.) |
| `TSV_DERIVED_DIR` | `music_derived_metadata`   | Directorio que contiene volcados TSV/TAR derivados de MusicBrainz (sellos, lugares, eventos, etc.) |
| `CSV_CORE_DIR`    | `output/converted/core`    | Directorio de trabajo donde se almacenan los archivos CSV principales convertidos antes de la preparación (creado automáticamente) |
| `CSV_DERIVED_DIR` | `output/converted/derived` | Directorio de trabajo donde se almacenan los archivos CSV derivados convertidos antes de la preparación (creado automáticamente) |

### Opciones de Muestreo

| Variable                     | Predeterminado | Descripción                                                                       |
| ---------------------------- | -------------- | --------------------------------------------------------------------------------- |
| `SAMPLE_PERCENT`             | `100.0`        | Porcentaje de datos a procesar (0.0-100.0). Use valores más bajos para pruebas    |
| `SAMPLE_SEED`                | `123`          | Semilla aleatoria para muestreo reproducible. Asegura resultados consistentes     |
| `DEMO_MODE`                  | `true`         | Habilitar modo demo (anula configuraciones de muestreo para pruebas rápidas)      |
| `DEMO_SAMPLE_PERCENT`        | `0.1`          | Porcentaje de muestreo aplicado al ejecutar `build --demo`                        |
| `DEMO_VECTOR_SAMPLE_PERCENT` | `0.1`          | Porcentaje de muestreo aplicado a la etapa de construcción vectorial al ejecutar `build --demo` |

### Opciones de Procesamiento de Archivos

| Variable             | Predeterminado | Descripción                                        |
| -------------------- | -------------- | -------------------------------------------------- |
| `DELIMITER`          | `\t`           | Delimitador de campo en archivos TSV de entrada (carácter tabulador). Debe ser un solo carácter; use tabulador real en .env si es necesario |
| `ENCODING`           | `utf-8`        | Codificación de caracteres de archivos de entrada  |
| `SKIP_HEADERS`       | `false`        | Omitir generación de archivos de encabezado Neo4j  |
| `SKIP_LABELS`        | `false`        | Omitir procesamiento de datos de nodos etiquetados |
| `SKIP_RELATIONSHIPS` | `false`        | Omitir procesamiento de datos de relaciones        |

## Opciones de Procesamiento de Datos Derivados

El pipeline soporta el procesamiento de datos "derivados" adicionales de MusicBrainz para crear un grafo de conocimiento más rico. Estas opciones controlan qué tipos de entidades y relaciones adicionales incluir.

### Entidades Derivadas Principales

| Variable              | Predeterminado | Descripción                                                                              |
| --------------------- | -------------- | ---------------------------------------------------------------------------------------- |
| `PROCESS_LABELS`      | `true`         | Sellos discográficos (Sony, Universal, etc.). Agrega contexto de industria y relaciones comerciales |
| `PROCESS_MEDIUMS`     | `true`         | Tipos de medios físicos (CD, Vinilo, Digital). Describe formatos de lanzamiento y portadores |
| `PROCESS_TRACKS`      | `true`         | Pistas individuales dentro de lanzamientos. Proporciona información detallada a nivel de pista |
| `PROCESS_PLACES`      | `true`         | Ubicaciones de grabación, lugares. Agrega contexto geográfico y de actuación             |
| `PROCESS_EVENTS`      | `true`         | Conciertos, festivales, eventos. Vincula artistas a sus actuaciones y giras              |
| `PROCESS_GENRES`      | `true`         | Géneros musicales. Habilita consultas y recomendaciones basadas en género                |
| `PROCESS_INSTRUMENTS` | `true`         | Instrumentos musicales. Muestra especializaciones de artistas y detalles de actuación    |
| `PROCESS_SERIES`      | `true`         | Series de Álbum/Artista. Agrupa lanzamientos relacionados y conecta colecciones          |
| `PROCESS_URLS`        | `true`         | Enlaces externos (Wikipedia, sitios oficiales). Proporciona recursos y referencias adicionales |

### Enriquecimiento de Metadatos

| Variable             | Predeterminado | Descripción                                                                    |
| -------------------- | -------------- | ------------------------------------------------------------------------------ |
| `PROCESS_ALIASES`    | `true`         | Nombres alternativos para entidades. Mejora la búsqueda y maneja variaciones de nombres |
| `PROCESS_TYPES`      | `true`         | Clasificaciones de tipo de entidad. Agrega información de tipo para mejor categorización |
| `PROCESS_ATTRIBUTES` | `true`         | Propiedades y características adicionales. Enriquece metadatos de entidad      |
| `PROCESS_CREDITS`    | `true`         | Créditos y contribuciones de artistas. Muestra atribución y roles detallados   |
| `PROCESS_LANGUAGES`  | `true`         | Idiomas de obra, países de lanzamiento. Agrega localización e información regional |
| `PROCESS_PACKAGING`  | `true`         | Tipos de empaque de lanzamiento. Describe formatos de lanzamiento físico       |
| `PROCESS_STATUSES`   | `true`         | Estados de lanzamiento (Oficial, Bootleg). Indica calidad y legitimidad del contenido |

### Relaciones Extendidas

| Variable                               | Predeterminado | Descripción                                                                        |
| -------------------------------------- | -------------- | ---------------------------------------------------------------------------------- |
| `PROCESS_EXTENDED_RELATIONSHIPS`       | `true`         | Procesar archivos de relación l\_\* adicionales. Agrega conexiones complejas entre entidades |
| `RELATIONSHIPS_TO_SKIP`                | -              | Lista separada por comas de relaciones a excluir. Útil para ajuste de rendimiento  |
| `QUIET_MISSING_EXTENDED_RELATIONSHIPS` | `false`        | Suprimir advertencias cuando faltan tablas l\_\* opcionales en los volcados proporcionados |

**Ejemplo:** `RELATIONSHIPS_TO_SKIP=l_artist_event,l_genre_genre,l_url_work`

### Opciones Avanzadas

| Variable            | Predeterminado | Descripción                                                                               |
| ------------------- | -------------- | ----------------------------------------------------------------------------------------- |
| `PROCESS_REDIRECTS` | `false`        | Redirecciones GID para limpieza de datos. Usado para mantenimiento de base de datos y deduplicación |
| `PROCESS_ISNI_IPI`  | `false`        | Identificadores profesionales ISNI/IPI. Para integración industrial y verificación profesional |
| `PROCESS_ISRC_ISWC` | `false`        | Códigos de grabación/obra ISRC/ISWC. Para gestión de derechos e identificación de contenido |
| `PROCESS_CDTOC`     | `false`        | Tabla de Contenidos de CD. Para identificación de CD y coincidencia de audio              |

## Construcción Vectorial y Pruebas

| Variable                      | Predeterminado | Descripción                                                                            |
| ----------------------------- | -------------- | -------------------------------------------------------------------------------------- |
| `VECTOR_BUILD_WORKERS`        | `4`            | Número de trabajadores para construcción vectorial                                     |
| `VECTOR_BUILD_SAMPLE_PERCENT` | `1.0`          | Porcentaje de datos a usar al construir la base de datos vectorial                     |
| `TEST_MODE`                   | `true`         | Habilitar modo de prueba (usa `TEST_SAMPLE_PERCENT` en lugar del conjunto completo)    |
| `TEST_SAMPLE_PERCENT`         | `1.0`          | Porcentaje de muestreo para modo de prueba                                             |
| `VECTOR_LABELS`               | _(lista)_      | Lista separada por comas de etiquetas Neo4j para incrustar (predeterminados cubren Artist, Recording, etc.) |

## Solución de Problemas y Validación

Después de la configuración, puede ejecutar una pequeña construcción de validación usando:

```bash
uv run python main.py build --config .env
uv run python main.py build-vector
```

Use `SAMPLE_PERCENT` más bajo o habilite `TEST_MODE` para iteración más rápida durante el desarrollo.
````