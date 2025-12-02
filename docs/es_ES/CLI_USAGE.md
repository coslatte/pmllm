# Guía de Uso de CLI para Preparación de Datos MusicBrainz

Esta guía proporciona instrucciones completas para usar la herramienta CLI `pmllm` para preparar datos de MusicBrainz para la importación a Neo4j y realizar el proceso de construcción completo.

## Tabla de Contenidos

- [Resumen](#resumen)
- [Instalación](#instalación)
- [Inicio Rápido](#inicio-rápido)
- [Referencia de Comandos](#referencia-de-comandos)
- [Proceso de Construcción Completo](#proceso-de-construcción-completo)
- [Ejemplos de Uso](#ejemplos-de-uso)

## Resumen

La herramienta CLI `pmllm` proporciona un pipeline completo para transformar archivos TSV crudos de MusicBrainz en un formato compatible con Neo4j. Soporta:

- **Conversión TSV a CSV**: Extraer y convertir archivos de volcado de MusicBrainz
- **Preparación de Datos**: Generar cabeceras, etiquetas y relaciones para Neo4j
- **Importación Neo4j**: Importación masiva de datos preparados a la base de datos Neo4j
- **Proceso de Construcción Completo**: Pipeline automatizado de extremo a extremo con archivos de configuración
- **7 Tipos de Nodos**: Artist, Recording, Release, Work, Area, ReleaseGroup, Tag
- **9 Tipos de Relaciones**: Artist-Recording, Artist-Release, Recording-Work, etc.
- **Muestreo Inteligente**: Mantiene la integridad referencial durante la reducción de datos
- **Validación de Grafos**: Comprobaciones de integridad post-procesamiento
- **Múltiples Modos**: Configuraciones de Prueba (50%) y Producción (100%)

## Instalación

Asegúrate de tener Python 3.10+ y las dependencias requeridas:

```bash
# Instalar dependencias
pip install -r requirements.txt

# O usando el proyecto
pip install -e .
```

## Inicio Rápido

### Construcción Demo (Dataset Mínimo)

```bash
# Copiar y configurar el archivo de entorno
cp .env.example .env
# Editar .env con tus rutas y configuraciones

# Ejecutar el pipeline completo de demostración (0.1% de muestreo por defecto)
uv run python main.py build --demo
```

`build --demo` ahora cubre conversión → preparación → importación Neo4j → construcción de vectores usando el endpoint de embeddings del gateway de modelos.

### Construcción Automatizada Completa

```bash
# Copiar y configurar el archivo de entorno
cp .env.example .env
# Editar .env con tus rutas y configuraciones

# Ejecutar el pipeline completo
uv run python main.py build
```

### Iniciar el Stack + Servidor API

Levanta los servicios dockerizados (Milvus, MinIO, gateway de modelos) y arranca el servidor FastAPI en un solo paso:

```bash
uv run python main.py start
```

Utiliza `--skip-compose` si los contenedores ya están ejecutándose o `--no-server` cuando solo necesitas las comprobaciones de salud.

### Solo Construcción de Datos (Conversión + Preparación)

```bash
uv run python main.py build-data \
  --core-dir music_metadata \
  --derived-dir music_derived_metadata \
  --output-dir output
```

`build-data` convierte los dumps TAR/TSV (core + derived) a CSV y ejecuta inmediatamente la preparación para Neo4j (cabeceras, datos etiquetados y relaciones) sin tocar la importación o la construcción vectorial. Usa `--reuse-converted/--no-reuse-converted` para decidir si se reutilizan los CSV ya existentes.

### Pasos Individuales

```bash
# Convertir archivos TSV a formato CSV
uv run python main.py convert music_metadata --out output/converted/core
uv run python main.py convert music_derived_metadata --out output/converted/derived

# Preparar datos para Neo4j
uv run python main.py prepare-neo4j \
  --core-dir output/converted/core \
  --derived-dir output/converted/derived \
  --output-dir output \
  --sample-percent 50.0

# (Opcional) construir paquete para Neo4j Desktop
uv run python main.py prepare-desktop --output-dir output --bundle-dir output/neo4j_desktop

# Importar a Neo4j
uv run python main.py import-neo4j --output-dir output --verify

# Construir base de datos vectorial
uv run python main.py build-vector

# Consultar el sistema
uv run python main.py query "¿Qué artistas son similares a Queen?"
```

## Referencia de Comandos

### Comandos Principales

| Comando           | Descripción                                                                                   |
| ----------------- | --------------------------------------------------------------------------------------------- |
| `build`           | Pipeline completo (convertir → preparar → importar → construir vector). Soporta `--demo`      |
| `build-data`      | Convierte dumps TAR/TSV y ejecuta la preparación para Neo4j (cabeceras, datos, relaciones)     |
| `convert`         | Convertir archivos TSV a formato CSV                                                          |
| `prepare-neo4j`   | Generar cabeceras, etiquetas y relaciones desde CSVs convertidos                              |
| `prepare-desktop` | Fusionar cabeceras + datos en CSVs listos para Neo4j Desktop para importaciones drag-and-drop |
| `import-neo4j`    | Ejecutar importación masiva de Neo4j (lee desde `output/core/*`)                              |
| `build-vector`    | Construir base de datos vectorial desde nodos Neo4j y almacenar embeddings en Milvus          |
| `query`           | Consultar el sistema RAG                                                                      |
| `start`           | Iniciar servicios docker (Milvus, gateway) y lanzar el servidor FastAPI con chequeos de salud |

### Comando Start

```bash
python main.py start [OPCIONES]
```

Une `docker compose up -d` y el arranque del servidor FastAPI en un solo comando con mensajes profesionales.

| Opción             | Por defecto                         | Descripción |
| ------------------ | ----------------------------------- | ----------- |
| `--compose-file`   | `docker-compose.yml`                | Archivo compose que define Milvus, MinIO y el gateway de modelos |
| `--skip-compose`   | `False`                             | Asume que los contenedores ya corren y solo ejecuta chequeos |
| `--no-server`      | `False`                             | Prepara/valida servicios pero no inicia el servidor FastAPI |
| `--host`           | `API_HOST` \ `0.0.0.0`              | Interfaz de red para el servidor FastAPI |
| `--port`           | `API_PORT` \ `8000`                 | Puerto donde debe escuchar el servidor FastAPI |
| `--reload/--no-reload` | `--no-reload`                  | Activa el auto-reload de uvicorn (solo desarrollo) |

Si algún servicio depende (Neo4j Bolt, Milvus o el gateway de modelos) no responde, el comando se detiene mostrando exactamente qué falta por iniciar.

### Comando Build

```bash
python main.py build [OPCIONES]
```

**Opciones:**

| Opción             | Por defecto | Descripción                                                                                   |
| ------------------ | ----------- | --------------------------------------------------------------------------------------------- |
| `--config RUTA`    | `.env`      | Ruta al archivo de configuración                                                              |
| `--demo/--no-demo` | `--no-demo` | Forzar muestreo demo + construcción vectorial en modo prueba (sobrescribe varios valores env) |
| `--profile PERFIL` | selección interactiva / `full` (no TTY) | Elegir un perfil: `full`, `demo`, `neo4j-only`, `embeddings-only` o `conversion-only`. Si se omite, la CLI pregunta (y en entornos no interactivos usa `full`). |

**Perfiles:**

- `full`: Ejecuta la cadena completa (convertir → preparar → importar → embeddings).
- `demo`: Igual que `full` pero fuerza los parámetros demo (`--demo` es un atajo).
- `neo4j-only`: Omite conversión/preparación y solo ejecuta la importación masiva de Neo4j usando CSV existentes.
- `embeddings-only`: Salta directo a la construcción vectorial; asume que Neo4j ya está poblado y en línea.
- `conversion-only`: Solo realiza la conversión de TAR/TSV a CSV.

### Comando Build-Data

```bash
python main.py build-data [OPCIONES]
```

Combina la conversión TAR/TSV y la preparación para Neo4j en una sola llamada. Útil cuando necesitas CSV frescos pero planeas ejecutar la importación de Neo4j manualmente más tarde.

| Opción                              | Por defecto (env)                            | Descripción |
| ----------------------------------- | -------------------------------------------- | ----------- |
| `--core-dir RUTA`                   | `TSV_CORE_DIR` \ `music_metadata`            | Directorio con los dumps core de MusicBrainz (TAR/TSV) |
| `--derived-dir RUTA`                | `TSV_DERIVED_DIR` \ `music_derived_metadata` | Directorio con los dumps derivados |
| `--output-dir RUTA`                 | `OUTPUT_DIR` \ `output`                      | Directorio base para cabeceras/datos/relaciones preparados |
| `--csv-core-dir RUTA`               | `CSV_CORE_DIR` \ `output/converted/core`     | Directorio opcional para los CSV core convertidos |
| `--csv-derived-dir RUTA`            | `CSV_DERIVED_DIR` \ `output/converted/derived` | Directorio opcional para los CSV derivados convertidos |
| `--sample-percent FLOAT`            | `SAMPLE_PERCENT` \ `100.0`                   | Porcentaje de filas a conservar durante la preparación |
| `--sample-seed INT`                 | `SAMPLE_SEED` \ `42`                         | Semilla determinista para el muestreo |
| `--delimiter STR`                   | `DELIMITER` \ `\t`                           | Delimitador de entrada (acepta literal `\t`) |
| `--encoding STR`                    | `ENCODING` \ `utf-8`                         | Codificación de archivo |
| `--skip-headers`                    | env `SKIP_HEADERS=false`                      | Saltar generación de cabeceras |
| `--skip-labels`                     | env `SKIP_LABELS=false`                       | Saltar creación de datos etiquetados |
| `--skip-relationships`              | env `SKIP_RELATIONSHIPS=false`                | Saltar generación de relaciones |
| `--reuse-converted / --no-reuse-converted` | `--reuse-converted` | Reutilizar los CSV existentes si ya fueron convertidos |

### Modo Demo / Compatibilidad hacia atrás

- Preferir `uv run python main.py build --demo` para construcciones mínimas.
- El comando `demo-build` fue eliminado; usar `build --demo` en su lugar.

### Comando Convert

```bash
python main.py convert [OPCIONES] RUTA
```

**Argumentos:**

- `RUTA`: Directorio que contiene archivos TSV

**Opciones:**

| Opción       | Por defecto | Descripción                            |
| ------------ | ----------- | -------------------------------------- |
| `--out RUTA` | `out_csv`   | Directorio de salida para archivos CSV |

### Comando Prepare-Neo4j

```bash
python main.py prepare-neo4j [OPCIONES]
```

**Opciones:**

| Opción                   | Por defecto (env)                             | Descripción                                                     |
| ------------------------ | --------------------------------------------- | --------------------------------------------------------------- |
| `--core-dir RUTA`        | `TSV_CORE_DIR` \\ `music_metadata`            | Directorio conteniendo los archivos CSV/TSV core convertidos    |
| `--derived-dir RUTA`     | `TSV_DERIVED_DIR` \\ `music_derived_metadata` | Directorio conteniendo archivos CSV/TSV derivados (opcional)    |
| `--output-dir RUTA`      | `OUTPUT_DIR` \\ `output`                      | Destino para subdirectorios generados `core/` y `derived/`      |
| `--sample-percent FLOAT` | `SAMPLE_PERCENT` \\ `100.0`                   | Porcentaje de filas a mantener (0-100)                          |
| `--sample-seed INT`      | `SAMPLE_SEED` \\ `42`                         | Semilla de muestreo determinista                                |
| `--delimiter STR`        | `DELIMITER` \\ `\t`                           | Delimitador usado en los archivos fuente (soporta literal `\t`) |
| `--encoding STR`         | `ENCODING` \\ `utf-8`                         | Codificación de archivo                                         |
| `--skip-headers`         | env `SKIP_HEADERS=false`                      | Saltar generación de cabeceras                                  |
| `--skip-labels`          | env `SKIP_LABELS=false`                       | Saltar generación de datos etiquetados                          |
| `--skip-relationships`   | env `SKIP_RELATIONSHIPS=false`                | Saltar generación de relaciones                                 |

### Comando Prepare-Desktop

```bash
python main.py prepare-desktop [OPCIONES]
```

Este comando copia las cabeceras y datos generados en `output/neo4j_desktop/{nodes,relationships}` con filas de cabecera adjuntas, para que Neo4j Desktop pueda importarlos vía drag-and-drop.

| Opción                                        | Por defecto              | Descripción                                                        |
| --------------------------------------------- | ------------------------ | ------------------------------------------------------------------ |
| `--output-dir RUTA`                           | `OUTPUT_DIR` \\ `output` | Directorio base que ya contiene artefactos `core/` + `derived/`    |
| `--bundle-dir RUTA`                           | `output/neo4j_desktop`   | Carpeta destino para CSVs listos para Desktop                      |
| `--delimiter STR`                             | `DELIMITER` \\ `\t`      | Delimitador para incrustar en las filas de cabecera                |
| `--encoding STR`                              | `ENCODING` \\ `utf-8`    | Codificación para los CSVs fusionados                              |
| `--include-derived-nodes / --no-...`          | `True`                   | Copiar nodos etiquetados desde `derived/` si están presentes       |
| `--include-extended-relationships / --no-...` | `True`                   | Copiar CSVs de relaciones extendidas desde `derived/relationships` |

### Comando Import-Neo4j

```bash
python main.py import-neo4j [OPCIONES]
```

**Opciones:**

| Opción                      | Por defecto (env)               | Descripción                                                                        |
| --------------------------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| `--output-dir RUTA`         | `OUTPUT_DIR` \\ `output`        | Directorio base conteniendo `core/headers`, `core/labeled`, y `core/relationships` |
| `--db-name STR`             | `DB_NAME` \\ `musicbrainz.db`   | Nombre de base de datos Neo4j objetivo (sin `.db` cuando se usa `:use`)            |
| `--delimiter STR`           | `DELIMITER` \\ `\t`             | Delimitador CSV pasado a `neo4j-admin`                                             |
| `--array-delimiter STR`     | `ARRAY_DELIMITER` \\ `;`        | Delimitador de campo array                                                         |
| `--allow-bad-relationships` | `ALLOW_BAD_RELATIONSHIPS=false` | No fallar en relaciones colgantes                                                  |
| `--multiline-fields`        | `MULTILINE_FIELDS=true`         | Tratar campos como multilínea al importar                                          |
| `--verify`                  | `VERIFY=false`                  | Ejecutar consultas de sanidad después de importar                                  |
| `--user STR`                | `NEO4J_USER` \\ `neo4j`         | Usuario Neo4j para verificación                                                    |
| `--password STR`            | `NEO4J_PASSWORD`                | Contraseña Neo4j                                                                   |
| `--host STR`                | `NEO4J_HOST` \\ `localhost`     | Host Neo4j                                                                         |
| `--port INT`                | `NEO4J_PORT` \\ `7687`          | Puerto Bolt para verificación                                                      |
| `--neo4j-bin-path RUTA`     | `NEO4J_BIN_PATH`                | Ruta explícita al directorio `bin/` de Neo4j                                       |
| `--java-home RUTA`          | `JAVA_HOME`                     | Instalación Java a usar para la importación                                        |
| `--legacy-import`           | `LEGACY_IMPORT=false`           | Usar la sintaxis heredada `neo4j-admin import`                                     |

**Nota sobre la base de datos Neo4j:**

Después de ejecutar la importación masiva, la base de datos se crea automáticamente. Sin embargo, para acceder a ella desde Neo4j Browser o para consultas interactivas, ejecuta estos comandos en Neo4j Browser:

```cypher
:use system
CREATE DATABASE <db-name> IF NOT EXISTS
:use <db-name>
```

Reemplaza `<db-name>` con el valor especificado en `--db-name` (sin la extensión `.db`). Por ejemplo, si usaste `--db-name musicbrainz.db`, usa `musicbrainz` en los comandos.

## Proceso de Construcción Completo

El comando `build` automatiza el pipeline completo usando un archivo de configuración (formato `.env`).

### Archivo de Configuración

Crea un archivo `.env` con tus configuraciones:

```bash
# Copiar desde ejemplo
cp .env.example .env

# Editar con tus valores
nano .env
```

### Configuración Requerida

```bash
# Directorios de Entrada/Salida
TSV_CORE_DIR=/data/musicbrainz/core
TSV_DERIVED_DIR=/data/musicbrainz/derived
OUTPUT_DIR=output
CSV_CORE_DIR=${OUTPUT_DIR}/converted/core
CSV_DERIVED_DIR=${OUTPUT_DIR}/converted/derived

# Muestreo (opcional)
SAMPLE_PERCENT=100.0
SAMPLE_SEED=42

# Configuraciones Neo4j
DB_NAME=musicbrainz.db
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_HOST=localhost
NEO4J_PORT=7687

# Construcción Vectorial
VECTOR_LABELS=Artist,Recording,Release,Tag
```

### Pasos del Proceso de Construcción

1. **Conversión**: Extraer archivos TAR (si están presentes) y convertir los volcados crudos apuntados por `TSV_CORE_DIR` / `TSV_DERIVED_DIR` en conjuntos de trabajo CSV (`CSV_CORE_DIR`, `CSV_DERIVED_DIR`).
2. **Preparación**: Generar cabeceras Neo4j, filas etiquetadas y archivos de relaciones en `OUTPUT_DIR/core` (opcionalmente muestreando filas para demos).
3. **Paquete Desktop (opcional)**: Ejecutar `prepare-desktop` para copiar los archivos preparados en `OUTPUT_DIR/neo4j_desktop` con cabeceras en línea para el importador drag-and-drop de Neo4j Desktop.
4. **Importación Neo4j**: Ejecutar `neo4j-admin database import` vía `import-neo4j`, luego opcionalmente ejecutar consultas de verificación a través de Bolt.
5. **Construcción Vectorial**: Transmitir nodos desde Neo4j, solicitar embeddings al gateway de modelos y escribir vectores en Milvus para RAG.

### Salida de Construcción

```text
Loaded config from: .env
Starting full build process...

Step 1: Converting MusicBrainz dumps (TAR/TSV) into CSV working directories
✓ Converted 15 core file(s) to CSV.
✓ Converted 10 derived file(s) to CSV.

Step 2: Preparing headers and data for Neo4j
✓ Preparation completed!
Generated files:
  - neo4j_headers (headers)
  - labeled (labeled data)
  - relationships (relationships)

Step 3: Importing CSVs into Neo4j (neo4j-admin bulk import)
✓ Neo4j bulk import completed.
✓ Verification completed.

Paso 4: Construcción de la base vectorial Milvus (requiere el contenedor del gateway de modelos)
✓ Vector DB build completed!

🎉 Build finished! Neo4j + Milvus are ready for RAG queries.
```

#### Post-Construcción: Acceso a la Base de Datos

Después de completar el proceso de construcción, la base de datos Neo4j se crea automáticamente. Para acceder a ella desde Neo4j Browser:

```cypher
:use system
CREATE DATABASE <db-name> IF NOT EXISTS
:use <db-name>
```

Donde `<db-name>` es el nombre especificado en `DB_NAME` (sin `.db`). Por defecto es `musicbrainz`.

## Ejemplos de Uso

### 1. Construcción Completa con Configuración por Defecto

```bash
python main.py build
```

### 2. Construcción Completa con Configuración Personalizada

```bash
python main.py build --config my_config.env
```

### 3. Pasos Individuales para Desarrollo

```bash
# Convertir archivos
python main.py convert /data/musicbrainz/core --out converted/core
python main.py convert /data/musicbrainz/derived --out converted/derived

# Preparar con muestra del 25%
python main.py prepare-neo4j \
  --core-dir converted/core \
  --derived-dir converted/derived \
  --output-dir output \
  --sample-percent 25.0 \
  --sample-seed 123

# Paquete para Neo4j Desktop (opcional)
python main.py prepare-desktop --output-dir output --bundle-dir output/neo4j_desktop

# Importar con verificación
python main.py import-neo4j \
  --output-dir output \
  --verify \
  --password mypassword
```

### 4. Pipeline de Producción

```bash
# Construcción completa de producción
echo "TSV_CORE_DIR=/data/mb-dump-2024/core" > .env
echo "TSV_DERIVED_DIR=/data/mb-dump-2024/derived" >> .env
echo "OUTPUT_DIR=/data/mb-dump-2024/output" >> .env
echo "SAMPLE_PERCENT=100.0" >> .env
echo "NEO4J_PASSWORD=production_password" >> .env

python main.py build
```

### 5. Pipeline de Pruebas

```bash
# Prueba rápida con muestra pequeña
echo "SAMPLE_PERCENT=10.0" > .env
echo "VERIFY=true" >> .env

python main.py build
```
