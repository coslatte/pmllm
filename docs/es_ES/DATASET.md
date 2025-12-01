# Documentación del Conjunto de Datos

## Conjunto de Datos de MusicBrainz

El sistema utiliza un conjunto de datos fragmentado de MusicBrainz que contiene metadatos musicales y relaciones.

### Fuente

- **Fuente Original**: MusicBrainz (musicbrainz.org)
- **Formato**: Volcados de PostgreSQL + Exportaciones de Neo4j
- **Alcance**: Metadatos musicales incluyendo artistas, grabaciones, lanzamientos, obras y relaciones

### Estructura de Datos

#### Entidades Principales

- **Artists (Artistas)**: Datos biográficos, orígenes, géneros
- **Recordings (Grabaciones)**: Pistas individuales con metadatos
- **Releases (Lanzamientos)**: Álbumes y sencillos
- **Works (Obras)**: Composiciones musicales
- **Areas (Áreas)**: Ubicaciones geográficas
- **Release Groups (Grupos de Lanzamiento)**: Agrupaciones lógicas
- **Tags (Etiquetas)**: Etiquetas de género y categoría

#### Entidades Derivadas

- **Labels (Sellos)**: Compañías discográficas
- **Mediums (Medios)**: Formatos físicos (CD, Vinilo, Digital)
- **Tracks (Pistas)**: Pistas individuales en lanzamientos
- **Places (Lugares)**: Lugares de grabación y estudios
- **Events (Eventos)**: Conciertos y festivales
- **Genres (Géneros)**: Géneros musicales
- **Instruments (Instrumentos)**: Instrumentos musicales
- **Series (Series)**: Series de álbumes/artistas
- **URLs**: Enlaces externos

#### Relaciones

- Artist-Recording (interpretado en)
- Artist-Release (lanzado)
- Recording-Work (pertenece a)
- Asociaciones geográficas
- Clasificaciones de género
- Relaciones de la industria

### Pipeline de Procesamiento

1. **Conversión TSV a CSV**: Volcados crudos de MusicBrainz a formato CSV
2. **Etiquetado de Datos**: Agregar etiquetas de tipo de entidad para importación en Neo4j
3. **Generación de Relaciones**: Crear archivos de relación para conexiones de grafo
4. **Muestreo**: Reducción opcional de datos para pruebas/desarrollo
5. **Importación Neo4j**: Importación masiva a la base de datos de grafos
6. **Embedding Vectorial**: Generar embeddings para recuperación RAG

### Configuración

El procesamiento de datos se controla mediante variables de entorno en `.env`:

- `SAMPLE_PERCENT`: Porcentaje de muestreo de datos
- `PROCESS_*`: Habilitar/deshabilitar tipos de datos derivados
- `TSV_CORE_DIR`: Ubicación de datos principales
- `TSV_DERIVED_DIR`: Ubicación de datos derivados

### Aseguramiento de Calidad

- Validación de esquema para todos los tipos de entidades
- Verificaciones de integridad de relaciones
- Compatibilidad de muestreo
- Optimizado para casos de uso de recomendación musical

### Uso en RAG

- **Búsqueda Vectorial**: Similitud semántica sobre descripciones de entidades
- **Contexto de Grafo**: Relaciones estructuradas desde Neo4j
- **Generación**: Respuestas contextuales usando Gemma 3 LLM
