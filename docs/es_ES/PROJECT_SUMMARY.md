# PMLLM - Sistema RAG con Grafo de Conocimiento Musical

## Resumen Completo del Proyecto

Este documento proporciona una visión integral del sistema PMLLM (Personalized Music Language Learning Model), consolidando todas las decisiones arquitectónicas, componentes y patrones de uso en una única referencia.

---

## 1. Descripción General del Proyecto

### Propósito

PMLLM es un sistema de Generación Aumentada por Recuperación (RAG) para datos musicales que combina:

- **Grafo de Conocimiento** (Neo4j) para relaciones estructuradas
- **Base de Datos Vectorial** (Milvus) para similitud semántica
- **Modelo de Lenguaje Grande** (Gemma 3) para generación de lenguaje natural

### Usuarios Objetivo

- Estudiantes universitarios buscando recursos de educación musical
- Profesionales explorando conexiones en la industria musical
- Desarrolladores construyendo funcionalidades de recomendación

### Criterios de Éxito

- ≥80% de precisión en conjunto de pruebas Q&A curado
- 50% de reducción en tiempo promedio de búsqueda de información
- Recomendaciones personalizadas y explicables

---

## 2. Arquitectura

### Metáfora "Dos Cerebros y Una Voz"

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CONSULTA DEL USUARIO                            │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ORQUESTADOR RAG                                 │
│                    (rag_pipeline.py)                                │
└─────────────────────────────────────────────────────────────────────┘
           │                                         │
           ▼                                         ▼
┌─────────────────────┐                 ┌─────────────────────┐
│   CEREBRO LÓGICO    │                 │  CEREBRO INTUITIVO  │
│      (Neo4j)        │                 │     (Milvus)        │
│                     │                 │                     │
│ • Hechos exactos    │                 │ • Significado       │
│ • Relaciones        │                 │   semántico         │
│ • Recorrido grafos  │                 │ • Embeddings        │
└─────────────────────┘                 └─────────────────────┘
           │                                         │
           └──────────────────┬──────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          VOZ                                         │
│                    (Gemma 3 LLM)                                    │
│                                                                      │
│    • Generación de lenguaje natural                                  │
│    • Respuestas contextuales                                         │
│    • Recomendaciones explicables                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   RESPUESTA AL USUARIO                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Topología de Contenedores

| Contenedor            | Puerto | Propósito                                      |
|-----------------------|--------|------------------------------------------------|
| `milvus-standalone`   | 19530  | Base de datos vectorial para embeddings        |
| `milvus-etcd`         | -      | Coordinación de metadatos Milvus               |
| `milvus-minio`        | 19000  | Almacenamiento de objetos para Milvus          |
| `gemma-embeddings`    | 8081   | Generación de embeddings (servidor llama.cpp)  |
| `gemma-chat`          | 8082   | Completaciones de chat (servidor llama.cpp)    |
| `pmllm-user-db`       | 5433   | PostgreSQL para datos de usuario/chats         |
| `pmllm-recommender-api`| 8080  | Backend FastAPI para frontend                  |

---

## 3. Pipeline de Datos

### Flujo de Datos

```
Dumps MusicBrainz TSV/TAR
         │
         ▼ (comando convert)
    Conjuntos CSV de Trabajo
         │
         ▼ (comando prepare-neo4j)
    Headers Neo4j + Datos Etiquetados + Relaciones
         │
         ▼ (comando import-neo4j)
    Base de Datos Grafo Neo4j
         │
         ▼ (comando build-vector)
    Base de Datos Vectorial Milvus
         │
         ▼ (comando query / API)
    Respuestas RAG
```

### Tipos de Entidades

**Nodos Principales (7):**
- Artist (15 campos)
- Recording (7 campos)
- Release (7 campos)
- Work (6 campos)
- Area (5 campos)
- ReleaseGroup (7 campos)
- Tag (3 campos)

