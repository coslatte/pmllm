````markdown
# Distribución de Datos para la Base de Datos de Chats y Recomendaciones de Usuario

## Resumen Ejecutivo

Este documento describe la arquitectura de datos del sistema PMLLM, enfocándose en la distribución y almacenamiento de datos relacionados con chats de usuario, preferencias musicales y el sistema de recomendaciones. El sistema utiliza una arquitectura híbrida con múltiples bases de datos especializadas para optimizar el rendimiento y la funcionalidad.

## Arquitectura General de Datos

El sistema implementa una arquitectura de "dos cerebros y una voz":

- **Cerebro Lógico (Neo4j)**: Base de datos de grafos para relaciones exactas entre entidades musicales
- **Cerebro Intuitivo (Milvus)**: Base de datos vectorial para similitudes semánticas
- **Voz (Gemma 3)**: Modelo de lenguaje (expuesto vía el contenedor `pmllm-model-gateway`) para generación de respuestas

### Componentes de Almacenamiento

1. **Base de Datos Local (SQLite)**
2. **Base de Datos de Grafos (Neo4j)**
3. **Base de Datos Vectorial (Milvus)**

## 1. Base de Datos de Chats y Preferencias de Usuario (SQLite)

### Estructura de Tablas

#### Tabla `users`

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Distribución de Datos:**

- Almacena información básica de usuarios registrados
- Índice en `username` para búsquedas rápidas
- Relación uno-a-uno con preferencias
- Relación uno-a-muchos con chats

#### Tabla `preferences`

```sql
CREATE TABLE preferences (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    fav_genres TEXT,  -- JSON array
    fav_artists TEXT, -- JSON array
    fav_instruments TEXT, -- JSON array
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Distribución de Datos:**

- **fav_genres**: Lista JSON de géneros musicales preferidos
  - Ejemplo: `["rock", "jazz", "classical"]`
  - Distribución típica: 1-5 géneros por usuario
- **fav_artists**: Lista JSON de artistas favoritos
  - Ejemplo: `["The Beatles", "Miles Davis", "Ludwig van Beethoven"]`
  - Distribución típica: 3-10 artistas por usuario
- **fav_instruments**: Lista JSON de instrumentos preferidos
  - Ejemplo: `["guitar", "piano", "saxophone"]`
  - Distribución típica: 1-3 instrumentos por usuario

#### Tabla `chats`

```sql
CREATE TABLE chats (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Distribución de Datos:**

- Cada chat representa una sesión de conversación
- Múltiples chats por usuario permitidos
- Historial temporal de interacciones

#### Tabla `messages`

```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    chat_id TEXT REFERENCES chats(id),
    role TEXT,  -- 'user' o 'assistant'
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Distribución de Datos:**

- **role**: Identifica si el mensaje es del usuario o del asistente
- **content**: Texto completo del mensaje
- Patrón típico: Alternancia user/assistant en conversaciones
- Longitud promedio de mensajes: 50-500 caracteres

### Estadísticas de Distribución Esperadas

- **Usuarios Activos**: 100-1000 usuarios iniciales
- **Chats por Usuario**: 1-20 chats promedio
- **Mensajes por Chat**: 5-50 mensajes promedio
- **Tamaño de Base de Datos**: ~10-100 MB para uso típico

## 2. Sistema de Recomendaciones

### Flujo de Datos para Recomendaciones

1. **Entrada de Usuario**: Preferencias almacenadas en SQLite
2. **Generación de Perfil**: Conversión de preferencias a texto descriptivo
3. **Búsqueda en Contexto**: Consulta a Neo4j + Milvus
4. **Generación de Recomendaciones**: LLM procesa contexto y preferencias

### Formato de Perfil de Usuario

El perfil se genera como texto natural:

```
"User likes rock, jazz music, favorite artists include The Beatles, Miles Davis, enjoys listening to guitar, piano."
```

### Estructura de Recomendaciones de Salida

```json
{
  "recommendations": [
    {
      "type": "artist|album|track",
      "title": "Nombre del artista, álbum o pista",
      "description": "Descripción corta",
      "explanation": "Explicación detallada basada en similitudes semánticas o relaciones de grafo",
      "confidence": 0.0-1.0,
      "sources": ["fuente1", "fuente2"],
      "suggested_actions": ["Escuchar...", "Explorar discografía"]
    }
  ],
  "general_summary": "Resumen general de las recomendaciones"
}
```

## 3. Base de Datos Musical (Neo4j + Milvus)

### Neo4j - Grafo de Conocimiento Musical

**Tipos de Nodos Principales:**

- Artist (Artista)
- Recording (Grabación)
- Release (Lanzamiento)
- Work (Obra)
- Area (Área geográfica)
- Genre (Género)
- Instrument (Instrumento)

**Relaciones Principales:**

- Artist → Recording (performs)
- Recording → Work (is based on)
- Release → ReleaseGroup (belongs to)
- Artist → Area (from)
- Recording → Genre (tagged as)

### Milvus - Base de Datos Vectorial

**Colecciones:**

- **music_entities**: Vectores para entidades musicales
  - Dimensiones: 768 (depende del modelo de embedding)
  - Índice: IVF_FLAT o HNSW para búsqueda eficiente
- **user_profiles**: Vectores para perfiles de usuario
  - Almacena representaciones vectoriales de preferencias
  - Usado para matching semántico con contenido musical

## 4. Distribución de Carga de Trabajo

### Lectura/Escritura por Componente

- **SQLite**: Alta frecuencia de lecturas para preferencias y chats
- **Neo4j**: Consultas de grafo para relaciones musicales
- **Milvus**: Búsqueda vectorial para similitudes semánticas
- **LLM**: Generación de texto para recomendaciones

### Estrategias de Optimización

1. **Caché de Perfiles**: Perfiles de usuario en Milvus para acceso rápido
2. **Indexación**: Índices en campos de búsqueda frecuente
3. **Compresión**: Vectores comprimidos en Milvus para eficiencia
4. **Sharding**: Datos musicales distribuidos por tipo de entidad

## 5. Consideraciones de Escalabilidad

### Límites Actuales

- SQLite: Adecuado para < 10,000 usuarios activos
- Neo4j: Maneja grafos de millones de nodos
- Milvus: Escalable a billones de vectores

### Planes de Expansión

- Migración a PostgreSQL para datos de usuario si crece
- Clustering de Neo4j para alta disponibilidad
- Distribución de Milvus para manejo de grandes volúmenes

## 6. Seguridad y Privacidad

### Protección de Datos

- Preferencias de usuario almacenadas como JSON encriptado
- Chats cifrados en tránsito y reposo
- Acceso basado en user_id para aislamiento

### Cumplimiento

- GDPR: Consentimiento para almacenamiento de preferencias
- Anonimización de datos para análisis
- Retención limitada de historial de chats

## 7. Monitoreo y Mantenimiento

### Métricas Clave

- Latencia de recomendaciones: < 5 segundos
- Precisión de recomendaciones: > 80%
- Disponibilidad del sistema: > 99.9%

### Tareas de Mantenimiento

- Limpieza periódica de chats antiguos
- Reindexación de vectores en Milvus
- Backup de bases de datos

---

_Este documento debe actualizarse con cada cambio significativo en la arquitectura de datos._
````