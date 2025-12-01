# Plan General y Arquitectura del Proyecto

Este documento detalla la visión arquitectónica y los pasos técnicos para construir el sistema de recomendación musical basado en RAG Híbrido (Grafo + Vectorial).

## 1. Bosquejo General del Proyecto (Arquitectura)

El sistema funciona como un experto musical con "dos cerebros" y una "voz":

### A. El Cerebro Lógico (Neo4j - Grafo de Conocimiento)

- **Función**: Almacena hechos concretos y conexiones exactas.
- **Ejemplo**: Sabe _exactamente_ qué artistas colaboraron en un álbum específico o qué canciones pertenecen a un subgénero preciso.
- **Uso**: Responde preguntas sobre relaciones directas (ej. "¿Qué conexiones existen entre el Artista A y el B?").

### B. El Cerebro Intuitivo (Milvus - Base de Datos Vectorial)

- **Función**: Almacena el "significado" semántico y el contexto mediante embeddings Gemma.
- **Modelo**: Utiliza `text-embedding-embeddinggemma-300m-qat` para generar los vectores.
- **Ejemplo**: Si se busca "canciones tristes sobre rupturas", encuentra canciones con letras o descripciones que _significan_ eso, aunque no contengan la palabra "triste".
- **Uso**: Recuperación de contexto cuando la consulta es vaga, temática o basada en similitud.

### C. La Voz (Gemma 3 - LLM)

- **Función**: Generador de texto y razonamiento final.
- **Modelo**: `gemma-3-1b-it-qat`, servido por el contenedor `pmllm-model-gateway`.
- **Uso**: Recibe la pregunta del usuario + la información recuperada de Neo4j y Milvus. Redacta una respuesta natural, explica las recomendaciones y cita las fuentes.

---

## 2. Flujo de Datos (Pipeline)

El proceso de transformación de los datos es el siguiente:

1. **Ingesta (Completado)**:

   - `Raw Data` (tar/tsv) -> `CSVs Limpios` (Headers + Datos normalizados).

2. **Construcción del Grafo (Paso Inmediato)**:

   - Uso de `neo4j-admin import` para carga masiva de CSVs en **Neo4j Desktop**.
   - _Resultado_: Una base de datos navegable con Nodos (Artistas, Canciones, Álbumes) y Relaciones.

3. **Vectorización (Paso Crítico)**:

   - Lectura de nodos desde Neo4j (o CSVs).
   - Generación de texto descriptivo para cada nodo (ej: "Queen es una banda de Rock formada en Londres...").
   - **Generación de embeddings**: Se delega al contenedor `pmllm-model-gateway`, el cual expone `/v1/embeddings` con el modelo `text-embedding-embeddinggemma-300m-qat`.
   - Almacenamiento de vectores en **Milvus**.

4. **Consulta (RAG Híbrido)**:
   - Usuario hace una pregunta.
   - Búsqueda en **Milvus** (Similitud semántica).
   - Búsqueda en **Neo4j** (Relaciones estructurales).
   - Consolidación de contexto -> Prompt enviado al **gateway de modelos** (API OpenAI-compat).
   - Generación de respuesta final.

---

## 3. Próximos Pasos Detallados

Hoja de ruta técnica para la implementación de la Fase 2:

### Paso 2.1: Levantar Infraestructura

- **Stack Docker**: Ejecutar `docker compose up -d` para iniciar Milvus (etcd + MinIO), el contenedor `pmllm-model-gateway` (Gemma embeddings/LLM) y el contenedor `pmllm-recommender-api` (chat y preferencias).
- **Neo4j Desktop**:
   - Crear un proyecto nuevo (vacío).
   - Ubicar la ruta de la carpeta `bin` de la instalación.
   - Mantener la base de datos detenida para permitir la importación inicial.

### Paso 2.2: Importación a Neo4j (El Grafo)

Utilizar el script `main.py` apuntando a la instalación local de Neo4j Desktop.

- **Reto**: Identificar la ruta `bin` correcta en Neo4j Desktop.
- **Acción**: Ejecutar comando de importación (`import-neo4j`).
- **Validación**: Verificar en Neo4j Browser que los nodos y relaciones se han creado correctamente.

### Paso 2.3: Construcción Vectorial (Los Embeddings)

Desarrollar/Actualizar el script de población (`db/vector/build_vector_db.py`):

1. Conectar a Neo4j para extraer lotes de nodos.
2. Generar descripciones textuales de los nodos.
3. **Generar Embeddings**: Consumir el endpoint `/v1/embeddings` del gateway (modelo `text-embedding-embeddinggemma-300m-qat`) para mantener consistencia con producción.
4. Insertar vectores y metadatos en Milvus.

### Paso 2.4: Consolidación RAG

Actualizar `rag_pipeline.py`:

- Integrar la búsqueda híbrida (Milvus + Neo4j).
- Configurar el cliente de API para apuntar al gateway (`http://localhost:9000/v1`).
- Diseñar el prompt final para Gemma 3.