**Nodos Derivados (9, configurables):**
- Label, Medium, Track, Place, Event, Genre, Instrument, Series, Url

**Relaciones (25+):**
- PERFORMED_ON, RELEASED, BELONGS_TO, FROM_AREA, HAS_TAG, PUBLISHED, PLAYS, etc.

---

## 4. Estructura del Proyecto

```
pmllm/
├── main.py                 # Punto de entrada CLI (basado en Typer)
├── docker-compose.yml      # Orquestación de contenedores
├── .env                    # Configuración de entorno
├── pyproject.toml          # Dependencias Python
│
├── db/
│   ├── neo4j/
│   │   ├── neo4j_handler.py    # Operaciones de consulta Neo4j
│   │   └── neo4j_importer.py   # Lógica de importación masiva
│   └── vector/
│       ├── build_vector_db.py  # Poblar Milvus desde Neo4j
│       ├── milvus_store.py     # Conexión Milvus
│       ├── rag_pipeline.py     # Orquestación RAG
│       ├── vector_query.py     # Búsqueda vectorial
│       └── helper/
│           ├── embedder.py     # Cliente API de embeddings
│           ├── llm_handler.py  # Cliente API de LLM
│           └── text_builder.py # Generación de texto para nodos
│
├── server/
│   ├── main.py                 # Aplicación FastAPI
│   ├── database.py             # Modelos SQLAlchemy
│   ├── query_engine.py         # Endpoint de consultas RAG
│   ├── recommendation_engine.py # Lógica de recomendaciones
│   └── milvus_handler.py       # Vectores de perfil de usuario
│
├── model_gateway/
│   ├── app.py                  # Servidor FastAPI embedding/LLM
│   ├── Dockerfile              # Build del contenedor
│   └── requirements.txt        # Dependencias del gateway
│
├── utils/
│   ├── cli_helpers.py          # Utilidades CLI
│   ├── constants.py            # Constantes compartidas
│   ├── data_builder.py         # Preparación de datos
│   ├── files_manager/
│   │   ├── converter.py        # Conversión TSV a CSV
│   │   ├── csv_helper.py       # Preparación CSV para Neo4j
│   │   └── reader.py           # Utilidades de lectura de archivos
│   └── helpers/
│       ├── convert_handler.py
│       ├── import_handler.py
│       └── prepare_handler.py
│
├── docs/
│   ├── PROJECT_SUMMARY.md      # Resumen del proyecto (EN)
│   ├── API_DOCUMENTATION.md    # Referencia API REST
│   ├── CLI_USAGE.md            # Guía de comandos CLI
│   ├── ENVIRONMENT.md          # Variables de entorno
│   ├── CHANGELOG.md            # Historial de versiones
│   ├── DATASET.md              # Documentación de datos
│   ├── DISTRIBUCION_DATOS.md   # Arquitectura de datos (ES)
│   ├── RECOMMENDATION_SYSTEM.md # Contratos de recomendación
│   ├── es_ES/                  # Traducciones al español
│   └── plan/                   # Documentos de planificación
│
└── data/
    ├── milvus/                 # Volúmenes de datos Milvus
    ├── neo4j/                  # Volúmenes de datos Neo4j
    └── postgres/               # Volúmenes de datos PostgreSQL
```

---

## 5. Comandos CLI

### Comandos Principales

| Comando           | Descripción                                                    |
|-------------------|----------------------------------------------------------------|
| `build`           | Pipeline completo: convertir → preparar → importar → vectores |
| `build --demo`    | Build demo con overrides de muestreo                           |
| `start`           | Iniciar servicios Docker + servidor FastAPI                    |
| `query`           | Consultar el sistema RAG                                       |

### Perfiles de Build

| Perfil            | Descripción                                                    |
|-------------------|----------------------------------------------------------------|
| `full`            | Pipeline completo (convertir → preparar → importar → embeddings)|
| `demo`            | Completo con overrides de muestreo demo                        |
| `neo4j-only`      | Saltar a importación masiva Neo4j                              |
| `embeddings-only` | Saltar a construcción de base vectorial                        |
| `conversion-only` | Solo convertir TAR/TSV a CSV                                   |

### Ejemplos de Uso

```bash
# Build demo (dataset mínimo)
uv run python main.py build --demo

# Build producción completo
uv run python main.py build --config .env

# Solo embeddings (Neo4j ya poblado)
uv run python main.py build --profile embeddings-only

# Consultar el sistema
uv run python main.py query "¿Qué artistas son similares a Queen?"

# Iniciar todos los servicios
uv run python main.py start
```

---

## 6. Variables de Entorno Clave

### Conexiones de Base de Datos

| Variable             | Default                      | Descripción                    |
|----------------------|------------------------------|--------------------------------|
| `NEO4J_URI`          | `bolt://localhost:7687`      | Conexión Bolt Neo4j            |
| `NEO4J_USER`         | `neo4j`                      | Usuario Neo4j                  |
| `NEO4J_PASSWORD`     | -                            | Contraseña Neo4j               |
| `MILVUS_HOST`        | `127.0.0.1`                  | Host servidor Milvus           |
| `MILVUS_PORT`        | `19530`                      | Puerto servidor Milvus         |

### Model Gateway

| Variable              | Default                                    | Descripción                    |
|-----------------------|--------------------------------------------|--------------------------------|
| `EMBEDDING_API_URL`   | `http://localhost:8082/v1/embeddings`      | Endpoint de embeddings         |
| `EMBEDDING_MODEL`     | `text-embedding-embeddinggemma-300m-qat`   | Nombre modelo embeddings       |
| `LLM_API_URL`         | `http://localhost:8082/v1/chat/completions`| Endpoint de chat               |
| `LLM_MODEL`           | `gemma-3-1b-it-qat`                        | Nombre modelo LLM              |

### Controles de Muestreo

| Variable                    | Default | Descripción                              |
|-----------------------------|---------|------------------------------------------|
| `SAMPLE_PERCENT`            | `0.08`  | Porcentaje de muestreo de datos          |
| `DEMO_MODE`                 | `true`  | Habilitar modo demo                      |
| `DEMO_VECTOR_SAMPLE_PERCENT`| `100`   | Muestreo build vectorial en modo demo    |
| `TEST_MODE`                 | `false` | Habilitar modo test (muestreo adicional) |
| `VECTOR_BUILD_SAMPLE_PERCENT`| `100`  | Porcentaje muestreo build vectorial      |

---

## 7. Endpoints de API

### Gestión de Usuarios

| Método | Endpoint       | Descripción                    |
|--------|----------------|--------------------------------|
| POST   | `/users`       | Crear nuevo usuario            |
| GET    | `/users/{id}`  | Obtener usuario por ID         |

### Preferencias

| Método | Endpoint       | Descripción                    |
|--------|----------------|--------------------------------|
| POST   | `/preferences` | Actualizar preferencias        |
| GET    | `/preferences` | Obtener preferencias           |

### Chat

| Método | Endpoint                  | Descripción                    |
|--------|---------------------------|--------------------------------|
| POST   | `/chat`                   | Crear nueva sesión de chat     |
| POST   | `/message`                | Enviar mensaje en chat         |
| GET    | `/chat/{id}/messages`     | Obtener historial de chat      |

### Consultas y Recomendaciones

| Método | Endpoint                     | Descripción                    |
|--------|------------------------------|--------------------------------|
| POST   | `/query`                     | Consulta RAG con contexto      |
| POST   | `/recommendations`           | Obtener recomendaciones personalizadas|
| POST   | `/recommendations/albums`    | Obtener recomendaciones de álbumes|

---

## 8. Sistema de Recomendaciones

### Contrato de Salida

```json
{
  "recommendations": [
    {
      "type": "course | content | connection | album_plan",
      "title": "Nombre descriptivo corto",
      "description": "Resumen de una oración",
      "explanation": "Razonamiento trazable citando nodos del grafo o hits vectoriales",
      "confidence": 0.0-1.0,
      "sources": ["neo4j:Artist(Queen)", "milvus:vector_id_123"],
      "suggested_actions": ["Escuchar en plataforma", "Conectar con curador"]
    }
  ],
  "general_summary": "Resumen de las recomendaciones"
}
```

### Criterios de Calidad

- Retornar 5-10 entradas cuando hay datos suficientes
- Preferir confianza ≥ 0.7
- Siempre citar fuentes (nodos Neo4j o vectores Milvus)
- Manejar ambigüedad pidiendo aclaración

---

## 9. Flujo de Trabajo de Desarrollo

### Prerrequisitos

- Python 3.10+
- Docker y Docker Compose
- Neo4j Desktop o Server
- Java (para importación masiva Neo4j)

### Inicio Rápido

```bash
# 1. Clonar y configurar
git clone https://github.com/coslatte/pmllm.git
cd pmllm

# 2. Instalar dependencias
uv sync

# 3. Configurar entorno
cp .env.example .env
# Editar .env con tus rutas y configuraciones

# 4. Iniciar contenedores
docker compose up -d

# 5. Ejecutar build demo
uv run python main.py build --demo

# 6. Consultar el sistema
uv run python main.py query "Recomienda álbumes similares a Queen"
```

### Gestión de Contenedores

```bash
# Iniciar todos los servicios
docker compose up -d

# Ver logs
docker compose logs -f gemma-embeddings

# Verificar estado de contenedores
docker ps

# Detener servicios
docker compose down
```

---

## 10. Estado Actual (Diciembre 2025)

### Completado (Etapa 1 y 2)

- ✅ Pipeline de preparación de datos (TSV → CSV → Neo4j)
- ✅ Base de datos grafo Neo4j con datos MusicBrainz
- ✅ Integración base de datos vectorial Milvus
- ✅ Generación de embeddings vía contenedores llama.cpp
- ✅ Pipeline RAG con recuperación híbrida
- ✅ CLI con perfiles de build y soporte de consultas
- ✅ Servidor FastAPI con gestión de usuario/chat
- ✅ Orquestación Docker Compose

### En Progreso (Etapa 3)

- 🔄 Aplicación frontend React
- 🔄 Algoritmos avanzados de recomendación
- 🔄 Framework de evaluación y testing

### Planificado

- 📋 Configuración de despliegue en producción
- 📋 Infraestructura de monitoreo y logging
- 📋 Métricas de evaluación extendidas

---

## 11. Documentación Relacionada

| Documento                      | Descripción                                    |
|--------------------------------|------------------------------------------------|
| `docs/CLI_USAGE.md`            | Referencia detallada de comandos CLI           |
| `docs/API_DOCUMENTATION.md`    | Especificación API REST                        |
| `docs/ENVIRONMENT.md`          | Referencia de variables de entorno             |
| `docs/RECOMMENDATION_SYSTEM.md`| Contratos y prompts de recomendación           |
| `docs/DATASET.md`              | Documentación de datos MusicBrainz             |
| `docs/DISTRIBUCION_DATOS.md`   | Arquitectura de datos (Español)                |
| `docs/CHANGELOG.md`            | Historial de versiones y cambios               |
| `docs/plan/PLAN.md`            | Hitos y tareas del proyecto                    |
| `docs/plan/general_plan.md`    | Visión arquitectónica (Español)                |

---

## 12. Contactos y Recursos

- **Repositorio**: https://github.com/coslatte/pmllm
- **MusicBrainz**: https://musicbrainz.org
- **Milvus Docs**: https://milvus.io/docs
- **Neo4j Docs**: https://neo4j.com/docs
- **Modelos Gemma**: https://ai.google.dev/gemma

---

*Última actualización: 14 de diciembre de 2025*
